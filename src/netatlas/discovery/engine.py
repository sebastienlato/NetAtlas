"""A bounded local campaign. Completed observations are flushed before yielding."""

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from netatlas import __version__
from netatlas.collectors.runner import collect
from netatlas.config import Settings
from netatlas.discovery.budget import Budget
from netatlas.discovery.policy import denial
from netatlas.discovery.scope import Scope
from netatlas.discovery.spool import Spool
from netatlas.discovery.tcp import connect
from netatlas.domain import Endpoint, Outcome, ScannerNode, Target
from netatlas.observation import Observation

type Connector = Callable[[Endpoint, float], Awaitable[tuple[Outcome, str | None]]]
logger = logging.getLogger("netatlas.discovery")


async def run_campaign(
    settings: Settings,
    scope: Scope,
    *,
    root: Path = Path("data"),
    stop: asyncio.Event | None = None,
    connector: Connector = connect,
) -> dict[str, object]:
    # Revalidate the public boundary, including callers using model_copy/construct.
    settings = Settings.model_validate(settings.model_dump())
    scope = Scope.model_validate(scope.model_dump())
    config = settings.measurement
    if not config.enabled:
        raise ValueError("measurement is disabled")
    scope.networks(config)
    stopping = stop or asyncio.Event()
    campaign_id = uuid4()
    scanner = ScannerNode(node_id=config.node_id, software_version=__version__)
    queue: asyncio.Queue[Endpoint | None] = asyncio.Queue(maxsize=config.queue_size)
    budget = Budget(config.global_connections_per_second, config.per_prefix_connections_per_second)
    attempted = 0
    connection_attempted = 0
    clock = asyncio.get_running_loop().time
    deadline = clock() + config.campaign_timeout_seconds

    def halted() -> bool:
        return stopping.is_set() or clock() >= deadline

    with Spool(root, campaign_id, settings, scope) as spool:

        async def produce() -> None:
            for endpoint in scope.endpoints(config):
                if halted():
                    return
                await queue.put(endpoint)
            for _ in range(config.max_concurrency):
                if halted():
                    return
                await queue.put(None)

        async def worker() -> None:
            nonlocal attempted, connection_attempted
            while not halted():
                endpoint = await queue.get()
                if endpoint is None or halted():
                    return
                started = datetime.now(UTC)
                admitted = False
                selected: Endpoint = endpoint

                async def admit(endpoint: Endpoint = selected) -> bool:
                    nonlocal attempted, connection_attempted, admitted, started
                    await budget.acquire(endpoint.address)
                    if (
                        halted()
                        or denial(endpoint.address, config, lab=scope.lab_loopback) is not None
                    ):
                        return False
                    if not admitted:
                        started = datetime.now(UTC)
                        attempted += 1
                        admitted = True
                    connection_attempted += 1
                    return True

                evidence = None
                service = None
                if config.protocol_evidence:
                    result = await collect(endpoint, config, admit)
                    if result is None:
                        continue
                    outcome, error = result.outcome, result.error
                    evidence, service = result.evidence, result.service
                else:
                    if not await admit():
                        continue
                    outcome, error = await connector(endpoint, config.connect_timeout_seconds)
                observation = Observation(
                    observation_id=uuid4(),
                    target=Target(
                        address=endpoint.address,
                        source="loopback-lab" if scope.lab_loopback else "explicit-scope",
                        campaign_id=str(campaign_id),
                    ),
                    endpoint=endpoint,
                    scanner=scanner,
                    config_sha256=settings.sha256,
                    started_at=started,
                    finished_at=max(started, datetime.now(UTC)),
                    outcome=outcome,
                    error_code=error,
                    protocol_evidence=evidence,
                    service=service,
                )
                # No await between completion and flush: cancellation cannot drop it.
                spool.append(observation)
                logger.info(
                    json.dumps(
                        {
                            "event": "connect_completed",
                            "campaign_id": str(campaign_id),
                            "observation_id": str(observation.observation_id),
                            "outcome": outcome.value,
                        }
                    )
                )

        async def pipeline() -> None:
            async with asyncio.TaskGroup() as group:
                group.create_task(produce())
                for _ in range(config.max_concurrency):
                    group.create_task(worker())

        work = asyncio.create_task(pipeline())
        watcher = asyncio.create_task(stopping.wait())
        status = "failed"
        try:
            done, _ = await asyncio.wait(
                {work, watcher},
                timeout=max(0, deadline - clock()),
                return_when=asyncio.FIRST_COMPLETED,
            )
            if stopping.is_set():
                status = "cancelled"
            elif work in done:
                await work
                status = "deadline_exceeded" if clock() >= deadline else "completed"
            else:
                status = "deadline_exceeded"
        except asyncio.CancelledError:
            status = "cancelled"
            raise
        finally:
            stopping.set()
            work.cancel()
            watcher.cancel()
            cleanup = asyncio.gather(work, watcher, return_exceptions=True)
            interrupted = False
            while not cleanup.done():
                try:
                    await asyncio.shield(cleanup)
                except asyncio.CancelledError:
                    # Repeated stop requests must not interrupt resource cleanup.
                    interrupted = True
                    status = "cancelled"
            spool.manifest["connection_attempted"] = connection_attempted
            spool.finish(status, attempted)
            logger.info(
                json.dumps(
                    {
                        "event": "campaign_finished",
                        "campaign_id": str(campaign_id),
                        "status": status,
                        "completed": spool.completed,
                    }
                )
            )
            if interrupted:
                raise asyncio.CancelledError
        return spool.manifest
