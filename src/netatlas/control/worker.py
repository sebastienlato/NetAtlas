"""One bounded local worker; delivery retries never call the collector again."""

import asyncio
import http.client
from datetime import UTC, datetime
from typing import Protocol

from netatlas import __version__
from netatlas.collectors.runner import collect
from netatlas.control.files import Boot, Credential, Pending, Spool
from netatlas.control.models import (
    BODY_BYTES,
    HEARTBEAT_SECONDS,
    Abandon,
    Claim,
    ControlError,
    Deliver,
    Heartbeat,
    Lease,
    Permit,
    Register,
    Reply,
    Request,
    Resume,
)
from netatlas.derivations.engine import canonical, digest
from netatlas.derivations.offline import json_object
from netatlas.discovery.policy import POLICY_SHA256, denial
from netatlas.discovery.tcp import connect
from netatlas.domain import ScannerNode, Target
from netatlas.observation import Observation


class Transport(Protocol):
    async def send(self, request: Request) -> Reply: ...


class LocalTransport:
    def __init__(self, credential: Credential, port: int = 8001):
        if not 1 <= port <= 65535:
            raise ValueError("port bound")
        self.credential, self.port = credential, port

    def _send(self, request: Request) -> Reply:
        raw = request.model_dump_json().encode()
        if len(raw) > BODY_BYTES:
            raise ValueError("request bound")
        # Numeric loopback only; http.client has no proxy, redirect or cookie machinery.
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        try:
            connection.request(
                "POST",
                "/control/v1/exchange",
                body=raw,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + self.credential.token,
                    "X-NetAtlas-Worker": str(self.credential.worker_id),
                },
            )
            response = connection.getresponse()
            body = response.read(65537)
            if response.status != 200:
                raise ControlError(response.status, "control_rejected")
            if len(body) > 65536:
                raise ValueError("response bound")
            return Reply.model_validate(json_object(body))
        except OSError, http.client.HTTPException:
            raise ControlError(503, "unavailable") from None
        finally:
            connection.close()

    async def send(self, request: Request) -> Reply:
        return await asyncio.to_thread(self._send, request)


class Worker:
    def __init__(self, transport: Transport, spool: Spool, boot: Boot):
        self.transport, self.spool, self.boot = transport, spool, boot

    def identity(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "worker_id": self.boot.worker_id,
            "session_id": self.boot.session_id,
        }

    def authority(self, lease: Lease) -> dict[str, object]:
        return self.identity() | {
            "job_id": lease.job_id,
            "attempt_id": lease.attempt_id,
            "fence": lease.fence,
        }

    async def start(self) -> None:
        await self.transport.send(
            Register.model_validate(
                self.identity() | {"action": "register", "generation": self.boot.generation}
            )
        )
        pending = self.spool.pending()
        if pending:
            if pending.delivery:
                # A new boot must explicitly acquire delivery-only authority; never resume a dial.
                try:
                    await self.transport.send(
                        Resume.model_validate(self.authority(pending.lease) | {"action": "resume"})
                    )
                except ControlError as exc:
                    if exc.status in (409, 410):
                        self.spool.clear()
                    raise
                updated = Deliver.model_validate(pending.delivery.model_dump() | self.identity())
                pending = Pending(lease=pending.lease, delivery=updated)
                self.spool.save(pending)
                await self.deliver(pending)
            else:
                # Registration expired the old attempt. Unstarted work may be re-leased;
                # issued work remains uncertain. Neither path reuses the old authority.
                self.spool.clear()

    async def deliver(self, pending: Pending) -> None:
        if pending.delivery is None:
            raise ValueError("missing durable result")
        for attempt in range(5):
            try:
                reply = await self.transport.send(pending.delivery)
                if reply.status not in ("inserted", "replayed"):
                    raise ControlError(503, "invalid_ack")
                self.spool.clear()
                return
            except ControlError as exc:
                if exc.status in (409, 410):
                    # Revoked/conflicting input must never become a replay reservoir.
                    self.spool.clear()
                    raise
                if exc.status not in (408, 429, 500, 503) or attempt == 4:
                    raise
                await asyncio.sleep(min(4, 0.25 * 2**attempt))

    async def step(self) -> bool:
        if self.spool.pending() is not None:
            raise ValueError("drain spool before claim")
        began = asyncio.get_running_loop().time()
        reply = await self.transport.send(
            Claim.model_validate(self.identity() | {"action": "claim"})
        )
        if reply.lease is None:
            if reply.status == "wait":
                await asyncio.sleep(min(1, reply.delay_seconds))
                return True
            return False
        lease = reply.lease
        config = lease.settings.measurement
        if (
            not config.enabled
            or lease.settings.sha256 != lease.config_sha256
            or lease.policy_sha256 != POLICY_SHA256
            or str(lease.endpoint.address) not in ("127.0.0.1", "::1")
            or denial(lease.endpoint.address, config, lab=True)
        ):
            raise ValueError("invalid job policy")
        self.spool.save(Pending(lease=lease))
        work = asyncio.create_task(self.measure(lease, began + lease.remaining_seconds))

        async def heartbeat() -> None:
            while True:
                await asyncio.sleep(HEARTBEAT_SECONDS)
                await self.transport.send(
                    Heartbeat.model_validate(self.authority(lease) | {"action": "heartbeat"})
                )

        watcher = asyncio.create_task(heartbeat())
        try:
            done, _ = await asyncio.wait({work, watcher}, return_when=asyncio.FIRST_COMPLETED)
            if watcher in done:
                await watcher  # Failure stops and closes active collector sockets.
                raise ControlError(503, "heartbeat_stopped")
            pending = await work
        except BaseException:
            work.cancel()
            await asyncio.gather(work, return_exceptions=True)
            raise
        finally:
            watcher.cancel()
            await asyncio.gather(watcher, return_exceptions=True)
        if pending is None:
            await self.transport.send(
                Abandon.model_validate(self.authority(lease) | {"action": "abandon"})
            )
            self.spool.clear()
            return True
        await self.deliver(pending)
        return True

    async def measure(self, lease: Lease, campaign_deadline: float) -> Pending | None:
        config = lease.settings.measurement
        loop = asyncio.get_running_loop()
        connections = 0
        started = datetime.now(UTC)

        async def admit() -> bool:
            nonlocal connections, started
            while loop.time() < campaign_deadline:
                began = loop.time()
                reply = await self.transport.send(
                    Permit.model_validate(
                        self.authority(lease) | {"action": "permit", "connection": connections + 1}
                    )
                )
                if reply.status == "wait":
                    await asyncio.sleep(
                        min(reply.delay_seconds, max(0, campaign_deadline - loop.time()))
                    )
                    continue
                if reply.status != "granted" or loop.time() - began >= reply.valid_seconds:
                    # Never retry an uncertain/expired grant, even when no local dial happened.
                    raise ControlError(410, "permit_expired")
                if loop.time() >= campaign_deadline or denial(
                    lease.endpoint.address, config, lab=True
                ):
                    return False
                if connections == 0:
                    started = datetime.now(UTC)
                connections += 1
                return True
            return False

        async with asyncio.timeout_at(campaign_deadline):
            evidence = service = None
            if config.protocol_evidence:
                collected = await collect(lease.endpoint, config, admit)
                if collected is None:
                    return None
                outcome, error = collected.outcome, collected.error
                evidence, service = collected.evidence, collected.service
            else:
                if not await admit():
                    return None
                outcome, error = await connect(lease.endpoint, config.connect_timeout_seconds)
            source = Observation(
                observation_id=lease.observation_id,
                target=Target(
                    address=lease.endpoint.address,
                    source="loopback-lab",
                    campaign_id=str(lease.campaign_id),
                ),
                endpoint=lease.endpoint,
                scanner=ScannerNode(node_id=str(self.boot.worker_id), software_version=__version__),
                config_sha256=lease.config_sha256,
                started_at=started,
                finished_at=max(started, datetime.now(UTC)),
                outcome=outcome,
                error_code=error,
                protocol_evidence=evidence,
                service=service,
            )
            delivery = Deliver.model_validate(
                self.authority(lease)
                | {
                    "action": "deliver",
                    "observation": source,
                    "source_sha256": digest(canonical(source)),
                }
            )
            pending = Pending(lease=lease, delivery=delivery)
            # No await from completed capture to fsynced slot; cancellation cannot drop a result.
            self.spool.save(pending)
            return pending
