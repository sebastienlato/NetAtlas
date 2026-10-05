"""Operational load, failure, access and restore drills; authored local fixtures only."""

import asyncio
import json
import logging
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from test_control import boot, claim, config, delivery, permit, queue, register
from test_read_api import client_for
from test_storage import observation

from netatlas.api import create_app
from netatlas.control.coordinator import Coordinator
from netatlas.control.files import Credentials, provision, read_private
from netatlas.control.http import create_control_app
from netatlas.derivations.engine import canonical
from netatlas.operations.access import provision_access
from netatlas.operations.status import readiness, snapshot
from netatlas.operations.telemetry import ROUTES, Telemetry, route_name
from netatlas.storage.backup import backup, compose_command, restore
from netatlas.storage.blobs import BlobStore
from netatlas.storage.database import MIN_FREE_BYTES, local_engine, transaction
from netatlas.storage.pipeline import Pipeline

pytest_plugins = ["test_storage"]


def test_fixed_telemetry_cardinality_and_private_summary(caplog: pytest.LogCaptureFixture) -> None:
    telemetry = Telemetry("read")
    telemetry.last_log -= 31
    with caplog.at_level(logging.INFO, logger="netatlas.operations"):
        for index in range(2000):
            telemetry.record(f"192.0.2.{index}?token=never-print", 503, 0.5)
    metrics = telemetry.metrics()
    assert len(telemetry.counts) == len(ROUTES) * 4
    assert 'route="other",status_class="5xx"} 2000' in metrics
    assert len(metrics) < 20000
    assert len(caplog.records) == 1
    assert json.loads(caplog.records[0].message)["event"] == "http_summary"
    assert "192.0.2" not in metrics + caplog.text
    assert "never-print" not in metrics + caplog.text
    assert route_name("/api/v1/endpoints/192.0.2.10/tcp/80/inspection") == "inspection"
    assert route_name("/private?secret") == "other"


def test_readiness_liveness_schema_blob_failure_recovery(
    pipeline: Pipeline,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    assert readiness(lambda: pipeline.engine, pipeline.blobs.root).status == "ready"
    with client_for(pipeline) as client:
        assert client.get("/readyz").status_code == 200
        pipeline.blobs.root.chmod(0o755)
        failed = client.get("/readyz")
        assert failed.status_code == 503 and failed.json()["blobs"] == "unavailable"
        assert client.get("/healthz").status_code == 200
        pipeline.blobs.root.chmod(0o700)
        assert client.get("/readyz").status_code == 200
        with pipeline.engine.begin() as connection:
            connection.execute(text("UPDATE alembic_version SET version_num='fixture'"))
        assert client.get("/readyz").json()["migration"] == "mismatch"
        with pipeline.engine.begin() as connection:
            connection.execute(text("UPDATE alembic_version SET version_num='0006'"))
        assert client.get("/readyz").status_code == 200
        usage = shutil.disk_usage(pipeline.blobs.root)
        monkeypatch.setattr(
            "netatlas.operations.status.shutil.disk_usage",
            lambda _: usage._replace(free=MIN_FREE_BYTES - 1),
        )
        assert client.get("/readyz").json()["status"] == "degraded"

    def unavailable() -> Any:
        raise OSError("postgres://private-password@192.0.2.1/raw-query")

    result = readiness(unavailable, tmp_path / "missing")
    assert result.status == "unavailable" and result.database == "unavailable"
    assert "password" not in result.model_dump_json()
    app = create_app(storage=tmp_path / "missing", blob_root=tmp_path / "absent")
    with TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 1234)) as client:
        assert client.get("/healthz").status_code == 200
        assert client.get("/readyz").status_code == 503
        assert not (tmp_path / "absent").exists()


def test_operational_counts_retention_optout_and_no_authority_mutation(pipeline: Pipeline) -> None:
    row = observation()
    pipeline.ingest(canonical(row), synthetic=True)
    c, b = Coordinator(pipeline), boot()
    queue(c)
    register(c, b)
    lease = claim(c, b)
    assert permit(c, b, lease).status == "granted"
    message = delivery(b, lease)
    c.exchange(message)
    c.exchange(message)
    result = snapshot(pipeline.engine, pipeline.blobs.root)
    assert result.permits_issued == result.delivery_receipts == 1
    assert result.retained_sources == result.outbox_events == 2
    assert result.stored_jobs.delivered == 1
    assert "192.0.2.10" not in result.model_dump_json()
    pipeline.maintain(suppress="127.0.0.1/32")
    result = snapshot(pipeline.engine, pipeline.blobs.root)
    assert result.delivery_receipts == 1 and result.retained_sources == 1
    assert result.stored_jobs.cancelled == 1
    c.stop()
    assert snapshot(pipeline.engine, pipeline.blobs.root).global_stopped
    assert readiness(lambda: pipeline.engine, pipeline.blobs.root).status == "ready"
    # A stale lease is reported, never reaped or given new measurement authority by a read.
    with pipeline.engine.begin() as connection:
        connection.execute(text("UPDATE control_jobs SET state='measuring'"))
        connection.execute(
            text("UPDATE control_attempts SET lease_until=clock_timestamp()-interval '1 second'")
        )
        connection.execute(text("INSERT INTO suppressions(network) VALUES ('192.0.2.0/24')"))
    result = snapshot(pipeline.engine, pipeline.blobs.root)
    assert result.overdue_leases == result.stored_jobs.measuring == 1
    assert result.retained_sources == 0 and result.removal_due_sources == 1


def test_read_load_busy_lane_recovers_without_sensitive_telemetry(
    pipeline: Pipeline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entered, release = threading.Event(), threading.Event()
    original = snapshot

    def held(*args: Any) -> Any:
        entered.set()
        assert release.wait(5)
        return original(*args)

    monkeypatch.setattr("netatlas.api.snapshot", held)
    with client_for(pipeline) as client, ThreadPoolExecutor(max_workers=16) as pool:
        pending = pool.submit(client.post, "/api/v1/operations", json={"schema_version": 1})
        assert entered.wait(3)
        try:
            futures = [
                pool.submit(
                    client.post,
                    "/api/v1/search",
                    json={"schema_version": 1, "query": {"text": "private fixture"}},
                )
                for _ in range(32)
            ]
            assert [f.result().status_code for f in futures] == [429] * 32
            assert client.get("/healthz").status_code == 200
        finally:
            release.set()
        assert pending.result().status_code == 200
        assert (
            client.post("/api/v1/search", json={"schema_version": 1, "query": {}}).status_code
            == 200
        )
        metrics = client.get("/metrics").text
        assert 'route="search",status_class="4xx"} 32' in metrics
        assert "private fixture" not in metrics
        assert client.get("/metrics", headers={"X-NetAtlas-Read": "0"}).status_code == 403
        assert client.get("/readyz", headers={"Cookie": "private"}).status_code == 403


def test_operations_lock_timeout_releases_lane(pipeline: Pipeline) -> None:
    with client_for(pipeline) as client:
        with transaction(pipeline.engine):
            started = time.monotonic()
            reply = client.post("/api/v1/operations", json={"schema_version": 1})
            assert reply.status_code == 503
            assert time.monotonic() - started < 4
            assert reply.json() == {"error": {"code": "unavailable"}}
            assert client.get("/healthz").status_code == 200
        assert client.post("/api/v1/operations", json={"schema_version": 1}).status_code == 200


def test_control_operational_routes_require_worker_secret(
    pipeline: Pipeline, tmp_path: Path
) -> None:
    provision(tmp_path / "credentials")
    credentials = Credentials.model_validate_json(
        read_private(tmp_path / "credentials/coordinator.json")
    )
    worker = credentials.workers[0]
    with TestClient(
        create_control_app(Coordinator(pipeline), credentials),
        base_url="http://127.0.0.1:8001",
        client=("127.0.0.1", 1234),
    ) as client:
        for route in ("healthz", "readyz", "metrics"):
            assert client.get("/" + route).status_code == 401
            headers = {
                "X-NetAtlas-Worker": str(worker.worker_id),
                "Authorization": "Bearer " + worker.token,
            }
            reply = client.get("/" + route, headers=headers)
            assert reply.status_code == 200
            assert worker.token not in reply.text and str(worker.worker_id) not in reply.text
            assert (
                client.get(
                    "/" + route, headers=headers | {"Origin": "http://127.0.0.1:5173"}
                ).status_code
                == 403
            )


def test_service_roles_delivery_read_denials_and_backup_restore(
    pipeline: Pipeline,
    tmp_path: Path,
) -> None:
    destination = tmp_path / "services"
    provision_access(pipeline.engine, destination)
    with pytest.raises(ValueError):
        provision_access(pipeline.engine, destination)
    read = local_engine(destination / "read")
    control = local_engine(destination / "control")
    roles = [str(read.url.username), str(control.url.username)]
    restored_engine = None
    name = "netatlas_restore_" + uuid4().hex
    created = False
    try:
        c = Coordinator(Pipeline(control, pipeline.blobs))
        queue(Coordinator(pipeline), settings=config(protocol_evidence=True))
        b = boot()
        register(c, b)
        lease = claim(c, b)
        assert permit(c, b, lease).status == "granted"
        from test_control import protocol_delivery

        source = protocol_delivery(b, lease)
        c.exchange(source)
        assert c.exchange(source).status == "replayed"
        with TestClient(
            create_app(engine=read, blobs=pipeline.blobs),
            base_url="http://127.0.0.1:8000",
            client=("127.0.0.1", 1234),
            headers={"X-NetAtlas-Read": "1"},
        ) as client:
            assert client.get("/readyz").status_code == 200
            assert (
                client.post("/api/v1/operations", json={"schema_version": 1}).json()[
                    "delivery_receipts"
                ]
                == 1
            )
            assert (
                client.post("/api/v1/search", json={"schema_version": 1, "query": {}}).status_code
                == 200
            )
            key = lease.endpoint
            reply = client.post(
                f"/api/v1/endpoints/{key.address}/tcp/{key.port}/inspection",
                json={
                    "schema_version": 1,
                    "query": {
                        "observation_id": str(source.observation.observation_id),
                        "source_sha256": source.source_sha256,
                    },
                },
            )
            assert reply.status_code == 200, reply.text
        for engine, sql in [
            (read, "DELETE FROM observations"),
            (read, "UPDATE control_switch SET stopped=false"),
            (control, "DELETE FROM observations"),
            (control, "DELETE FROM suppressions"),
            (control, "UPDATE control_switch SET stopped=false"),
            (control, "DELETE FROM control_campaigns"),
            (control, "DROP TABLE observations"),
            (control, "CREATE TABLE forbidden(x int)"),
        ]:
            with pytest.raises(SQLAlchemyError), engine.begin() as connection:
                connection.execute(text(sql))
        archive = tmp_path / "backup" / "drill"
        backup(pipeline.engine, pipeline.blobs, archive)
        # Restore ACL-free archive into a separate empty DB; role grants must not travel.
        subprocess.run(
            [*compose_command(), "createdb", "-U", "postgres", name],
            check=True,
            capture_output=True,
        )
        created = True
        restored_engine = create_engine(
            pipeline.engine.url.set(database=name), hide_parameters=True
        )
        blobs = BlobStore(tmp_path / "restored")
        assert restore(restored_engine, blobs, archive)["observations"] == 1
        p = Pipeline(restored_engine, blobs)
        assert Coordinator(p).is_stopped()
        assert Coordinator(p).status() == {"cancelled": 1}
        p.maintain(suppress="127.0.0.1/32")
        assert snapshot(restored_engine, blobs.root).retained_sources == 0
        with restored_engine.connect() as connection:
            assert not connection.execute(
                text("SELECT has_table_privilege(:role,'observations','SELECT')"),
                {"role": roles[0]},
            ).scalar_one()
    finally:
        read.dispose()
        control.dispose()
        if restored_engine:
            restored_engine.dispose()
        if created:
            subprocess.run(
                [*compose_command(), "dropdb", "-U", "postgres", name],
                check=True,
                capture_output=True,
            )
        with pipeline.engine.begin() as connection:
            for role in roles:
                connection.execute(text(f'DROP OWNED BY "{role}"'))
                connection.execute(text(f'DROP ROLE "{role}"'))


def test_low_disk_preserves_pending_and_rolls_back_source(
    pipeline: Pipeline,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from test_storage import scalar

    from netatlas.control.files import Pending, Spool

    c, b = Coordinator(pipeline), boot()
    queue(c)
    register(c, b)
    lease = claim(c, b)
    spool = Spool(tmp_path / "spool")
    reservation = Pending(lease=lease)
    spool.save(reservation)
    usage = shutil.disk_usage(pipeline.blobs.root)
    monkeypatch.setattr(
        "netatlas.storage.database.shutil.disk_usage", lambda _: usage._replace(free=1)
    )
    with pytest.raises(OSError):
        spool.save(Pending(lease=lease, delivery=delivery(b, lease)))
    assert spool.pending() == reservation
    with pytest.raises(OSError):
        pipeline.ingest(canonical(observation()), synthetic=True)
    assert scalar(pipeline, "SELECT count(*) FROM observations") == 0
    assert scalar(pipeline, "SELECT count(*) FROM outbox") == 0
    assert list(pipeline.blobs.root.iterdir()) == []


def test_rotation_preserves_worker_authority_identity_and_revokes_old_tokens(
    pipeline: Pipeline,
    tmp_path: Path,
) -> None:
    from netatlas.control.files import Spool

    provision(tmp_path / "old")
    old = Credentials.model_validate_json(read_private(tmp_path / "old/coordinator.json"))
    provision(tmp_path / "new", previous=old)
    new = Credentials.model_validate_json(read_private(tmp_path / "new/coordinator.json"))
    assert [c.worker_id for c in old.workers] == [c.worker_id for c in new.workers]
    assert all(a.token != b.token for a, b in zip(old.workers, new.workers, strict=True))
    spool = Spool(tmp_path / "spool")
    first = spool.boot(old.workers[0].worker_id)
    register(Coordinator(pipeline), first)
    second = spool.boot(new.workers[0].worker_id)
    assert second.generation == first.generation + 1
    app = create_control_app(Coordinator(pipeline), new)
    with TestClient(app, base_url="http://127.0.0.1:8001", client=("127.0.0.1", 1234)) as client:
        message = {
            "schema_version": 1,
            "action": "register",
            "worker_id": str(second.worker_id),
            "session_id": str(second.session_id),
            "generation": second.generation,
        }
        for credentials, expected in ((old, 401), (new, 200)):
            headers = {
                "X-NetAtlas-Worker": str(second.worker_id),
                "Authorization": "Bearer " + credentials.workers[0].token,
            }
            assert (
                client.post("/control/v1/exchange", json=message, headers=headers).status_code
                == expected
            )


def test_control_load_eight_requests_backpressure_recovers(
    pipeline: Pipeline,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provision(tmp_path / "credentials")
    credentials = Credentials.model_validate_json(
        read_private(tmp_path / "credentials/coordinator.json")
    )
    c = Coordinator(pipeline)
    original = c.exchange
    release, entered = threading.Event(), threading.Event()
    lock = threading.Lock()
    count = 0

    def held(message: Any) -> Any:
        nonlocal count
        with lock:
            count += 1
            if count == 8:
                entered.set()
        assert release.wait(8)
        return original(message)

    monkeypatch.setattr(c, "exchange", held)
    worker = credentials.workers[0]
    headers = {
        "X-NetAtlas-Worker": str(worker.worker_id),
        "Authorization": "Bearer " + worker.token,
    }
    message = {
        "schema_version": 1,
        "action": "register",
        "worker_id": str(worker.worker_id),
        "session_id": str(uuid4()),
        "generation": 1,
    }
    with (
        TestClient(
            create_control_app(c, credentials),
            base_url="http://127.0.0.1:8001",
            client=("127.0.0.1", 1234),
            headers=headers,
        ) as client,
        ThreadPoolExecutor(max_workers=16) as pool,
    ):
        # The HTTP admission bound is independent of asyncio's CPU-dependent default
        # executor (which can have fewer than eight threads on a small CI runner).
        # Give the controlled held-call fixture eight threads so its barrier can open.
        async def configure_executor() -> None:
            asyncio.get_running_loop().set_default_executor(ThreadPoolExecutor(max_workers=8))

        assert client.portal is not None
        client.portal.call(configure_executor)
        pending = [pool.submit(client.post, "/control/v1/exchange", json=message) for _ in range(8)]
        assert entered.wait(5)
        try:
            rejected = [
                pool.submit(client.post, "/control/v1/exchange", json=message) for _ in range(24)
            ]
            assert [f.result().status_code for f in rejected] == [429] * 24
            assert client.get("/healthz").status_code == 200
            assert count == 8
        finally:
            release.set()
        assert [f.result().status_code for f in pending] == [200] * 8
        assert client.post("/control/v1/exchange", json=message).status_code == 200
        assert 'route="control",status_class="4xx"} 24' in client.get("/metrics").text


def test_backup_retention_rejects_before_restore_write(pipeline: Pipeline, tmp_path: Path) -> None:
    from datetime import UTC, datetime, timedelta

    archive = tmp_path / "backups" / "drill"
    backup(pipeline.engine, pipeline.blobs, archive)
    manifest = json.loads((archive / "manifest.json").read_text())
    assert manifest["version"] == 2
    manifest["created_at"] = (datetime.now(UTC) - timedelta(days=8)).isoformat()
    manifest["expires_at"] = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    (archive / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="retention"):
        restore(pipeline.engine, pipeline.blobs, archive)
