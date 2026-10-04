"""No public connections: policy arithmetic, fake clocks and loopback fixtures only."""

import asyncio
import errno
import hashlib
import json
import logging
import signal
import socket
import subprocess
import sys
from collections.abc import Iterator
from ipaddress import ip_address, ip_network
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from netatlas import cli
from netatlas.config import MeasurementSettings, Settings
from netatlas.discovery.budget import Budget
from netatlas.discovery.engine import run_campaign
from netatlas.discovery.policy import SPECIAL_NETWORKS, denial
from netatlas.discovery.scope import Scope
from netatlas.discovery.spool import Spool
from netatlas.discovery.tcp import connect
from netatlas.domain import Endpoint, Outcome
from netatlas.observation import Observation


def enabled(**overrides: object) -> Settings:
    return Settings.model_validate(
        {
            "measurement": {
                "enabled": True,
                "operator_name": "Fixture Researcher",
                "operator_contact": "research@example.org",
                "user_agent": "NetAtlas/0.1 (research; fixture)",
                "global_connections_per_second": 100,
                "per_prefix_connections_per_second": 20,
                "max_concurrency": 2,
                "queue_size": 1,
                **overrides,
            }
        }
    )


def lab(*ports: int) -> Scope:
    return Scope(targets=("127.0.0.1",), ports=ports, lab_loopback=True)


def read_campaign(root: Path) -> tuple[dict[str, object], list[Observation]]:
    directory = next(path for path in root.iterdir() if path.is_dir())
    manifest = json.loads((directory / "manifest.json").read_text())
    payload = (directory / "observations.jsonl").read_bytes()
    assert hashlib.sha256(payload).hexdigest() == manifest["observations_sha256"]
    observations = [Observation.model_validate_json(line) for line in payload.splitlines()]
    assert len(observations) == manifest["completed"]
    assert manifest["attempted"] == manifest["completed"] + manifest["incomplete"]
    return manifest, observations


def test_policy_registry_boundaries_and_denial_precedence() -> None:
    settings = MeasurementSettings()
    for network in SPECIAL_NETWORKS:
        for address in (network.network_address, network.broadcast_address):
            assert denial(address, settings) is not None
    for literal in (
        "224.0.0.0",
        "239.255.255.255",
        "ff00::",
        "ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff",
        "::ffff:127.0.0.1",
        "::ffff:192.0.2.1",
        "fe80::1%lo0",
        "192.0.0.9",
        "2001:1::3",
    ):
        assert denial(ip_address(literal), settings) is not None
    # Numeric boundary fixtures only; these are NEVER passed to a connector.
    for cidr in ("100.64.0.0/10", "3fff::/20"):
        last = ip_network(cidr).broadcast_address
        assert denial(last, settings) is not None
        assert denial(last + 1, settings) is None
    allow_all = MeasurementSettings.model_validate({"allow_cidrs": ["0.0.0.0/0", "::/0"]})
    assert denial(ip_address("192.0.2.1"), allow_all) == "special_use"
    assert denial(ip_address("127.0.0.1"), allow_all) == "special_use"
    assert denial(ip_address("127.0.0.1"), allow_all, lab=True) is None
    assert denial(ip_address("::1"), allow_all, lab=True) is None
    assert denial(ip_address("127.0.0.2"), allow_all, lab=True) == "outside_loopback_lab"
    for field, reason in (("exclusion_cidrs", "excluded"), ("opt_out_cidrs", "opt_out")):
        config = MeasurementSettings.model_validate(
            {field: ["127.0.0.1/32"], "allow_cidrs": ["127.0.0.1/32"]}
        )
        assert denial(ip_address("127.0.0.1"), config, lab=True) == reason
    restricted = MeasurementSettings.model_validate({"allow_cidrs": ["::1/128"]})
    assert denial(ip_address("127.0.0.1"), restricted, lab=True) == "outside_allowlist"


def test_scope_streaming_dedup_bounds_and_seed() -> None:
    config = MeasurementSettings()
    scope = Scope(targets=("192.0.2.0/30", "192.0.2.1", "2001:db8::/126"), ports=(80, 80, 443))
    addresses = scope.addresses(config)
    assert isinstance(addresses, Iterator)
    expanded = list(addresses)
    assert len(expanded) == len(set(expanded)) == 8
    assert {"192.0.2.0", "192.0.2.3", "2001:db8::", "2001:db8::3"} <= set(map(str, expanded))
    assert expanded == list(scope.addresses(config))
    assert expanded != list(Scope(**(scope.model_dump() | {"seed": 7})).addresses(config))
    assert scope.preview(config)["eligible_endpoints"] == 0
    assert list(scope.endpoints(config)) == []
    for target in ("0.0.0.0/0", "::/0", "2001:db8::/64", "192.0.0.0/19"):
        with pytest.raises(ValueError, match="budget"):
            next(Scope(targets=(target,), ports=(80,)).addresses(config))
    with pytest.raises(ValueError, match="budget"):
        Scope(targets=("192.0.0.0/20",), ports=(1, 2, 3, 4, 5)).preview(config)
    for patch in (
        {"targets": ("localhost",)},
        {"targets": ("192.0.2.1/24",)},
        {"targets": ("::1%lo0",)},
        {"ports": (0,)},
        {"ports": (65536,)},
        {"ports": (True,)},
        {"ports": ("80",)},
        {"ports": tuple(range(1, 66))},
        {"lab_loopback": True, "targets": ("127.0.0.0/30",)},
        {"lab_loopback": True, "targets": ("192.0.2.1",)},
    ):
        with pytest.raises(ValidationError):
            Scope.model_validate({"targets": ("192.0.2.1",), "ports": (80,), **patch})
    assert len(list(lab(80, 80, 443).endpoints(config))) == 2


def test_enabled_identity_and_limits() -> None:
    assert enabled().measurement.enabled
    assert enabled(operator_contact="https://example.org/research").measurement.enabled
    for patch in (
        {"operator_name": "  "},
        {"operator_contact": ""},
        {"operator_contact": "not-a-contact"},
        {"operator_contact": "https://user:secret@example.org"},
        {"operator_contact": "https://example.org/?token=secret"},
        {"user_agent": "NetAtlas/0.1 (research; measurement disabled)"},
        {"user_agent": "Agent\nInjected"},
        {"node_id": "bad\nnode"},
        {"enabled": "true"},
        {"max_addresses": 4097},
        {"max_endpoints": 16385},
        {"queue_size": 257},
        {"campaign_timeout_seconds": float("nan")},
    ):
        with pytest.raises(ValidationError):
            enabled(**patch)


@pytest.mark.parametrize("address", ["127.0.0.1", "::1"])
def test_loopback_open_refused_and_peer_eof(address: str) -> None:
    async def exercise() -> None:
        closed = asyncio.Event()
        received: list[bytes] = []

        async def peer(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            try:
                received.append(await reader.read(1))
            finally:
                writer.close()
                await writer.wait_closed()
                closed.set()

        try:
            server = await asyncio.start_server(peer, address, 0)
        except OSError as exc:
            if address == "::1" and exc.errno in {errno.EAFNOSUPPORT, errno.EADDRNOTAVAIL}:
                pytest.skip("host has no IPv6 loopback")
            raise
        async with server:
            port = server.sockets[0].getsockname()[1]
            assert await connect(Endpoint(address=ip_address(address), port=port), 1) == (
                Outcome.OPEN,
                None,
            )
            await asyncio.wait_for(closed.wait(), 1)
            assert received == [b""]  # Connect-only discovery sends no application bytes.
        family = socket.AF_INET if address == "127.0.0.1" else socket.AF_INET6
        with socket.socket(family, socket.SOCK_STREAM) as reserved:
            reserved.bind((address, 0))
            # Darwin can silently hold connects to a bound, non-listening socket.
            # Release this fixture port before testing the kernel refusal.
            endpoint = Endpoint(address=ip_address(address), port=reserved.getsockname()[1])
        assert await connect(endpoint, 1) == (Outcome.CLOSED, "connection_refused")

    asyncio.run(exercise())


def test_timeout_errors_and_cancel_close_owned_sockets(monkeypatch: pytest.MonkeyPatch) -> None:
    async def exercise() -> None:
        loop = asyncio.get_running_loop()
        sockets: list[socket.socket] = []
        entered = asyncio.Event()
        error: int | None = None

        async def fake_connect(sock: socket.socket, destination: tuple[str, int]) -> None:
            sockets.append(sock)
            entered.set()
            if error is not None:
                raise OSError(error, "sensitive destination and untrusted error text")
            await asyncio.Future[None]()

        monkeypatch.setattr(loop, "sock_connect", fake_connect)
        endpoint = Endpoint(address=ip_address("192.0.2.1"), port=80)
        assert await connect(endpoint, 0.001) == (Outcome.TIMEOUT, "connect_timeout")
        for code, expected in (
            (errno.ECONNREFUSED, (Outcome.CLOSED, "connection_refused")),
            (errno.ETIMEDOUT, (Outcome.TIMEOUT, "connect_timeout")),
            (errno.EHOSTUNREACH, (Outcome.ERROR, "network_unreachable")),
            (errno.EACCES, (Outcome.ERROR, "local_permission_denied")),
            (errno.EMFILE, (Outcome.ERROR, "socket_error")),
        ):
            error = code
            assert await connect(endpoint, 1) == expected
        error = None
        entered.clear()
        pending = asyncio.create_task(connect(endpoint, 1))
        await entered.wait()
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending
        assert all(sock.fileno() == -1 for sock in sockets)

    asyncio.run(exercise())


def test_rate_budget_shared_prefixes_no_bursts_and_cancel() -> None:
    async def exercise() -> None:
        now = 0.0
        times: list[tuple[str, float]] = []

        async def sleep(delay: float) -> None:
            nonlocal now
            now += delay + 0.01  # Delayed wakeups must not generate catch-up bursts.
            await asyncio.sleep(0)

        budget = Budget(10, 2, clock=lambda: now, sleep=sleep)

        async def acquire(address: str) -> None:
            await budget.acquire(ip_address(address))
            times.append((address, now))

        addresses = [
            "192.0.2.1",
            "198.51.100.1",
            "192.0.2.254",
            "2001:db8::1",
            "2001:db8:0:1::1",
            "2001:db8:1::1",
        ]
        await asyncio.gather(*(acquire(address) for address in addresses))
        assert all(b[1] - a[1] >= 0.1 - 1e-9 for a, b in zip(times, times[1:], strict=False))
        assert times[2][1] - times[0][1] >= 0.5
        assert times[4][1] - times[3][1] >= 0.5
        waiting = asyncio.Event()

        async def block(delay: float) -> None:
            waiting.set()
            await asyncio.Future[None]()

        cancellable = Budget(1, 1, clock=lambda: 0.0, sleep=block)
        await cancellable.acquire(ip_address("192.0.2.1"))
        task = asyncio.create_task(cancellable.acquire(ip_address("192.0.2.2")))
        await waiting.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert cancellable.next_global == 1
        assert not cancellable.lock.locked()

    asyncio.run(exercise())


def test_campaign_concurrency_jsonl_manifest_and_redacted_logs(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def exercise() -> None:
        active = peak = 0
        starts: list[float] = []

        async def fake(endpoint: Endpoint, timeout: float) -> tuple[Outcome, str | None]:
            nonlocal active, peak
            active += 1
            peak = max(active, peak)
            starts.append(asyncio.get_running_loop().time())
            try:
                await asyncio.sleep(0.12)
                return Outcome.CLOSED, "connection_refused"
            finally:
                active -= 1

        settings = enabled()
        scope = lab(10001, 10002, 10003, 10004, 10005, 10006)
        manifest = await run_campaign(settings, scope, root=tmp_path, connector=fake)
        assert manifest["status"] == "completed"
        assert active == 0 and peak == 2
        assert all(b - a >= 0.049 for a, b in zip(starts, starts[1:], strict=False))
        saved, observations = read_campaign(tmp_path)
        assert saved == manifest
        assert saved["config_sha256"] == settings.sha256
        assert saved["effective_config"] == settings.model_dump(mode="json")
        assert saved["seed"] == scope.seed
        assert saved["config_version"] == 3 and saved["manifest_version"] == 2
        assert saved["policy_version"] and saved["policy_sha256"] and saved["registry_version"]
        assert len(observations) == len({item.observation_id for item in observations}) == 6
        assert {item.endpoint.port for item in observations} == set(scope.ports)
        for item in observations:
            assert UUID(item.target.campaign_id) == UUID(str(saved["campaign_id"]))
            assert item.target.source == "loopback-lab"
            assert item.config_sha256 == settings.sha256
            assert item.error_code == "connection_refused"
            assert item.service is None and item.response is None

    caplog.set_level(logging.INFO, logger="netatlas.discovery")
    asyncio.run(exercise())
    assert "127.0.0.1" not in caplog.text and "research@example.org" not in caplog.text
    events = [json.loads(record.message) for record in caplog.records]
    assert events[-1]["event"] == "campaign_finished"
    assert len(events) == 7


@pytest.mark.parametrize("method", ["event", "task", "deadline"])
def test_cancel_flushes_completed_and_stops_queued_work(
    tmp_path: Path,
    method: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generated = 0
    original = Scope.endpoints

    def counted(scope: Scope, config: MeasurementSettings) -> Iterator[Endpoint]:
        nonlocal generated
        for endpoint in original(scope, config):
            generated += 1
            yield endpoint

    monkeypatch.setattr(Scope, "endpoints", counted)

    async def exercise() -> None:
        started = 0
        active = 0
        blocked = asyncio.Event()
        stop = asyncio.Event()

        async def fake(endpoint: Endpoint, timeout: float) -> tuple[Outcome, str | None]:
            nonlocal started, active
            started += 1
            active += 1
            try:
                if started == 1:
                    return Outcome.OPEN, None
                blocked.set()
                await asyncio.Future[None]()
                raise AssertionError("unreachable")
            finally:
                active -= 1

        task = asyncio.create_task(
            run_campaign(
                enabled(max_concurrency=1, campaign_timeout_seconds=0.2),
                lab(1, 2, 3, 4, 5, 6),
                root=tmp_path,
                stop=stop,
                connector=fake,
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
            await asyncio.wait_for(task, 1)
        assert active == 0 and started == 2
        # One completed, one active, one queued and at most one producer lookahead.
        assert generated <= 4
        manifest, observations = read_campaign(tmp_path)
        assert manifest["status"] == ("deadline_exceeded" if method == "deadline" else "cancelled")
        assert manifest["attempted"] == 2 and manifest["incomplete"] == 1
        assert len(observations) == 1 and observations[0].outcome == Outcome.OPEN
        assert not [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]

    asyncio.run(exercise())


def test_fail_closed_no_work_and_exclusive_spool(tmp_path: Path) -> None:
    async def exercise() -> None:
        async def forbidden(endpoint: Endpoint, timeout: float) -> tuple[Outcome, str | None]:
            raise AssertionError("denied/stopped work must never dial")

        with pytest.raises(ValueError, match="disabled"):
            await run_campaign(Settings(), lab(80), root=tmp_path, connector=forbidden)
        assert list(tmp_path.iterdir()) == []
        stop = asyncio.Event()
        stop.set()
        manifest = await run_campaign(
            enabled(), lab(80), root=tmp_path, stop=stop, connector=forbidden
        )
        assert manifest["attempted"] == 0 and manifest["status"] == "cancelled"
        denied_root = tmp_path / "denied"
        manifest = await run_campaign(
            enabled(),
            Scope(targets=("192.0.2.1", "2001:db8::1"), ports=(80,)),
            root=denied_root,
            connector=forbidden,
        )
        assert manifest["completed"] == 0 and manifest["status"] == "completed"
        with (
            Spool(tmp_path / "lock", uuid4(), enabled(), lab(80)),
            pytest.raises(BlockingIOError),
            Spool(tmp_path / "lock", uuid4(), enabled(), lab(80)),
        ):
            pytest.fail("concurrent campaign acquired spool lock")

    asyncio.run(exercise())


def test_worker_failure_closes_siblings_and_finalizes_manifest(tmp_path: Path) -> None:
    async def exercise() -> None:
        active = 0

        async def broken(endpoint: Endpoint, timeout: float) -> tuple[Outcome, str | None]:
            nonlocal active
            active += 1
            try:
                await asyncio.sleep(0.1)
                raise RuntimeError("do not log this raw exception")
            finally:
                active -= 1

        with pytest.raises(ExceptionGroup):
            await run_campaign(enabled(), lab(1, 2, 3, 4), root=tmp_path, connector=broken)
        assert active == 0
        manifest, observations = read_campaign(tmp_path)
        assert manifest["status"] == "failed" and observations == []
        assert manifest["incomplete"] == manifest["attempted"]

    asyncio.run(exercise())


def test_cli_dry_run_default_even_with_enabled_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "load_settings", lambda path: enabled())
    monkeypatch.setattr(
        sys, "argv", ["netatlas", "discover", "--target", "192.0.2.0/30", "--port", "80"]
    )
    cli.main()
    preview = json.loads(capsys.readouterr().out)
    assert preview["dry_run"] is True and preview["eligible_endpoints"] == 0
    assert list(tmp_path.iterdir()) == []
    monkeypatch.setattr(cli, "load_settings", lambda path: Settings())
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "netatlas",
            "discover",
            "--target",
            "127.0.0.1",
            "--port",
            "80",
            "--lab-loopback",
            "--measure",
        ],
    )
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    assert not (tmp_path / "data").exists()


def test_cli_sigterm_preserves_results(tmp_path: Path) -> None:
    config = tmp_path / "lab.toml"
    config.write_text("""[measurement]
enabled = true
operator_name = "Fixture Researcher"
operator_contact = "research@example.org"
user_agent = "NetAtlas/0.1 (research; fixture)"
per_prefix_connections_per_second = 0.1
""")
    with socket.socket() as reserved, socket.socket() as second:
        reserved.bind(("127.0.0.1", 0))
        second.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]
        process = subprocess.Popen(
            [
                "netatlas",
                "--config",
                str(config),
                "discover",
                "--target",
                "127.0.0.1",
                "--port",
                str(port),
                "--port",
                str(second.getsockname()[1]),
                "--lab-loopback",
                "--measure",
            ],
            cwd=tmp_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            assert process.stderr is not None
            # A bounded select avoids hanging the suite if CLI startup regresses.
            import select

            assert select.select([process.stderr], [], [], 5)[0]
            event = json.loads(process.stderr.readline())
            assert event["event"] == "connect_completed"
            process.send_signal(signal.SIGTERM)
            _, errors = process.communicate(timeout=5)
            assert process.returncode == 130
            assert "127.0.0.1" not in errors and "research@example.org" not in errors
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
        manifest, observations = read_campaign(tmp_path / "data")
        assert manifest["status"] == "cancelled" and manifest["attempted"] == 1
        assert len(observations) == 1


def test_repeated_cancellation_does_not_interrupt_cleanup(tmp_path: Path) -> None:
    async def exercise() -> None:
        entered = asyncio.Event()
        cleaning = asyncio.Event()
        closed = asyncio.Event()

        async def fake(endpoint: Endpoint, timeout: float) -> tuple[Outcome, str | None]:
            entered.set()
            try:
                await asyncio.Future[None]()
            finally:
                cleaning.set()
                await asyncio.sleep(0.01)
                closed.set()
            raise AssertionError("unreachable")

        task = asyncio.create_task(run_campaign(enabled(), lab(80), root=tmp_path, connector=fake))
        await entered.wait()
        task.cancel()
        await cleaning.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert closed.is_set()
        manifest, observations = read_campaign(tmp_path)
        assert manifest["status"] == "cancelled" and observations == []

    asyncio.run(exercise())
