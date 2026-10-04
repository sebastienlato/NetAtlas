"""Port-independent two-connection plan; discovery supplies admission for EVERY dial."""

import asyncio
import base64
import errno
import socket
import ssl
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from netatlas.collectors.io import ByteLimit, Channel, Counters, SocketChannel
from netatlas.collectors.protocols import Parsed, inspect
from netatlas.collectors.tls import TlsCollector
from netatlas.config import MeasurementSettings
from netatlas.domain import CapturedResponse, Endpoint, Outcome, Protocol, Service
from netatlas.evidence import Exchange, ProtocolEvidence, TlsMetadata

STRATEGY = "greeting-http-tls-v1"
type Admission = Callable[[], Awaitable[bool]]


def capture(
    data: bytes, *, truncated: bool = False, media: str = "application/octet-stream"
) -> CapturedResponse:
    return CapturedResponse(
        body_base64=base64.b64encode(data).decode("ascii"), truncated=truncated, media_type=media
    )


def connect_error(exc: OSError) -> tuple[Outcome, str]:
    if exc.errno == errno.ECONNREFUSED:
        return Outcome.CLOSED, "connection_refused"
    if exc.errno == errno.ETIMEDOUT:
        return Outcome.TIMEOUT, "connect_timeout"
    if exc.errno in {errno.ENETUNREACH, errno.EHOSTUNREACH}:
        return Outcome.ERROR, "network_unreachable"
    if exc.errno in {errno.EACCES, errno.EPERM}:
        return Outcome.ERROR, "local_permission_denied"
    return Outcome.ERROR, "socket_error"


@dataclass
class Attempt:
    number: int
    outcome: Outcome = Outcome.TIMEOUT
    status: str = "connect_failed"
    error: str | None = "connect_timeout"
    raw: bytearray = field(default_factory=bytearray)
    parsed: Parsed = field(default_factory=Parsed)
    tls: TlsMetadata | None = None
    allow_tls: bool = False
    http_request_sent: bool = False

    def freeze(self) -> Exchange:
        return Exchange.model_validate(
            {
                "connection": self.number,
                "probe": "greeting-http" if self.number == 1 else "tls",
                "tcp_outcome": self.outcome,
                "status": self.status,
                "error_code": self.error,
                "response": capture(bytes(self.raw), truncated=self.status != "complete")
                if self.raw
                else None,
                "http_request_sent": self.http_request_sent,
                "http": self.parsed.http.model_copy(update={"host_source": "target-ip"})
                if self.parsed.http and self.http_request_sent
                else self.parsed.http,
                "ssh": self.parsed.ssh,
                "smtp": self.parsed.smtp,
                "tls": self.tls,
                "candidates": self.parsed.candidates,
            }
        )


@dataclass
class Collected:
    outcome: Outcome
    error: str | None
    service: Service | None
    evidence: ProtocolEvidence


async def application(
    channel: Channel,
    endpoint: Endpoint,
    config: MeasurementSettings,
    count: Counters,
    attempt: Attempt,
) -> None:
    async def read() -> bytes:
        remaining = config.max_response_bytes - count.retained
        if remaining <= 0:
            raise ByteLimit
        chunk = await channel.read(min(1024, remaining))
        attempt.raw.extend(chunk)
        count.retained += len(chunk)
        attempt.parsed = inspect(bytes(attempt.raw), eof=not chunk)
        return chunk

    try:
        async with asyncio.timeout(config.greeting_timeout_seconds):
            first = await read()
    except TimeoutError:
        # No bytes received. One ordinary GET; no cookies, credentials, redirect,
        # decompression, resource fetch, content negotiation or DNS.
        attempt.allow_tls = True
        host = str(endpoint.address)
        if endpoint.address.version == 6:
            host = f"[{host}]"
        request = (
            f"GET / HTTP/1.1\r\nHost: {host}:{endpoint.port}\r\n"
            f"User-Agent: {config.user_agent}\r\nConnection: close\r\n\r\n"
        ).encode("ascii")
        await channel.write(request)
        attempt.http_request_sent = True
    else:
        if not first:
            attempt.allow_tls = True
    while not attempt.parsed.done:
        await read()
    attempt.status = attempt.parsed.status


async def interact(
    endpoint: Endpoint,
    config: MeasurementSettings,
    count: Counters,
    attempt: Attempt,
) -> None:
    family = socket.AF_INET if endpoint.address.version == 4 else socket.AF_INET6
    try:
        with socket.socket(family, socket.SOCK_STREAM) as sock:
            sock.setblocking(False)
            async with asyncio.timeout(config.connect_timeout_seconds):
                await asyncio.get_running_loop().sock_connect(
                    sock, (str(endpoint.address), endpoint.port)
                )
            attempt.outcome, attempt.error = Outcome.OPEN, None
            attempt.status = "unknown"
            raw = SocketChannel(sock, config, count)
            async with asyncio.timeout(config.interaction_timeout_seconds):
                if attempt.number == 2:
                    collector = TlsCollector(raw)
                    attempt.tls = await collector.collect(config, count)
                    tls = collector.channel
                    await application(tls, endpoint, config, count, attempt)
                else:
                    await application(raw, endpoint, config, count, attempt)
    except TimeoutError:
        if attempt.outcome == Outcome.OPEN:
            attempt.status = "interaction_timeout"
    except ByteLimit:
        attempt.status = "byte_limit"
    except ssl.SSLError:
        attempt.status, attempt.error = "tls_error", "tls_handshake_or_record_error"
    except OSError as exc:
        if attempt.outcome == Outcome.OPEN:
            attempt.status, attempt.error = "transport_error", "socket_error"
        else:
            attempt.outcome, attempt.error = connect_error(exc)


def recognized(attempt: Attempt) -> bool:
    return any(
        (
            attempt.parsed.http,
            attempt.parsed.ssh,
            attempt.parsed.smtp,
            attempt.parsed.candidates,
            attempt.tls,
        )
    )


async def collect(
    endpoint: Endpoint, config: MeasurementSettings, admit: Admission
) -> Collected | None:
    if not await admit():
        return None
    count = Counters()
    attempts: list[Attempt] = []
    termination = "finished"
    active: Attempt | None = None
    try:
        async with asyncio.timeout(config.endpoint_timeout_seconds):
            for number in range(1, config.max_connections_per_endpoint + 1):
                # Callback waits on the shared pacer, rechecks policy/stop state,
                # counts the actual attempt, and returns without an intervening await.
                if number > 1 and not await admit():
                    termination = "admission_stopped"
                    break
                attempt = Attempt(number)
                attempts.append(attempt)
                active = attempt
                await interact(endpoint, config, count, attempt)
                active = None
                if attempt.status == "byte_limit":
                    termination = "byte_limit"
                    break
                if attempt.outcome != Outcome.OPEN or recognized(attempt) or not attempt.allow_tls:
                    break
            else:
                if attempts and not recognized(attempts[-1]):
                    termination = "connection_limit"
    except TimeoutError:
        termination = "endpoint_timeout"
        if active is not None:
            active.status = "endpoint_timeout"
            if active.outcome != Outcome.OPEN:
                active.error = "endpoint_timeout"
    if not attempts:
        return None
    connected = any(attempt.outcome == Outcome.OPEN for attempt in attempts)
    protocols: set[Protocol] = set()
    for attempt in attempts:
        if attempt.parsed.http:
            protocols.add(Protocol.HTTP)
        if attempt.parsed.ssh:
            protocols.add(Protocol.SSH)
        if attempt.parsed.smtp:
            protocols.add(Protocol.SMTP)
    has_tls = any(attempt.tls is not None for attempt in attempts)
    protocol = (
        next(iter(protocols))
        if len(protocols) == 1
        else Protocol.TLS
        if has_tls and not protocols
        else Protocol.UNKNOWN
    )
    return Collected(
        outcome=Outcome.OPEN if connected else attempts[0].outcome,
        error=None if connected else attempts[0].error,
        service=Service(protocol=protocol, tls=has_tls) if connected else None,
        evidence=ProtocolEvidence.model_validate(
            {
                "strategy": STRATEGY,
                "exchanges": tuple(attempt.freeze() for attempt in attempts),
                "received_bytes": count.received,
                "sent_bytes": count.sent,
                "retained_bytes": count.retained,
                "termination": termination,
            }
        ),
    )
