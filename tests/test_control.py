"""Distributed failure acceptance using PostgreSQL, authored evidence and loopback only."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from test_storage import scalar

from netatlas.config import Settings
from netatlas.control.cli import main
from netatlas.control.coordinator import Coordinator
from netatlas.control.files import (
    Boot,
    Credentials,
    Pending,
    Spool,
    provision,
    read_private,
)
from netatlas.control.http import create_control_app
from netatlas.control.models import (
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
    request_reader,
)
from netatlas.control.worker import Worker
from netatlas.derivations.engine import canonical, digest
from netatlas.derivations.offline import json_object
from netatlas.discovery.scope import Scope
from netatlas.domain import Outcome, ScannerNode, Target
from netatlas.observation import Observation
from netatlas.storage.database import transaction
from netatlas.storage.pipeline import Pipeline

pytest_plugins = ["test_storage"]


def config(**overrides: Any) -> Settings:
    return Settings.model_validate(
        {
            "measurement": {
                "enabled": True,
                "operator_name": "Authored fixture",
                "operator_contact": "fixture@example.org",
                "user_agent": "NetAtlas research fixture",
                "global_connections_per_second": 100,
                "per_prefix_connections_per_second": 20,
                **overrides,
            }
        }
    )


def queue(c: Coordinator, *ports: int, settings: Settings | None = None) -> UUID:
    return c.enqueue(
        settings or config(),
        Scope(targets=("127.0.0.1",), ports=ports or (12345,), lab_loopback=True),
        measure=True,
        synthetic=True,
    )


def boot(worker: UUID | None = None, generation: int = 1) -> Boot:
    return Boot(worker_id=worker or uuid4(), session_id=uuid4(), generation=generation)


def identity(b: Boot) -> dict[str, Any]:
    return {"schema_version": 1, "worker_id": b.worker_id, "session_id": b.session_id}


def register(c: Coordinator, b: Boot) -> None:
    c.exchange(
        Register.model_validate(identity(b) | {"action": "register", "generation": b.generation})
    )


def claim(c: Coordinator, b: Boot) -> Lease:
    reply = c.exchange(Claim.model_validate(identity(b) | {"action": "claim"}))
    assert reply.lease is not None
    return reply.lease


def authority(b: Boot, lease: Lease) -> dict[str, Any]:
    return identity(b) | {
        "job_id": lease.job_id,
        "attempt_id": lease.attempt_id,
        "fence": lease.fence,
    }


def permit(c: Coordinator, b: Boot, lease: Lease, number: int = 1) -> Reply:
    return c.exchange(
        Permit.model_validate(authority(b, lease) | {"action": "permit", "connection": number})
    )


def delivery(b: Boot, lease: Lease) -> Deliver:
    now = datetime.now(UTC)
    source = Observation(
        observation_id=lease.observation_id,
        endpoint=lease.endpoint,
        target=Target(
            address=lease.endpoint.address,
            source="loopback-lab",
            campaign_id=str(lease.campaign_id),
        ),
        scanner=ScannerNode(node_id=str(b.worker_id), software_version="fixture"),
        config_sha256=lease.config_sha256,
        started_at=now,
        finished_at=now,
        outcome=Outcome.CLOSED,
        error_code="connection_refused",
    )
    return Deliver.model_validate(
        authority(b, lease)
        | {"action": "deliver", "observation": source, "source_sha256": digest(canonical(source))}
    )


def protocol_delivery(b: Boot, lease: Lease) -> Deliver:
    from netatlas.collectors.runner import capture
    from netatlas.evidence import Exchange, ProtocolEvidence
    from netatlas.protocol_syntax import inspect

    raw = b"HTTP/1.1 200 OK\r\nContent-Length: 7\r\n\r\nfixture"
    evidence = ProtocolEvidence(
        exchanges=(
            Exchange(
                connection=1,
                probe="greeting-http",
                tcp_outcome=Outcome.OPEN,
                status="complete",
                response=capture(raw),
                http=inspect(raw).http,
            ),
        ),
        received_bytes=len(raw),
        retained_bytes=len(raw),
        sent_bytes=0,
        termination="finished",
    )
    original = delivery(b, lease)
    source = Observation.model_validate(
        original.observation.model_dump()
        | {"outcome": Outcome.OPEN, "error_code": None, "protocol_evidence": evidence}
    )
    return Deliver.model_validate(
        original.model_dump() | {"observation": source, "source_sha256": digest(canonical(source))}
    )


def expire_lease(p: Pipeline) -> None:
    with transaction(p.engine) as conn:
        conn.execute(
            text("UPDATE control_attempts SET lease_until=clock_timestamp()-interval '1 second'")
        )


def ready(p: Pipeline, *, settings: Settings | None = None) -> tuple[Coordinator, Boot, Lease]:
    c, b = Coordinator(p), boot()
    queue(c, settings=settings)
    register(c, b)
    return c, b, claim(c, b)


def test_private_credentials_spool_bounds_and_generation(tmp_path: Path) -> None:
    root = tmp_path / "credentials"
    provision(root)
    credentials = Credentials.model_validate(json_object(read_private(root / "coordinator.json")))
    assert credentials.workers[0].token != credentials.workers[1].token
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in root.iterdir())
    assert credentials.workers[0].token not in repr(credentials)
    with pytest.raises(ValueError):
        provision(root)
    spool = Spool(tmp_path / "worker")
    with spool.lock():
        first = spool.boot(credentials.workers[0].worker_id)
        with pytest.raises(BlockingIOError), Spool(spool.root).lock():
            pass
    with spool.lock():
        second = spool.boot(first.worker_id)
        assert second.generation == 2 and second.session_id != first.session_id
        with pytest.raises(ValueError):
            spool.boot(uuid4())
    (root / "worker-1.json").chmod(0o644)
    with pytest.raises(ValueError):
        read_private(root / "worker-1.json")


def test_dry_run_opens_no_storage(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("preview opened storage")

    monkeypatch.setattr("netatlas.control.cli.local_engine", forbidden)
    assert main(["enqueue", "--target", "192.0.2.1", "--port", "80"]) == 0
    assert "preview" in capsys.readouterr().out


@pytest.mark.parametrize(
    "change", [{"schema_version": 2}, {"extra": True}, {"connection": 3}, {"fence": 0}]
)
def test_envelope_bounds(change: dict[str, Any]) -> None:
    value = {
        "schema_version": 1,
        "action": "permit",
        "worker_id": uuid4(),
        "session_id": uuid4(),
        "job_id": uuid4(),
        "attempt_id": uuid4(),
        "fence": 1,
        "connection": 1,
    }
    with pytest.raises(ValueError):
        request_reader.validate_python(value | change)


def test_queue_requires_enabled_synthetic_loopback_and_bounds(pipeline: Pipeline) -> None:
    c = Coordinator(pipeline)
    scope = Scope(targets=("127.0.0.1",), ports=(12345,), lab_loopback=True)
    for settings, measure, synthetic in (
        (Settings(), True, True),
        (config(), False, True),
        (config(), True, False),
    ):
        with pytest.raises(ValueError):
            c.enqueue(settings, scope, measure=measure, synthetic=synthetic)
    with pytest.raises(ValueError):
        c.enqueue(
            config(), Scope(targets=("192.0.2.1",), ports=(80,)), measure=True, synthetic=True
        )
    with pytest.raises(ValueError):
        queue(c, 1, 2, settings=config(queue_size=1))
    queue(c)
    with pytest.raises(ControlError, match="campaign_active"):
        queue(c)


def test_registration_reordering_fences_old_sessions_and_caps_workers(pipeline: Pipeline) -> None:
    c, old, lease = ready(pipeline)
    register(c, old)  # lost register acknowledgement
    new = boot(old.worker_id, 2)
    register(c, new)
    with pytest.raises(ControlError, match="fenced"):
        register(c, old)
    with pytest.raises(ControlError, match="fenced"):
        permit(c, old, lease)
    second = boot()
    register(c, second)
    with pytest.raises(ControlError, match="worker_limit"):
        register(c, boot())
    replacement = claim(c, second)
    assert replacement.job_id == lease.job_id and replacement.fence == 2
    assert replacement.attempt_id != lease.attempt_id
    assert replacement.observation_id != lease.observation_id
    with pytest.raises(ControlError, match="fenced"):
        c.exchange(Resume.model_validate(authority(new, lease) | {"action": "resume"}))


def test_unstarted_reclaim_bounded_and_lost_claim_ack(pipeline: Pipeline) -> None:
    c, b, lease = ready(pipeline)
    assert claim(c, b) == lease or claim(c, b).attempt_id == lease.attempt_id
    for fence in (2, 3):
        expire_lease(pipeline)
        lease = claim(c, b)
        assert lease.fence == fence
    expire_lease(pipeline)
    assert c.status() == {"failed": 1}
    assert c.exchange(Claim.model_validate(identity(b) | {"action": "claim"})).status == "idle"


def test_issued_attempt_never_remeasured_and_late_delivery(pipeline: Pipeline) -> None:
    c, b, lease = ready(pipeline)
    assert permit(c, b, lease).status == "granted"
    result = delivery(b, lease)
    expire_lease(pipeline)
    assert c.status() == {"uncertain": 1}
    with pytest.raises(ControlError, match="stopped"):
        permit(c, b, lease)
    assert c.exchange(Claim.model_validate(identity(b) | {"action": "claim"})).status == "idle"
    assert c.exchange(result).status == "inserted"
    assert pipeline.load(result.observation.observation_id) == result.observation


def test_heartbeat_expiry_restart_and_delivery_only_resume(pipeline: Pipeline) -> None:
    c, old, lease = ready(pipeline)
    permit(c, old, lease)
    result = delivery(old, lease)
    c.exchange(Heartbeat.model_validate(authority(old, lease) | {"action": "heartbeat"}))
    new = boot(old.worker_id, 2)
    register(c, new)
    with pytest.raises(ControlError, match="fenced"):
        c.exchange(result)
    rebound = Deliver.model_validate(result.model_dump() | identity(new))
    with pytest.raises(ControlError, match="fenced"):
        c.exchange(rebound)
    c.exchange(Resume.model_validate(authority(new, lease) | {"action": "resume"}))
    with pytest.raises(ControlError, match="fenced"):
        permit(c, new, lease)
    assert c.exchange(rebound).status == "inserted"
    assert scalar(pipeline, "SELECT connections FROM control_attempts") == 1


@pytest.mark.parametrize(
    "stage", ["after_blobs", "before_commit", "control_before_commit", "control_after_commit"]
)
def test_atomic_delivery_lost_ack_and_coordinator_restart(pipeline: Pipeline, stage: str) -> None:
    c, b, lease = ready(pipeline, settings=config(protocol_evidence=True))
    permit(c, b, lease)
    message = protocol_delivery(b, lease)

    def fail(actual: str) -> None:
        if actual == stage:
            raise RuntimeError("injected fault")

    c.pipeline = Pipeline(pipeline.engine, pipeline.blobs, hook=fail)
    with pytest.raises(RuntimeError):
        c.exchange(message)
    committed = stage == "control_after_commit"
    assert scalar(pipeline, "SELECT count(*) FROM observations") == int(committed)
    assert scalar(
        pipeline, "SELECT count(*) FROM control_attempts WHERE source_sha256 IS NOT NULL"
    ) == int(committed)
    restarted = Coordinator(pipeline)
    assert restarted.exchange(message).status == ("replayed" if committed else "inserted")
    assert restarted.exchange(message).status == "replayed"
    assert scalar(pipeline, "SELECT count(*) FROM outbox") == 1
    assert scalar(pipeline, "SELECT connections FROM control_attempts") == 1


@pytest.mark.parametrize("field,value", [("observation_id", uuid4()), ("config_sha256", "f" * 64)])
def test_identity_conflict_never_overwrites(pipeline: Pipeline, field: str, value: Any) -> None:
    c, b, lease = ready(pipeline)
    permit(c, b, lease)
    original = delivery(b, lease)
    c.exchange(original)
    changed = Observation.model_validate(original.observation.model_dump() | {field: value})
    forged = Deliver.model_validate(
        original.model_dump()
        | {"observation": changed, "source_sha256": digest(canonical(changed))}
    )
    with pytest.raises(ControlError, match="identity_conflict"):
        c.exchange(forged)
    assert pipeline.load(original.observation.observation_id) == original.observation


def test_global_prefix_second_connection_and_restart_pacing(pipeline: Pipeline) -> None:
    c = Coordinator(pipeline)
    queue(
        c,
        12345,
        12346,
        settings=config(
            protocol_evidence=True,
            global_connections_per_second=2,
            per_prefix_connections_per_second=1,
        ),
    )
    one, two = boot(), boot()
    register(c, one)
    register(c, two)
    first, second = claim(c, one), claim(c, two)
    assert permit(c, one, first).status == "granted"
    with pytest.raises(ControlError, match="permit_consumed"):
        permit(c, one, first)
    other = permit(Coordinator(pipeline), two, second)
    tls = permit(c, one, first, 2)
    assert other.status == tls.status == "wait"
    assert 1 < other.delay_seconds <= 1.25
    with transaction(pipeline.engine) as conn:
        conn.execute(
            text("""UPDATE control_pacing SET next_at=clock_timestamp()-interval '2 seconds',
                     last_at=clock_timestamp()-interval '2 seconds'""")
        )
    assert permit(c, one, first, 2).status == "granted"
    with pytest.raises(ValueError):
        permit(c, one, first, 3)
    assert permit(c, two, second).status == "wait"
    assert scalar(pipeline, "SELECT sum(connections) FROM control_attempts") == 2


def test_concurrency_slot_survives_worker_loss_and_cancel(pipeline: Pipeline) -> None:
    c = Coordinator(pipeline)
    campaign = queue(c, 12345, 12346, settings=config(max_concurrency=1))
    one, two = boot(), boot()
    register(c, one)
    register(c, two)
    first = claim(c, one)
    permit(c, one, first)
    expire_lease(pipeline)
    assert c.exchange(Claim.model_validate(identity(two) | {"action": "claim"})).status == "wait"
    c.cancel(campaign)
    queue(c, 12347, settings=config(max_concurrency=1))
    assert c.exchange(Claim.model_validate(identity(two) | {"action": "claim"})).status == "wait"
    with transaction(pipeline.engine) as conn:
        conn.execute(
            text("UPDATE control_attempts SET hard_until=clock_timestamp()-interval '1 second'")
        )
    assert claim(c, two).endpoint.port == 12347


@pytest.mark.parametrize("action", ["cancel", "suppress", "deadline", "delivery_expiry"])
def test_stop_retention_and_suppression(pipeline: Pipeline, action: str) -> None:
    c, b, lease = ready(pipeline)
    permit(c, b, lease)
    result = delivery(b, lease)
    if action == "cancel":
        c.cancel(lease.campaign_id)
    elif action == "suppress":
        pipeline.maintain(suppress="127.0.0.1/32")
    else:
        table, column = (
            ("control_campaigns", "deadline")
            if action == "deadline"
            else ("control_attempts", "delivery_until")
        )
        with transaction(pipeline.engine) as conn:
            conn.execute(
                text(f"UPDATE {table} SET {column}=clock_timestamp()-interval '10 seconds'")
            )
    with pytest.raises(ControlError):
        c.exchange(result)
    with pytest.raises(ControlError):
        c.exchange(Heartbeat.model_validate(authority(b, lease) | {"action": "heartbeat"}))
    assert scalar(pipeline, "SELECT count(*) FROM observations") == 0


def test_http_authentication_and_bounded_errors(pipeline: Pipeline, tmp_path: Path) -> None:
    provision(tmp_path / "auth")
    creds = Credentials.model_validate(
        json_object(read_private(tmp_path / "auth/coordinator.json"))
    )
    c = Coordinator(pipeline)
    b = boot(creds.workers[0].worker_id)
    raw = Register.model_validate(identity(b) | {"action": "register", "generation": 1}).model_dump(
        mode="json"
    )
    headers = {
        "Authorization": "Bearer " + creds.workers[0].token,
        "X-NetAtlas-Worker": str(b.worker_id),
    }
    with TestClient(
        create_control_app(c, creds), base_url="http://127.0.0.1:8001", client=("127.0.0.1", 43210)
    ) as client:
        path = "/control/v1/exchange"
        assert client.post(path, json=raw).status_code == 401
        assert client.post(path, json=raw, headers=headers).status_code == 200
        for extra in (
            {"Origin": "http://127.0.0.1:5173"},
            {"Cookie": "fixture=1"},
            {"Host": "example.org"},
            {"Content-Encoding": "gzip"},
        ):
            assert client.post(path, json=raw, headers=headers | extra).status_code == 403
        wrong = raw | {"worker_id": str(creds.workers[1].worker_id)}
        assert client.post(path, json=wrong, headers=headers).status_code == 401
        assert (
            client.post(path, json=raw | {"extra": "private-input"}, headers=headers).status_code
            == 422
        )
        response = client.post(
            path, content=b"x" * 1048577, headers=headers | {"Content-Type": "application/json"}
        )
        assert response.status_code == 413
        assert creds.workers[0].token not in response.text and "private-input" not in response.text
        assert response.headers["cache-control"] == "no-store"
        assert client.post("/api/v1/search", json={}).status_code == 404
    with TestClient(
        create_control_app(c, creds), base_url="http://127.0.0.1:8001", client=("192.0.2.1", 43210)
    ) as client:
        assert client.post(path, json=raw, headers=headers).status_code == 403


class DirectTransport:
    def __init__(self, c: Coordinator):
        self.c = c
        self.delivery_failures = 0
        self.lost_ack = False
        self.heartbeat_failure = False

    async def send(self, message: Request) -> Reply:
        if isinstance(message, Deliver) and self.delivery_failures:
            self.delivery_failures -= 1
            raise ControlError(503, "unavailable")
        if isinstance(message, Heartbeat) and self.heartbeat_failure:
            raise ControlError(503, "unavailable")
        reply = await asyncio.to_thread(self.c.exchange, message)
        if isinstance(message, Deliver) and self.lost_ack:
            self.lost_ack = False
            raise ControlError(503, "lost_ack")
        return reply


def test_worker_saved_delivery_retry_restart_no_measurement(
    pipeline: Pipeline, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    c, b, lease = ready(pipeline)
    permit(c, b, lease)
    message = delivery(b, lease)
    spool = Spool(tmp_path / "spool")
    spool.save(Pending(lease=lease, delivery=message))
    transport = DirectTransport(c)
    transport.lost_ack = True
    new = boot(b.worker_id, 2)

    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("replayed delivery measured a target")

    monkeypatch.setattr("netatlas.control.worker.connect", forbidden)
    monkeypatch.setattr("netatlas.control.worker.collect", forbidden)
    asyncio.run(Worker(transport, spool, new).start())
    assert spool.pending() is None
    assert pipeline.load(lease.observation_id) == message.observation
    assert scalar(pipeline, "SELECT connections FROM control_attempts") == 1


def test_worker_storage_unavailable_keeps_one_slot_and_stops_claims(
    pipeline: Pipeline, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    c, b, lease = ready(pipeline)
    permit(c, b, lease)
    pending = Pending(lease=lease, delivery=delivery(b, lease))
    spool = Spool(tmp_path / "spool")
    spool.save(pending)
    transport = DirectTransport(c)
    transport.delivery_failures = 5
    worker = Worker(transport, spool, b)

    async def no_wait(delay: float) -> None:
        pass

    monkeypatch.setattr("netatlas.control.worker.asyncio.sleep", no_wait)
    with pytest.raises(ControlError):
        asyncio.run(worker.deliver(pending))
    assert spool.pending() == pending
    with pytest.raises(ValueError, match="drain"):
        asyncio.run(worker.step())
    assert scalar(pipeline, "SELECT count(*) FROM observations") == 0
    assert scalar(pipeline, "SELECT connections FROM control_attempts") == 1


def test_late_permit_response_burns_authority_without_dial(
    pipeline: Pipeline, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    c, b = Coordinator(pipeline), boot()
    queue(c)

    class Delayed(DirectTransport):
        async def send(self, message: Request) -> Reply:
            reply = await super().send(message)
            if isinstance(message, Permit):
                await asyncio.sleep(0.3)
            return reply

    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("expired permit opened socket")

    monkeypatch.setattr("netatlas.control.worker.connect", forbidden)
    spool = Spool(tmp_path / "spool")
    worker = Worker(Delayed(c), spool, b)

    async def scenario() -> None:
        await worker.start()
        with pytest.raises(ControlError, match="permit_expired"):
            await worker.step()
        restarted = Worker(DirectTransport(c), spool, boot(b.worker_id, 2))
        await restarted.start()
        assert not await restarted.step()

    asyncio.run(scenario())
    assert c.status() == {"uncertain": 1}
    assert scalar(pipeline, "SELECT connections FROM control_attempts") == 1


@pytest.mark.parametrize("stop", ["heartbeat", "suppression", "cancellation"])
def test_worker_stop_closes_inflight_socket(pipeline: Pipeline, tmp_path: Path, stop: str) -> None:
    from test_protocols import fixture

    async def scenario() -> None:
        contacted, closed = asyncio.Event(), asyncio.Event()

        async def peer(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            await reader.readuntil(b"\r\n\r\n")
            contacted.set()
            assert await reader.read() == b""
            closed.set()

        async with fixture(peer) as endpoint:
            c, b = Coordinator(pipeline), boot()
            queue(
                c,
                endpoint.port,
                settings=config(
                    protocol_evidence=True,
                    greeting_timeout_seconds=0.02,
                    interaction_timeout_seconds=6,
                    endpoint_timeout_seconds=8,
                ),
            )
            transport = DirectTransport(c)
            spool = Spool(tmp_path / "spool")
            worker = Worker(transport, spool, b)
            await worker.start()
            task = asyncio.create_task(worker.step())
            await asyncio.wait_for(contacted.wait(), 4)
            if stop == "heartbeat":
                transport.heartbeat_failure = True
            elif stop == "suppression":
                await asyncio.to_thread(pipeline.maintain, suppress="127.0.0.1/32")
            else:
                task.cancel()
            with pytest.raises((ControlError, asyncio.CancelledError)):
                await asyncio.wait_for(task, 4)
            await asyncio.wait_for(closed.wait(), 2)
            pending = spool.pending()
            assert pending is not None and pending.delivery is None
        assert scalar(pipeline, "SELECT count(*) FROM observations") == 0
        assert scalar(pipeline, "SELECT connections FROM control_attempts") == 1

    asyncio.run(scenario())


def test_queue_capacity_clock_regression_and_independent_prefixes(
    pipeline: Pipeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    c = Coordinator(pipeline)
    c.enqueue(
        config(global_connections_per_second=2, per_prefix_connections_per_second=1),
        Scope(targets=("127.0.0.1", "::1"), ports=(12345,), lab_loopback=True),
        measure=True,
        synthetic=True,
    )
    one, two = boot(), boot()
    register(c, one)
    register(c, two)
    first, second = claim(c, one), claim(c, two)
    assert first.endpoint.address != second.endpoint.address
    assert permit(c, one, first).status == "granted"
    other_prefix = permit(c, two, second)
    assert other_prefix.status == "wait" and 0.5 < other_prefix.delay_seconds <= 0.75
    with transaction(pipeline.engine) as conn:
        conn.execute(text("UPDATE control_pacing SET last_at=clock_timestamp()+interval '1 day'"))
    with pytest.raises(ControlError, match="clock_regressed"):
        permit(c, two, second)
    c.cancel(first.campaign_id)
    monkeypatch.setattr("netatlas.control.coordinator.MAX_JOBS", 2)
    with pytest.raises(ControlError, match="queue_full"):
        queue(c)


def test_populated_upgrade_preserves_source_and_restore_cancels_jobs(
    empty_engine: Any, tmp_path: Path
) -> None:
    import subprocess

    from test_storage import observation

    from netatlas.storage.backup import backup, compose_command, restore
    from netatlas.storage.blobs import BlobStore
    from netatlas.storage.database import migrate

    migrate(empty_engine, "0004")
    p = Pipeline(empty_engine, BlobStore(tmp_path / "blobs"))
    source = observation()
    p.ingest(canonical(source), synthetic=True)
    migrate(empty_engine)
    assert p.load(source.observation_id) == source
    c, b, lease = ready(p)
    permit(c, b, lease)
    archive = tmp_path / "backups" / "phase10"
    backup(empty_engine, p.blobs, archive)
    name = "netatlas_restore_" + uuid4().hex
    subprocess.run(
        [*compose_command(), "createdb", "-U", "postgres", name], check=True, capture_output=True
    )
    from sqlalchemy import create_engine

    engine = create_engine(empty_engine.url.set(database=name), hide_parameters=True)
    try:
        blobs = BlobStore(tmp_path / "restored")
        assert restore(engine, blobs, archive)["observations"] == 1
        restored = Pipeline(engine, blobs)
        assert Coordinator(restored).status() == {"cancelled": 1}
        assert restored.load(source.observation_id) == source
        with pytest.raises(ControlError):
            permit(Coordinator(restored), b, lease)
    finally:
        engine.dispose()
        subprocess.run(
            [*compose_command(), "dropdb", "-U", "postgres", "--force", name],
            check=True,
            capture_output=True,
        )


@pytest.mark.parametrize("scheduled", [False, True])
def test_two_worker_processes_share_budget_and_collect_tls(
    pipeline: Pipeline, tmp_path: Path, scheduled: bool
) -> None:
    import socket
    import ssl
    import subprocess
    import sys
    import threading
    import time

    import uvicorn
    from test_protocols import fixture

    # An ephemeral cert/key is generated locally, never committed or logged.
    key, cert = tmp_path / "fixture.key", tmp_path / "fixture.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(key),
            "-out",
            str(cert),
            "-days",
            "1",
            "-subj",
            "/CN=fixture.invalid",
        ],
        check=True,
        capture_output=True,
    )
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)
    c = Coordinator(pipeline)
    auth = tmp_path / "auth"
    provision(auth)
    credentials = Credentials.model_validate(json_object(read_private(auth / "coordinator.json")))
    admissions: list[float] = []
    original = c.exchange
    registered: set[UUID] = set()
    both_registered = threading.Event()
    dropped: set[UUID] = set()

    def audited(request: Request) -> Reply:
        if isinstance(request, Claim):
            assert both_registered.wait(5)
        reply = original(request)
        if isinstance(request, Register):
            registered.add(request.worker_id)
            if len(registered) == 2:
                both_registered.set()
        if isinstance(request, Deliver) and request.worker_id not in dropped:
            dropped.add(request.worker_id)
            raise ControlError(503, "lost_ack")
        if isinstance(request, Permit) and reply.status == "granted":
            admissions.append(time.monotonic())
        return reply

    c.exchange = audited  # type: ignore[method-assign]
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        server = uvicorn.Server(
            uvicorn.Config(
                create_control_app(c, credentials, port),
                host="127.0.0.1",
                port=port,
                access_log=False,
                proxy_headers=False,
                log_level="critical",
            )
        )
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        for _ in range(500):
            if server.started:
                break
            time.sleep(0.01)
        assert server.started

        async def scenario() -> None:
            async def http_peer(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
                await reader.readuntil(b"\r\n\r\n")
                writer.write(
                    b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n"
                    b"Content-Length: 7\r\nServer: NetAtlasFixture\r\n\r\nfixture"
                )
                await writer.drain()

            async with (
                fixture(http_peer, tls=context) as tls_endpoint,
                fixture(http_peer) as http_endpoint,
            ):
                settings = config(
                    protocol_evidence=True,
                    greeting_timeout_seconds=0.05,
                    interaction_timeout_seconds=2,
                    endpoint_timeout_seconds=8,
                    global_connections_per_second=10,
                    per_prefix_connections_per_second=4,
                )
                if scheduled:
                    from test_scheduler import change, lab_request

                    from netatlas.scheduler.service import enqueue, report

                    request = lab_request()
                    request = change(
                        request,
                        settings=settings,
                        universe=request.universe.model_dump()
                        | {
                            "regions": [request.universe.regions[0]],
                            "seeds": [],
                            "ports": [tls_endpoint.port, http_endpoint.port],
                        },
                    )
                    campaign = enqueue(c, request, measure=True, synthetic=True)
                else:
                    campaign = queue(c, tls_endpoint.port, http_endpoint.port, settings=settings)
                processes = []
                try:
                    for number in (1, 2):
                        process = await asyncio.create_subprocess_exec(
                            sys.executable,
                            "-m",
                            "netatlas.control.cli",
                            "worker",
                            "--credential",
                            str(auth / f"worker-{number}.json"),
                            "--spool",
                            str(tmp_path / f"worker-{number}"),
                            "--port",
                            str(port),
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        processes.append(process)
                    results = await asyncio.wait_for(
                        asyncio.gather(*(p.communicate() for p in processes)), 30
                    )
                    assert [p.returncode for p in processes] == [0, 0], results
                finally:
                    for process in processes:
                        if process.returncode is None:
                            process.kill()
                            await process.wait()
            assert c.status() == {"delivered": 2}
            if scheduled:
                counts = report(c, campaign)["execution"]
                assert isinstance(counts, dict)
                assert counts["scheduled"] == counts["measured"] == counts["retained"] == 2
                assert counts["permits_issued"] == 3
            with pipeline.engine.connect() as conn:
                owners: Any = (
                    conn.execute(text("SELECT DISTINCT worker_id FROM control_attempts"))
                    .scalars()
                    .all()
                )
                ids: Any = (
                    conn.execute(text("SELECT observation_id FROM control_attempts"))
                    .scalars()
                    .all()
                )
            assert len(owners) == 2
            sources = [pipeline.load(value) for value in ids]
            tls_source = next(
                source for source in sources if source.endpoint.port == tls_endpoint.port
            )
            assert isinstance(tls_source, Observation) and tls_source.protocol_evidence
            assert len(tls_source.protocol_evidence.exchanges) == 2
            assert tls_source.protocol_evidence.exchanges[1].tls
            assert tls_source.protocol_evidence.exchanges[1].tls.verification == "not_performed"
            assert len(admissions) == 3
            assert len(dropped) == 2
            assert scalar(pipeline, "SELECT count(*) FROM outbox") == 2
            # Full 250ms permit windows plus 250ms prefix spacing, across both processes.
            assert all(b - a >= 0.48 for a, b in zip(admissions, admissions[1:], strict=False))
            assert all(not (tmp_path / f"worker-{n}" / "pending.json").exists() for n in (1, 2))

        try:
            asyncio.run(scenario())
        finally:
            server.should_exit = True
            thread.join(timeout=5)
            assert not thread.is_alive()


def test_killed_worker_process_restarts_without_remeasuring(
    pipeline: Pipeline, tmp_path: Path
) -> None:
    import socket
    import sys
    import threading
    import time

    import uvicorn
    from test_protocols import fixture

    c = Coordinator(pipeline)
    auth = tmp_path / "auth"
    provision(auth)
    credentials = Credentials.model_validate(json_object(read_private(auth / "coordinator.json")))
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        server = uvicorn.Server(
            uvicorn.Config(
                create_control_app(c, credentials, port),
                access_log=False,
                proxy_headers=False,
                log_level="critical",
            )
        )
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        for _ in range(500):
            if server.started:
                break
            time.sleep(0.01)
        assert server.started

        async def scenario() -> None:
            contacted = asyncio.Event()
            count = 0

            async def slow(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
                nonlocal count
                count += 1
                await reader.readuntil(b"\r\n\r\n")
                contacted.set()
                await reader.read()

            async def launch() -> asyncio.subprocess.Process:
                return await asyncio.create_subprocess_exec(
                    sys.executable,
                    "-m",
                    "netatlas.control.cli",
                    "worker",
                    "--credential",
                    str(auth / "worker-1.json"),
                    "--spool",
                    str(tmp_path / "worker"),
                    "--port",
                    str(port),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

            async with fixture(slow) as endpoint:
                queue(
                    c,
                    endpoint.port,
                    settings=config(
                        protocol_evidence=True,
                        greeting_timeout_seconds=0.02,
                        interaction_timeout_seconds=6,
                        endpoint_timeout_seconds=8,
                    ),
                )
                process = await launch()
                try:
                    await asyncio.wait_for(contacted.wait(), 8)
                    process.kill()
                    await process.wait()
                    restarted = await launch()
                    try:
                        output = await asyncio.wait_for(restarted.communicate(), 10)
                        assert restarted.returncode == 0, output
                    finally:
                        if restarted.returncode is None:
                            restarted.kill()
                            await restarted.wait()
                    assert count == 1
                finally:
                    if process.returncode is None:
                        process.kill()
                        await process.wait()
            assert c.status() == {"uncertain": 1}
            assert scalar(pipeline, "SELECT count(*) FROM observations") == 0
            assert scalar(pipeline, "SELECT connections FROM control_attempts") == 1

        try:
            asyncio.run(scenario())
        finally:
            server.should_exit = True
            thread.join(timeout=5)
            assert not thread.is_alive()


def test_reordered_deliveries_preserve_current_source_and_exact_digest(pipeline: Pipeline) -> None:
    c, first, old = ready(pipeline)
    permit(c, first, old)
    earlier = delivery(first, old)
    expire_lease(pipeline)
    assert c.status() == {"uncertain": 1}
    # A NEW explicit campaign is a new measurement, not recovery of the uncertain job.
    queue(c)
    second = boot()
    register(c, second)
    newer = claim(c, second)
    with transaction(pipeline.engine) as conn:
        conn.execute(
            text("""UPDATE control_pacing SET next_at=clock_timestamp()-interval '2 seconds',
            last_at=clock_timestamp()-interval '2 seconds'""")
        )
    permit(c, second, newer)
    later = delivery(second, newer)
    assert c.exchange(later).status == "inserted"
    assert c.exchange(earlier).status == "inserted"
    assert c.exchange(later).status == c.exchange(earlier).status == "replayed"
    assert (
        scalar(pipeline, "SELECT last_attempt FROM current_services")
        == later.observation.observation_id
    )
    assert scalar(pipeline, "SELECT count(*) FROM outbox") == 2
    changed = Deliver.model_validate(earlier.model_dump() | {"source_sha256": "0" * 64})
    with pytest.raises(ControlError, match="identity_conflict"):
        c.exchange(changed)


def test_replay_does_not_ack_missing_blobs_or_revive_suppression(pipeline: Pipeline) -> None:
    c, b, lease = ready(pipeline, settings=config(protocol_evidence=True))
    permit(c, b, lease)
    message = protocol_delivery(b, lease)
    c.exchange(message)
    sha = scalar(pipeline, "SELECT sha256 FROM blobs")
    data = pipeline.blobs.read(sha)
    (pipeline.blobs.root / sha).unlink()
    with pytest.raises(OSError):
        c.exchange(message)
    assert pipeline.blobs.put(data) == sha
    assert c.exchange(message).status == "replayed"
    pipeline.maintain(suppress="127.0.0.1/32")
    with pytest.raises(ControlError, match="stopped"):
        c.exchange(message)
    assert scalar(pipeline, "SELECT count(*) FROM observations") == 0
    assert not list(pipeline.blobs.root.iterdir())
