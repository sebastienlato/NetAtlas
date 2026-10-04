"""Synthetic parsers and explicit loopback peers; never public measurement."""

import asyncio
import base64
import errno
import json
import logging
import socket
import ssl
import subprocess
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager, suppress
from ipaddress import ip_address
from pathlib import Path

import pytest
from pydantic import ValidationError

from netatlas.collectors.io import SocketChannel
from netatlas.collectors.protocols import inspect
from netatlas.collectors.runner import Collected, collect
from netatlas.config import MeasurementSettings, Settings
from netatlas.discovery import engine
from netatlas.discovery.engine import run_campaign
from netatlas.discovery.policy import denial
from netatlas.discovery.scope import Scope
from netatlas.domain import Endpoint, ObservationV1, Outcome, Protocol
from netatlas.evidence import ProtocolEvidence
from netatlas.examples import example_observation
from netatlas.observation import Observation, observation_reader


def settings(**overrides: object) -> Settings:
    return Settings.model_validate(
        {
            "measurement": {
                "enabled": True,
                "protocol_evidence": True,
                "operator_name": "Fixture Researcher",
                "operator_contact": "research@example.org",
                "user_agent": "NetAtlas/0.3 (research; fixture)",
                "greeting_timeout_seconds": 0.02,
                "interaction_timeout_seconds": 0.2,
                "endpoint_timeout_seconds": 2,
                "connect_timeout_seconds": 0.2,
                "global_connections_per_second": 100,
                "per_prefix_connections_per_second": 20,
                "max_concurrency": 2,
                **overrides,
            }
        }
    )


type Peer = Callable[[asyncio.StreamReader, asyncio.StreamWriter], Awaitable[None]]


@asynccontextmanager
async def fixture(
    peer: Peer, *, tls: ssl.SSLContext | None = None, host: str = "127.0.0.1"
) -> AsyncIterator[Endpoint]:
    tasks: set[asyncio.Task[None]] = set()
    errors: list[BaseException] = []

    async def wrapped(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        original_transport = writer.transport
        try:
            if tls is not None:
                # Own the writer before starting TLS, including failed handshakes.
                await writer.start_tls(tls, ssl_handshake_timeout=1)
            await peer(reader, writer)
        except ConnectionError, ssl.SSLError:
            pass  # Bounded collectors deliberately close before oversized peer writes finish.
        except BaseException as exc:
            if not isinstance(exc, asyncio.CancelledError):
                errors.append(exc)
        finally:
            writer.close()
            original_transport.abort()
            # A failed start_tls may never notify the original stream protocol.
            with suppress(ConnectionError, ssl.SSLError, TimeoutError):
                await asyncio.wait_for(writer.wait_closed(), 0.2)

    def connected(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        task = asyncio.create_task(wrapped(reader, writer))
        tasks.add(task)
        task.add_done_callback(tasks.discard)

    # Own the accept task and its transports explicitly. Server.close() races
    # asyncio's untracked transport-creation callbacks during very short TLS peers.
    # A fixed number of sleep(0) calls cannot guarantee those callbacks have drained.
    loop = asyncio.get_running_loop()
    transports: set[asyncio.Transport] = set()
    listener = socket.socket(socket.AF_INET6 if ":" in host else socket.AF_INET)
    listener.setblocking(False)
    listener.bind((host, 0))
    listener.listen()

    async def accept() -> None:
        while True:
            accepted, _ = await loop.sock_accept(listener)
            try:
                transport, _ = await loop.connect_accepted_socket(
                    lambda: asyncio.StreamReaderProtocol(asyncio.StreamReader(), connected),
                    accepted,
                )
            except BaseException:
                accepted.close()
                raise
            transports.add(transport)

    accept_task = asyncio.create_task(accept())
    try:
        yield Endpoint(address=ip_address(host), port=listener.getsockname()[1])
    finally:
        accept_task.cancel()
        await asyncio.gather(accept_task, return_exceptions=True)
        listener.close()
        for transport in transports:
            transport.abort()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    assert not errors


async def admitted_collect(endpoint: Endpoint, **overrides: object) -> Collected:
    admissions = 0

    async def admit() -> bool:
        nonlocal admissions
        admissions += 1
        return True

    config = settings(**overrides).measurement
    result = await collect(endpoint, config, admit)
    assert result is not None
    assert admissions == len(result.evidence.exchanges)
    assert result.evidence.received_bytes <= config.max_response_bytes
    assert result.evidence.retained_bytes <= config.max_response_bytes
    assert result.evidence.sent_bytes <= config.max_sent_bytes
    return result


@pytest.mark.parametrize(
    "payload,protocol,status",
    [
        (b"SSH-2.0-Synthetic_1 comments\r\n", Protocol.SSH, "complete"),
        (b"notice\r\nSSH-1.99-Synthetic\r\n", Protocol.SSH, "complete"),
        (b"220-mail.example.org ESMTP synthetic\r\n220 ready\r\n", Protocol.SMTP, "complete"),
        (b"220 ftp.example.org ready\r\n", Protocol.UNKNOWN, "ambiguous"),
        (b"220 smtp.example.org ready\r\n", Protocol.UNKNOWN, "ambiguous"),
        (b"SSH-2.0-\x00bad\r\n", Protocol.UNKNOWN, "malformed"),
        (b"220 bad\x00SMTP\r\n", Protocol.UNKNOWN, "malformed"),
        (b"\x00\xff\x1b[2J<script>hostile</script>", Protocol.UNKNOWN, "unknown"),
    ],
)
def test_greetings_on_unconventional_ports_never_send_commands(
    payload: bytes, protocol: Protocol, status: str
) -> None:
    async def exercise() -> None:
        received: list[bytes] = []
        eof = asyncio.Event()

        async def peer(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            try:
                # Fragment the greeting, including the protocol prefix.
                for chunk in (payload[:2], payload[2:]):
                    writer.write(chunk)
                    await writer.drain()
                    await asyncio.sleep(0)
                received.append(await reader.read())
            except ConnectionError:
                received.append(b"")  # Early binary rejection may reset unread peer data.
            finally:
                eof.set()

        async with fixture(peer) as endpoint:
            assert endpoint.port not in {22, 25, 80, 443, 465, 587}
            result = await admitted_collect(endpoint)
            await asyncio.wait_for(eof.wait(), 1)
        assert result.outcome == Outcome.OPEN and result.error is None
        assert result.service and result.service.protocol == protocol
        exchange = result.evidence.exchanges[0]
        assert exchange.status == status and exchange.response
        assert payload.startswith(base64.b64decode(exchange.response.body_base64))
        assert len(result.evidence.exchanges) == 1
        assert received == [b""] and result.evidence.sent_bytes == 0
        if status == "ambiguous":
            assert exchange.candidates == (Protocol.SMTP, Protocol.FTP)

    asyncio.run(exercise())


def test_http_request_redirect_hostile_body_and_header_metadata(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    async def exercise() -> None:
        requests: list[bytes] = []
        body = b'<script>fetch("https://example.org/secret")</script>\x00\xff\x1b[2J'
        response = (
            b"HTTP/1.1 302 Found\r\nLocation: https://example.org/secret\r\n"
            b"Set-Cookie: fixture=untrusted\r\nX-Synthetic: one\r\nX-Synthetic: two\r\n"
            + f"Content-Length: {len(body)}\r\n\r\n".encode()
            + body
        )

        async def peer(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            requests.append(await reader.readuntil(b"\r\n\r\n"))
            for chunk in (response[:9], response[9:50], response[50:]):
                writer.write(chunk)
                await writer.drain()
                await asyncio.sleep(0)
            assert await reader.read() == b""

        async with fixture(peer) as endpoint:
            scope = Scope(
                targets=(str(endpoint.address),), ports=(endpoint.port,), lab_loopback=True
            )
            manifest = await run_campaign(settings(), scope, root=tmp_path)
        directory = tmp_path / str(manifest["campaign_id"])
        observation = Observation.model_validate_json(
            (directory / "observations.jsonl").read_text()
        )
        evidence = observation.protocol_evidence
        assert evidence and evidence.exchanges[0].http
        http = evidence.exchanges[0].http
        assert http.status == 302 and http.headers_complete
        assert http.headers[2:4] == (("X-Synthetic", "one"), ("X-Synthetic", "two"))
        raw = evidence.exchanges[0].response
        assert raw and not raw.truncated and base64.b64decode(raw.body_base64) == response
        assert evidence.received_bytes == len(response) == evidence.retained_bytes
        assert evidence.sent_bytes == len(requests[0])
        assert len(requests) == manifest["connection_attempted"] == 1
        assert (
            requests[0]
            == (
                f"GET / HTTP/1.1\r\nHost: 127.0.0.1:{endpoint.port}\r\n"
                "User-Agent: NetAtlas/0.3 (research; fixture)\r\nConnection: close\r\n\r\n"
            ).encode()
        )
        assert observation.service and observation.service.protocol == Protocol.HTTP
        assert manifest["observation_schema_version"] == 2 and manifest["manifest_version"] == 2
        assert manifest["preview"] == scope.preview(settings().measurement)

    caplog.set_level(logging.INFO, logger="netatlas.discovery")
    asyncio.run(exercise())
    assert "hostile" not in caplog.text and "fixture=untrusted" not in caplog.text
    assert "127.0.0.1" not in caplog.text and "secret" not in caplog.text


@pytest.mark.parametrize(
    "response,expected",
    [
        (b"HTTP/1.1 200 OK\r\nBad Header\r\n\r\nx", "malformed"),
        (b"HTTP/1.1 200 OK\r\nX: \x1b[2J\r\n\r\nx", "malformed"),
        (b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\nContent-Length: 5\r\n\r\nx", "malformed"),
        (b"HTTP/1.1 200 OK\r\nContent-Length: 20\r\n\r\nx", "eof"),
        (b"HTTP/1.1 200 OK\r\n" + b"X: value\r\n" * 33 + b"\r\n", "malformed"),
        (b"HTTP/1.1 200 OK\r\nX: " + b"a" * 9000, "malformed"),
    ],
)
def test_malformed_http_is_bounded_and_does_not_erase_reachability(
    response: bytes, expected: str
) -> None:
    async def exercise() -> None:
        async def peer(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            await reader.readuntil(b"\r\n\r\n")
            writer.write(response)
            await writer.drain()

        async with fixture(peer) as endpoint:
            result = await admitted_collect(endpoint)
        assert result.outcome == Outcome.OPEN and result.service
        assert result.service.protocol == Protocol.HTTP
        assert result.evidence.exchanges[0].status == expected
        assert result.evidence.received_bytes <= 8192
        assert len(result.evidence.exchanges) == 1

    asyncio.run(exercise())


@pytest.mark.parametrize("mode", ["receive", "send", "interaction", "endpoint", "connection"])
def test_cumulative_limits_and_deadlines(mode: str) -> None:
    async def exercise() -> None:
        peers = 0
        requests: list[bytes] = []

        async def peer(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            nonlocal peers
            peers += 1
            requests.append(await reader.read(8192))
            if mode == "receive":
                writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 99999\r\n\r\n" + b"z" * 10000)
                await writer.drain()
            elif mode == "connection":
                writer.write(b"not http\r\n")
                await writer.drain()
                return
            await reader.read()

        overrides: dict[str, object] = {"max_connections_per_endpoint": 1}
        if mode == "receive":
            overrides["max_response_bytes"] = 128
        if mode == "send":
            overrides["max_sent_bytes"] = 1
        if mode == "interaction":
            overrides["interaction_timeout_seconds"] = 0.08
        if mode == "endpoint":
            overrides.update(endpoint_timeout_seconds=0.08, interaction_timeout_seconds=1)
        async with fixture(peer) as endpoint:
            start = asyncio.get_running_loop().time()
            result = await admitted_collect(endpoint, **overrides)
            elapsed = asyncio.get_running_loop().time() - start
            await asyncio.sleep(0.01)
        assert result.outcome == Outcome.OPEN and peers == 1
        exchange = result.evidence.exchanges[0]
        if mode in {"receive", "send"}:
            assert result.evidence.termination == exchange.status == "byte_limit"
            if mode == "receive":
                assert result.evidence.received_bytes == result.evidence.retained_bytes == 128
                assert exchange.response and exchange.response.truncated
                assert exchange.http and exchange.http.status == 200
            else:
                assert result.evidence.sent_bytes == 0 and requests == [b""]
        elif mode in {"interaction", "endpoint"}:
            assert 0.06 <= elapsed < 0.5
            assert exchange.status == f"{mode}_timeout"
        else:
            assert result.evidence.termination == "connection_limit"
            assert result.service and result.service.protocol == Protocol.UNKNOWN

    asyncio.run(exercise())


@pytest.fixture
def tls_context(tmp_path: Path) -> tuple[ssl.SSLContext, bytes, list[str | None]]:
    # Ephemeral synthetic key/certificate generated only in the test temp directory.
    key, cert = tmp_path / "key.pem", tmp_path / "cert.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "1",
            "-subj",
            "/CN=untrusted.example.invalid",
            "-keyout",
            str(key),
            "-out",
            str(cert),
        ],
        check=True,
        capture_output=True,
    )
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)
    context.set_alpn_protocols(["http/1.1"])
    sni: list[str | None] = []

    def received_sni(sock: object, name: str | None, ctx: object) -> None:
        sni.append(name)

    context.set_servername_callback(received_sni)
    return context, ssl.PEM_cert_to_DER_cert(cert.read_text()), sni


def test_tls_self_signed_cert_https_and_cumulative_wire_budgets(
    tls_context: tuple[ssl.SSLContext, bytes, list[str | None]], monkeypatch: pytest.MonkeyPatch
) -> None:
    async def exercise() -> None:
        context, der, sni = tls_context
        received = sent = 0
        original_read, original_write = SocketChannel.read, SocketChannel.write

        async def read(channel: SocketChannel, size: int) -> bytes:
            nonlocal received
            data = await original_read(channel, size)
            received += len(data)
            return data

        async def write(channel: SocketChannel, data: bytes) -> None:
            nonlocal sent
            await original_write(channel, data)
            sent += len(data)

        monkeypatch.setattr(SocketChannel, "read", read)
        monkeypatch.setattr(SocketChannel, "write", write)

        async def peer(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            request = await reader.readuntil(b"\r\n\r\n")
            assert b"GET / HTTP/1.1" in request
            writer.write(b"HTTP/1.1 204 No Content\r\n\r\n")
            await writer.drain()
            await reader.read()

        async with fixture(peer, tls=context) as endpoint:
            result = await admitted_collect(endpoint)
        assert result.service and result.service.protocol == Protocol.HTTP and result.service.tls
        assert len(result.evidence.exchanges) == 2 and sni == [None]
        exchange = result.evidence.exchanges[1]
        assert exchange.tls and exchange.http and exchange.http.status == 204
        assert exchange.tls.verification == "not_performed" and exchange.tls.sni is None
        assert base64.b64decode(exchange.tls.certificates[0].body_base64) == der
        assert not exchange.tls.chain_truncated
        assert exchange.tls.version in {"TLSv1.2", "TLSv1.3"} and exchange.tls.secret_bits >= 128
        assert exchange.tls.alpn == "http/1.1"
        assert result.evidence.received_bytes == received
        assert result.evidence.sent_bytes == sent
        assert result.evidence.retained_bytes == len(der) + len(b"HTTP/1.1 204 No Content\r\n\r\n")

    asyncio.run(exercise())


def test_all_connections_share_admission_policy_pacing_and_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def exercise() -> None:
        starts: list[float] = []
        original_connect = asyncio.get_running_loop().sock_connect

        async def dial(sock: socket.socket, address: tuple[str, int]) -> None:
            starts.append(asyncio.get_running_loop().time())
            await original_connect(sock, address)

        monkeypatch.setattr(asyncio.get_running_loop(), "sock_connect", dial)

        async def peer(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            await reader.read(8192)
            writer.write(b"\x00not http or tls")
            await writer.drain()

        async with fixture(peer) as first, fixture(peer) as second:
            scope = Scope(
                targets=("127.0.0.1",), ports=(first.port, second.port), lab_loopback=True
            )
            manifest = await run_campaign(settings(), scope, root=tmp_path / "paced")
            assert manifest["connection_attempted"] == 4 and manifest["completed"] == 2
            assert all(b - a >= 0.049 for a, b in zip(starts, starts[1:], strict=False))
            starts.clear()
            checks = 0
            original_denial = denial

            def deny_second(
                address: object, config: MeasurementSettings, *, lab: bool = False
            ) -> str | None:
                nonlocal checks
                checks += 1
                if checks == 2:
                    return "opt_out"
                return original_denial(ip_address(str(address)), config, lab=lab)

            monkeypatch.setattr(engine, "denial", deny_second)
            manifest = await run_campaign(
                settings(),
                Scope(targets=("127.0.0.1",), ports=(first.port,), lab_loopback=True),
                root=tmp_path / "denied",
            )
            assert manifest["connection_attempted"] == len(starts) == 1 and checks == 2

    asyncio.run(exercise())


@pytest.mark.parametrize("method", ["event", "task", "deadline"])
def test_protocol_cancellation_flushes_closes_and_stops_fallback(
    tmp_path: Path, method: str
) -> None:
    async def exercise() -> None:
        blocked = asyncio.Event()
        closed = asyncio.Event()
        stop = asyncio.Event()
        calls = 0

        async def peer(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            nonlocal calls
            calls += 1
            if calls == 1:
                writer.write(b"SSH-2.0-Synthetic\r\n")
                await writer.drain()
                await reader.read()
            else:
                blocked.set()
                await reader.read()
                closed.set()

        # Different ports ensure one complete observation then active work.
        async with fixture(peer) as endpoint, fixture(peer) as second:
            scope = Scope(
                targets=("127.0.0.1",), ports=(endpoint.port, second.port), lab_loopback=True
            )
            task = asyncio.create_task(
                run_campaign(
                    settings(
                        max_concurrency=1,
                        greeting_timeout_seconds=1,
                        interaction_timeout_seconds=1,
                        campaign_timeout_seconds=0.25,
                    ),
                    scope,
                    root=tmp_path,
                    stop=stop,
                )
            )
            await asyncio.wait_for(blocked.wait(), 1)
            if method == "task":
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
            else:
                if method == "event":
                    stop.set()
                await task
            await asyncio.wait_for(closed.wait(), 1)
        directory = next(path for path in tmp_path.iterdir() if path.is_dir())
        manifest = json.loads((directory / "manifest.json").read_text())
        assert manifest["completed"] == manifest["incomplete"] == 1
        assert manifest["connection_attempted"] == calls == 2
        assert manifest["status"] == ("deadline_exceeded" if method == "deadline" else "cancelled")
        assert len((directory / "observations.jsonl").read_text().splitlines()) == 1
        assert not [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]

    asyncio.run(exercise())


def test_protocol_connect_failure_semantics_and_socket_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        sockets: list[socket.socket] = []
        failure: int | None = None

        async def dial(sock: socket.socket, address: tuple[str, int]) -> None:
            sockets.append(sock)
            if failure is None:
                await asyncio.Future[None]()
            raise OSError(failure, "untrusted private error")

        monkeypatch.setattr(asyncio.get_running_loop(), "sock_connect", dial)
        endpoint = Endpoint(address=ip_address("192.0.2.1"), port=25)
        for injected, outcome, code in [
            (None, Outcome.TIMEOUT, "connect_timeout"),
            (errno.ECONNREFUSED, Outcome.CLOSED, "connection_refused"),
            (errno.EHOSTUNREACH, Outcome.ERROR, "network_unreachable"),
            (errno.EACCES, Outcome.ERROR, "local_permission_denied"),
            (errno.EMFILE, Outcome.ERROR, "socket_error"),
        ]:
            failure = injected
            result = await admitted_collect(endpoint, connect_timeout_seconds=0.01)
            assert result.outcome == outcome and result.error == code and result.service is None
            assert len(result.evidence.exchanges) == 1
        assert all(sock.fileno() == -1 for sock in sockets)

    asyncio.run(exercise())


def test_schema_versions_compatibility_and_preview_caps() -> None:
    current = example_observation(Settings())
    payload = current.model_dump(mode="json")
    legacy = {key: value for key, value in payload.items() if key != "protocol_evidence"}
    legacy["schema_version"] = 1
    old = observation_reader.validate_python(legacy)
    assert isinstance(old, ObservationV1) and old.schema_version == 1
    assert observation_reader.validate_python(payload) == current
    with pytest.raises(ValidationError):
        Observation.model_validate(legacy)
    with pytest.raises(ValidationError):
        ObservationV1.model_validate(payload)
    with pytest.raises(ValidationError):
        observation_reader.validate_python(payload | {"schema_version": 99})
    for patch in (
        {"config_version": 2},
        {"measurement": {"max_connections_per_endpoint": 3}},
        {"measurement": {"user_agent": "research \u2603"}},
    ):
        with pytest.raises(ValidationError):
            Settings.model_validate(patch)
    scope = Scope(targets=("127.0.0.1",), ports=(80, 80, 443), lab_loopback=True)
    preview = scope.preview(settings().measurement)
    plan = preview["interaction_plan"]
    assert isinstance(plan, dict) and plan["max_campaign_connections"] == 4
    plain = scope.preview(Settings().measurement)["interaction_plan"]
    assert isinstance(plain, dict) and plain["max_campaign_connections"] == 2
    assert plain["max_sent_bytes_per_endpoint"] == plain["max_received_bytes_per_endpoint"] == 0
    with pytest.raises(ValidationError):
        ProtocolEvidence.model_validate(
            {
                "exchanges": [
                    {
                        "connection": 1,
                        "probe": "greeting-http",
                        "tcp_outcome": "open",
                        "status": "unknown",
                    }
                ],
                "received_bytes": 0,
                "sent_bytes": 0,
                "retained_bytes": 1,
                "termination": "finished",
            }
        )


def test_fragmented_parser_and_cap_prefixes() -> None:
    valid = b"SSH-2.0-Synthetic\r\n"
    assert all(not inspect(valid[:index]).done for index in range(1, len(valid)))
    assert inspect(valid).ssh
    assert inspect(b"SSH-2.0-" + b"x" * 245 + b"\r\n").ssh
    assert inspect(b"SSH-2.0-" + b"x" * 300).status == "malformed"
    assert inspect(b"220-" + b"x" * 600).status == "malformed"


@pytest.mark.parametrize("mode", ["receive", "send", "slow", "smtp"])
def test_tls_limits_partial_handshake_and_non_http_protocol(
    tls_context: tuple[ssl.SSLContext, bytes, list[str | None]], mode: str
) -> None:
    async def exercise() -> None:
        context, _, _ = tls_context

        async def peer(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            if mode == "smtp":
                writer.write(b"220 mail.example.org ESMTP synthetic\r\n")
                await writer.drain()
                assert await reader.read() == b""
            else:
                await reader.read(8192)
                await reader.read()

        overrides: dict[str, object] = {}
        if mode == "receive":
            overrides["max_response_bytes"] = 128
        if mode == "send":
            overrides["max_sent_bytes"] = 200
        async with fixture(peer, tls=context) as endpoint:
            result = await admitted_collect(endpoint, **overrides)
        assert result.outcome == Outcome.OPEN
        assert len(result.evidence.exchanges) == 2
        exchange = result.evidence.exchanges[1]
        if mode in {"receive", "send"}:
            assert exchange.status == result.evidence.termination == "byte_limit"
            assert exchange.tls is None
        elif mode == "slow":
            assert exchange.tls and exchange.status == "interaction_timeout"
            assert result.service and result.service.protocol == Protocol.TLS
        else:
            assert exchange.tls and exchange.smtp and not exchange.http_request_sent
            assert (
                result.service and result.service.protocol == Protocol.SMTP and result.service.tls
            )

    asyncio.run(exercise())


def test_endpoint_deadline_includes_fallback_admission_but_not_first_wait() -> None:
    async def exercise() -> None:
        admissions = 0
        calls = 0

        async def peer(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            nonlocal calls
            calls += 1
            await reader.read(8192)
            writer.write(b"\x00unknown")
            await writer.drain()

        async def admit() -> bool:
            nonlocal admissions
            admissions += 1
            await asyncio.sleep(0.1)
            return True

        async with fixture(peer) as endpoint:
            result = await collect(
                endpoint, settings(endpoint_timeout_seconds=0.05).measurement, admit
            )
        assert result and result.outcome == Outcome.OPEN
        assert calls == 1 and admissions == 2
        assert result.evidence.termination == "endpoint_timeout"
        assert len(result.evidence.exchanges) == 1

    asyncio.run(exercise())


def test_ipv6_http_host_and_no_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    async def exercise() -> None:
        requests: list[bytes] = []

        async def peer(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            requests.append(await reader.readuntil(b"\r\n\r\n"))
            writer.write(b"HTTP/1.1 204 No Content\r\n\r\n")
            await writer.drain()

        async def forbidden(*args: object, **kwargs: object) -> object:
            raise AssertionError("numeric probes must never resolve names")

        try:
            async with fixture(peer, host="::1") as endpoint:
                monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", forbidden)
                result = await admitted_collect(endpoint)
                assert f"Host: [::1]:{endpoint.port}\r\n".encode() in requests[0]
                exchange = result.evidence.exchanges[0]
                assert exchange.http_request_sent and exchange.http
                assert exchange.http.host_source == "target-ip"
        except OSError as exc:
            if exc.errno in {errno.EAFNOSUPPORT, errno.EADDRNOTAVAIL}:
                pytest.skip("host has no IPv6 loopback")
            raise

    asyncio.run(exercise())


@pytest.mark.parametrize("stage", ["handshake", "application"])
def test_cancel_during_tls_closes_owned_socket(
    tmp_path: Path, tls_context: tuple[ssl.SSLContext, bytes, list[str | None]], stage: str
) -> None:
    async def exercise() -> None:
        ready, closed, stop = asyncio.Event(), asyncio.Event(), asyncio.Event()
        calls = 0

        async def peer(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            nonlocal calls
            calls += 1
            request = await reader.read(8192)
            if stage == "handshake" and calls == 1:
                assert request.startswith(b"GET / ")
                return
            if stage == "handshake":
                assert request.startswith(b"\x16\x03")
            ready.set()
            await reader.read()
            closed.set()

        async with fixture(
            peer, tls=tls_context[0] if stage == "application" else None
        ) as endpoint:
            scope = Scope(targets=("127.0.0.1",), ports=(endpoint.port,), lab_loopback=True)
            task = asyncio.create_task(
                run_campaign(
                    settings(interaction_timeout_seconds=2), scope, root=tmp_path, stop=stop
                )
            )
            await asyncio.wait_for(ready.wait(), 1)
            stop.set()
            manifest = await task
            await asyncio.wait_for(closed.wait(), 1)
        assert manifest["connection_attempted"] == 2 and manifest["incomplete"] == 1
        assert manifest["completed"] == 0 and manifest["status"] == "cancelled"

    asyncio.run(exercise())


def test_tls_handshake_deadline_preserves_tcp_open() -> None:
    async def exercise() -> None:
        calls = 0

        async def peer(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            nonlocal calls
            calls += 1
            await reader.read(8192)
            if calls == 2:
                await reader.read()

        async with fixture(peer) as endpoint:
            result = await admitted_collect(endpoint, interaction_timeout_seconds=0.06)
        assert result.outcome == Outcome.OPEN and result.service
        assert result.service.protocol == Protocol.UNKNOWN
        assert result.evidence.exchanges[1].status == "interaction_timeout"
        assert result.evidence.exchanges[1].tls is None

    asyncio.run(exercise())


def test_expired_self_signed_certificate_is_preserved_without_trust_claim(
    tmp_path: Path, tls_context: tuple[ssl.SSLContext, bytes, list[str | None]]
) -> None:
    expired = tmp_path / "expired.pem"
    # Use the portable CA start/end-date options, not version-dependent negative days.
    request = tmp_path / "request.pem"
    database, serial, config = tmp_path / "index", tmp_path / "serial", tmp_path / "ca.cnf"
    database.write_text("")
    serial.write_text("01\n")
    config.write_text(
        "[ca]\ndefault_ca = fixture\n[fixture]\n"
        f'database = "{database}"\nserial = "{serial}"\n'
        f'new_certs_dir = "{tmp_path}"\n'
        "default_md = sha256\npolicy = fixture_policy\n"
        "[fixture_policy]\ncommonName = supplied\n"
    )
    subprocess.run(
        [
            "openssl",
            "req",
            "-new",
            "-key",
            str(tmp_path / "key.pem"),
            "-subj",
            "/CN=untrusted.example.invalid",
            "-out",
            str(request),
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "openssl",
            "ca",
            "-selfsign",
            "-batch",
            "-notext",
            "-config",
            str(config),
            "-keyfile",
            str(tmp_path / "key.pem"),
            "-cert",
            str(tmp_path / "cert.pem"),
            "-startdate",
            "20000101000000Z",
            "-enddate",
            "20000102000000Z",
            "-in",
            str(request),
            "-out",
            str(expired),
        ],
        check=True,
        capture_output=True,
    )
    assert (
        subprocess.run(
            ["openssl", "x509", "-in", str(expired), "-checkend", "0", "-noout"],
            capture_output=True,
        ).returncode
        == 1
    )
    context = tls_context[0]
    context.load_cert_chain(expired, tmp_path / "key.pem")

    async def exercise() -> None:
        async def peer(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            writer.write(b"SSH-2.0-Synthetic\r\n")
            await writer.drain()
            await reader.read()

        async with fixture(peer, tls=context) as endpoint:
            result = await admitted_collect(endpoint)
        evidence = result.evidence.exchanges[1].tls
        assert evidence and evidence.verification == "not_performed"
        assert base64.b64decode(evidence.certificates[0].body_base64) == ssl.PEM_cert_to_DER_cert(
            expired.read_text()
        )
        assert result.service and result.service.protocol == Protocol.SSH and result.service.tls

    asyncio.run(exercise())


def test_receive_cap_is_shared_across_both_connections() -> None:
    async def exercise() -> None:
        calls = 0

        async def peer(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            nonlocal calls
            calls += 1
            await reader.read(8192)
            writer.write(b"unidentified greeting after GET" if calls == 1 else b"\x00" * 4096)
            await writer.drain()

        async with fixture(peer) as endpoint:
            result = await admitted_collect(endpoint, max_response_bytes=64)
        assert calls == len(result.evidence.exchanges) == 2
        assert result.evidence.received_bytes == 64
        first = result.evidence.exchanges[0].response
        assert first and result.evidence.retained_bytes == len(base64.b64decode(first.body_base64))
        assert result.outcome == Outcome.OPEN and result.service
        assert result.service.protocol == Protocol.UNKNOWN
        assert result.evidence.exchanges[1].status == "tls_error"

    asyncio.run(exercise())
