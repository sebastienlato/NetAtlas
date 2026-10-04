"""Real PostgreSQL acceptance tests; opt in with NETATLAS_TEST_DB=1 (local Compose)."""

import base64
import json
import os
import subprocess
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import DBAPIError

from netatlas.config import Settings
from netatlas.derivations.engine import canonical, digest
from netatlas.derivations.offline import load_pack
from netatlas.examples import example_observation
from netatlas.observation import Observation
from netatlas.storage.backup import backup, compose_command, restore
from netatlas.storage.blobs import BlobStore
from netatlas.storage.database import local_engine, migrate, transaction
from netatlas.storage.pipeline import Pipeline, mirror_handler


def observation(
    *,
    identity: UUID | None = None,
    age: int = 0,
    outcome: str = "open",
    address: str = "192.0.2.10",
    body: bytes | None = b"HTTP/1.1 200 OK\r\nServer: nginx\r\n\r\nfixture",
) -> Observation:
    row = example_observation(Settings()).model_dump(mode="json")
    row["observation_id"] = str(identity or uuid4())
    row["target"]["address"] = address
    row["endpoint"]["address"] = address
    row["started_at"] = datetime.now(UTC) - timedelta(seconds=age + 1)
    row["finished_at"] = row["started_at"] + timedelta(milliseconds=25)
    row["outcome"] = outcome
    row["response"] = {"body_base64": base64.b64encode(body).decode()} if body is not None else None
    if outcome != "open":
        row["service"] = row["response"] = None
    return Observation.model_validate(row)


@pytest.fixture
def empty_engine() -> Iterator[Engine]:
    if os.environ.get("NETATLAS_TEST_DB") != "1":
        pytest.skip("requires local Compose; run make check-db")
    admin = local_engine(Path("data/storage"))
    name = "netatlas_test_" + uuid4().hex
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    engine = create_engine(admin.url.set(database=name), hide_parameters=True)
    try:
        yield engine
    finally:
        engine.dispose()
        with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        admin.dispose()


@pytest.fixture
def pipeline(empty_engine: Engine, tmp_path: Path) -> Pipeline:
    migrate(empty_engine)
    return Pipeline(empty_engine, BlobStore(tmp_path / "blobs"))


def scalar(pipeline: Pipeline, sql: str) -> Any:
    with pipeline.engine.connect() as connection:
        return connection.execute(text(sql)).scalar_one()


def fail_at(stage: str) -> Any:
    def hook(actual: str) -> None:
        if actual == stage:
            raise RuntimeError("injected failure")

    return hook


def test_blob_permissions_integrity_and_gc(tmp_path: Path) -> None:
    store = BlobStore(tmp_path / "blobs")
    sha = store.put(b"hostile <script>fixture</script>")
    assert store.put(b"hostile <script>fixture</script>") == sha
    assert (store.root / sha).stat().st_mode & 0o777 == 0o600
    assert store.root.stat().st_mode & 0o777 == 0o700
    assert store.collect({sha}) == 0
    (store.root / sha).write_bytes(b"corruption")
    with pytest.raises(ValueError, match="integrity"):
        store.read(sha)
    assert store.collect(set()) == 1
    with pytest.raises(ValueError):
        store.put(b"x" * 65537)
    with pytest.raises(ValueError):
        store.read("../secret")


def test_blob_symlink_and_public_directory_rejected(tmp_path: Path) -> None:
    public = tmp_path / "public"
    public.mkdir(mode=0o755)
    with pytest.raises(ValueError):
        BlobStore(public)
    store = BlobStore(tmp_path / "private")
    (store.root / digest(b"x")).symlink_to(public)
    with pytest.raises(OSError):
        store.put(b"x")


def test_duplicate_conflict_and_blob_dedup_preserve_history(pipeline: Pipeline) -> None:
    first = observation()
    assert pipeline.ingest(canonical(first), synthetic=True) == "inserted"
    assert pipeline.ingest(first.model_dump_json(indent=2).encode(), synthetic=True) == "replayed"
    second = observation()
    pipeline.ingest(canonical(second), synthetic=True)
    assert scalar(pipeline, "SELECT count(*) FROM observations") == 2
    assert scalar(pipeline, "SELECT count(*) FROM blobs") == 1
    assert scalar(pipeline, "SELECT count(*) FROM evidence_refs") == 2
    assert scalar(pipeline, "SELECT count(*) FROM outbox") == 2
    changed = observation(identity=first.observation_id, body=b"different")
    with pytest.raises(ValueError, match="conflict"):
        pipeline.ingest(canonical(changed), synthetic=True)
    assert pipeline.load(first.observation_id) == first
    assert pipeline.verify() == {"observations": 2, "derivations": 0}


def test_reordered_negative_and_empty_open_preserve_last_evidence(pipeline: Pipeline) -> None:
    old = observation(age=40)
    new = observation(age=30)
    negative = observation(age=10, outcome="timeout")
    empty = observation(age=20, body=None)
    for row in (negative, new, empty, old):
        pipeline.ingest(canonical(row), synthetic=True)
    with pipeline.engine.connect() as connection:
        projection = connection.execute(text("SELECT * FROM current_services")).mappings().one()
        assert projection["last_attempt"] == negative.observation_id
        assert projection["last_open"] == empty.observation_id
        assert projection["last_evidence"] == new.observation_id


def test_tie_break_is_uuid_not_arrival_order(pipeline: Pipeline) -> None:
    row = observation(identity=UUID(int=2))
    smaller = Observation.model_validate(row.model_dump() | {"observation_id": UUID(int=1)})
    for item in (row, smaller):
        pipeline.ingest(canonical(item), synthetic=True)
    assert scalar(pipeline, "SELECT last_attempt FROM current_services") == row.observation_id


@pytest.mark.parametrize("stage", ["after_blobs", "before_commit", "after_commit"])
def test_failure_and_lost_ack_replay(pipeline: Pipeline, stage: str) -> None:
    row = observation()
    failed = Pipeline(pipeline.engine, pipeline.blobs, hook=fail_at(stage))
    with pytest.raises(RuntimeError):
        failed.ingest(canonical(row), synthetic=True)
    committed = stage == "after_commit"
    assert scalar(pipeline, "SELECT count(*) FROM observations") == int(committed)
    assert scalar(pipeline, "SELECT count(*) FROM outbox") == int(committed)
    assert pipeline.collect() == (0 if committed else 1)
    assert pipeline.ingest(canonical(row), synthetic=True) == (
        "replayed" if committed else "inserted"
    )
    assert pipeline.verify()["observations"] == 1


def test_database_error_rolls_back_refs_projection_outbox(pipeline: Pipeline) -> None:
    row = observation()
    with pipeline.engine.begin() as connection:
        connection.execute(
            text("""
            CREATE FUNCTION reject_event() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'injected transaction failure'; END $$;
            CREATE TRIGGER reject_event BEFORE INSERT ON outbox
            FOR EACH ROW EXECUTE FUNCTION reject_event();
        """)
        )
    with pytest.raises(DBAPIError):
        pipeline.ingest(canonical(row), synthetic=True)
    for table in ("observations", "blobs", "evidence_refs", "current_services", "outbox"):
        assert scalar(pipeline, f"SELECT count(*) FROM {table}") == 0
    assert pipeline.collect() == 1
    with pipeline.engine.begin() as connection:
        connection.execute(text("DROP TRIGGER reject_event ON outbox"))
    pipeline.ingest(canonical(row), synthetic=True)


def test_concurrent_duplicate_and_cleanup_are_serialized(pipeline: Pipeline) -> None:
    row = observation()
    with ThreadPoolExecutor(max_workers=4) as executor:
        tasks = [executor.submit(pipeline.ingest, canonical(row), synthetic=True) for _ in range(3)]
        gc = executor.submit(pipeline.collect)
        results = [task.result() for task in tasks]
        gc.result()
    assert sorted(results) == ["inserted", "replayed", "replayed"]
    assert pipeline.verify()["observations"] == 1


def test_v1_v2_and_independent_pack_versions_replay(pipeline: Pipeline) -> None:
    row = observation()
    legacy = row.model_dump(mode="json")
    legacy.pop("protocol_evidence")
    legacy["schema_version"] = 1
    pipeline.ingest(json.dumps(legacy).encode(), synthetic=True)
    assert pipeline.load(row.observation_id).schema_version == 1
    pack = load_pack()
    first = pipeline.derive(row.observation_id, pack)
    assert pipeline.derive(row.observation_id, pack) == first
    changed = type(pack).model_validate(pack.model_dump() | {"version": "1.0.1"})
    assert pipeline.derive(row.observation_id, changed) != first
    assert pipeline.verify() == {"observations": 1, "derivations": 2}
    assert scalar(pipeline, "SELECT count(*) FROM packs") == 2
    assert scalar(pipeline, "SELECT count(*) FROM outbox") == 3


def test_protocol_and_certificate_references_roundtrip(pipeline: Pipeline) -> None:
    from netatlas.domain import CapturedResponse, Outcome
    from netatlas.evidence import Exchange, ProtocolEvidence, TlsMetadata

    row = observation(body=None)
    capture = CapturedResponse(
        body_base64=base64.b64encode(b"SSH-2.0-OpenSSH_fixture\r\n").decode()
    )
    cert = CapturedResponse(body_base64=base64.b64encode(b"synthetic DER bytes").decode())
    # Contract permits opaque certificate bytes; storage never parses identities.
    evidence = ProtocolEvidence(
        exchanges=(
            Exchange(
                connection=1,
                probe="tls",
                tcp_outcome=Outcome.OPEN,
                status="complete",
                response=capture,
                tls=TlsMetadata(
                    version="TLSv1.3", cipher="fixture", secret_bits=128, certificates=(cert,)
                ),
            ),
        ),
        termination="finished",
        received_bytes=100,
        sent_bytes=20,
        retained_bytes=len(base64.b64decode(capture.body_base64)) + 19,
    )
    row = Observation.model_validate(row.model_dump() | {"protocol_evidence": evidence})
    pipeline.ingest(canonical(row), synthetic=True)
    assert pipeline.load(row.observation_id) == row
    pipeline.derive(row.observation_id, load_pack())
    assert scalar(pipeline, "SELECT count(*) FROM evidence_refs") == 2


@pytest.mark.parametrize("stage", ["after_consumer_effect", "before_commit", "after_commit"])
def test_consumer_failure_atomic_receipt_and_retry(pipeline: Pipeline, stage: str) -> None:
    row = observation()
    pipeline.ingest(canonical(row), synthetic=True)
    failed = Pipeline(pipeline.engine, pipeline.blobs, hook=fail_at(stage))
    with pytest.raises(RuntimeError):
        failed.consume()
    committed = stage == "after_commit"
    assert scalar(pipeline, "SELECT count(*) FROM consumer_receipts") == int(committed)
    assert scalar(pipeline, "SELECT count(*) FROM consumer_observations") == int(committed)
    assert pipeline.consume()["delivered"] == int(not committed)
    assert pipeline.consume()["delivered"] == 0
    assert pipeline.consume(replay=True)["delivered"] == 1
    assert scalar(pipeline, "SELECT count(*) FROM consumer_observations") == 1


def test_replay_pagination_and_second_consumer(pipeline: Pipeline) -> None:
    for _ in range(3):
        pipeline.ingest(canonical(observation()), synthetic=True)
    assert pipeline.consume("second")["delivered"] == 3
    cursor = 0
    for _ in range(3):
        result = pipeline.consume(limit=1, replay=True, after=cursor)
        assert result["delivered"] == 1
        assert result["cursor"] > cursor
        cursor = result["cursor"]
    assert pipeline.consume(replay=True, after=cursor)["delivered"] == 0
    assert scalar(pipeline, "SELECT count(*) FROM consumer_observations") == 6


def test_expiry_removal_shared_blob_and_projection_rebuild(pipeline: Pipeline) -> None:
    old = observation(age=29 * 86400)
    new = observation()
    for row in (old, new):
        pipeline.ingest(canonical(row), synthetic=True)
        pipeline.derive(row.observation_id, load_pack())
    pipeline.consume()
    result = pipeline.maintain(now=datetime.now(UTC) + timedelta(days=2))
    assert result == {"removed": 1, "blobs_collected": 0}
    assert scalar(pipeline, "SELECT last_evidence FROM current_services") == new.observation_id
    assert scalar(pipeline, "SELECT count(*) FROM derivations") == 1
    assert scalar(pipeline, "SELECT count(*) FROM consumer_observations") == 1
    assert pipeline.verify()["observations"] == 1
    with pytest.raises(ValueError, match="removed"):
        pipeline.ingest(canonical(old), synthetic=True)
    result = pipeline.maintain(suppress="192.0.2.0/24")
    assert result == {"removed": 1, "blobs_collected": 1}
    for table in (
        "observations",
        "derivations",
        "current_services",
        "packs",
        "consumer_observations",
    ):
        assert scalar(pipeline, f"SELECT count(*) FROM {table}") == 0
    pipeline.consume(replay=True)
    assert scalar(pipeline, "SELECT count(*) FROM consumer_observations") == 0
    with pytest.raises(ValueError, match="suppressed"):
        pipeline.ingest(canonical(observation()), synthetic=True)


def test_removal_crash_before_gc_recovers_without_resurrection(pipeline: Pipeline) -> None:
    row = observation(address="2001:db8::10")
    pipeline.ingest(canonical(row), synthetic=True)
    failed = Pipeline(pipeline.engine, pipeline.blobs, hook=fail_at("after_removal_commit"))
    with pytest.raises(RuntimeError):
        failed.maintain(suppress="2001:db8::/32")
    assert scalar(pipeline, "SELECT count(*) FROM observations") == 0
    assert pipeline.collect() == 1
    with pytest.raises(ValueError):
        pipeline.ingest(canonical(row), synthetic=True)


def test_out_of_order_deletion_event_cannot_resurrect(pipeline: Pipeline) -> None:
    row = observation()
    pipeline.ingest(canonical(row), synthetic=True)
    pipeline.maintain(suppress="192.0.2.10/32")
    with transaction(pipeline.engine) as connection:
        for _ in range(2):
            mirror_handler(connection, "out_of_order", row.observation_id)
    assert scalar(pipeline, "SELECT count(*) FROM consumer_observations") == 0


@pytest.mark.parametrize(
    "variant",
    [
        "missing_opt_in",
        "private_address",
        "expired",
        "future",
        "oversized",
        "unknown_schema",
        "duplicate_key",
    ],
)
def test_invalid_inputs_fail_before_publication(pipeline: Pipeline, variant: str) -> None:
    row = observation(
        age=31 * 86400 if variant == "expired" else -600 if variant == "future" else 0,
        address="10.0.0.1" if variant == "private_address" else "192.0.2.10",
    )
    data = canonical(row)
    if variant == "oversized":
        data = b"x" * (1048576 + 1)
    elif variant == "unknown_schema":
        data = data.replace(b'"schema_version":2', b'"schema_version":9')
    elif variant == "duplicate_key":
        data = b'{"schema_version":2,' + data[1:]
    with pytest.raises(ValueError):
        pipeline.ingest(data, synthetic=variant != "missing_opt_in")
    assert scalar(pipeline, "SELECT count(*) FROM observations") == 0
    assert list(pipeline.blobs.root.iterdir()) == []


def test_missing_or_corrupt_blob_never_acknowledges_replay(pipeline: Pipeline) -> None:
    row = observation()
    pipeline.ingest(canonical(row), synthetic=True)
    blob = next(pipeline.blobs.root.iterdir())
    blob.write_bytes(b"bad")
    with pytest.raises(ValueError, match="integrity"):
        pipeline.ingest(canonical(row), synthetic=True)
    blob.unlink()
    with pytest.raises(OSError):
        pipeline.ingest(canonical(row), synthetic=True)


@pytest.mark.parametrize(
    "table", ["observations", "derivations", "packs", "evidence_refs", "blobs"]
)
def test_history_updates_rejected(pipeline: Pipeline, table: str) -> None:
    row = observation()
    pipeline.ingest(canonical(row), synthetic=True)
    pipeline.derive(row.observation_id, load_pack())
    column = {
        "observations": "document",
        "derivations": "document",
        "packs": "document",
        "evidence_refs": "pointer",
        "blobs": "size",
    }[table]
    with (
        pytest.raises(DBAPIError, match="immutable history"),
        pipeline.engine.begin() as connection,
    ):
        connection.execute(text(f"UPDATE {table} SET {column}={column}"))


def test_upgrade_backfill_and_idempotent_migration(empty_engine: Engine) -> None:
    migrate(empty_engine, "0001")
    row = observation()
    with empty_engine.begin() as connection:
        connection.execute(
            text("""
            INSERT INTO observations (id, source_sha256, schema_version, endpoint_key, address,
              transport, port, started_at, finished_at, outcome, has_evidence, document)
            VALUES (:id, :sha, 2, :key, '192.0.2.10', 'tcp', 80, :start, :end,
                    'open', false, CAST(:document AS jsonb))
        """),
            {
                "id": row.observation_id,
                "sha": digest(canonical(row)),
                "key": row.endpoint.key,
                "start": row.started_at,
                "end": row.finished_at,
                "document": row.model_dump_json(),
            },
        )
    migrate(empty_engine)
    migrate(empty_engine)
    with empty_engine.connect() as connection:
        result = connection.execute(text("SELECT * FROM observations")).mappings().one()
        assert result["expires_at"] == row.finished_at + timedelta(days=30)
        assert result["document"] == row.model_dump(mode="json")
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0002"
        )


def test_backup_restore_history_blobs_derivations_outbox(
    pipeline: Pipeline, tmp_path: Path
) -> None:
    row = observation()
    pipeline.ingest(canonical(row), synthetic=True)
    pipeline.derive(row.observation_id, load_pack())
    pipeline.consume(limit=1)
    saved = tmp_path / "backups" / "snapshot"
    backup(pipeline.engine, pipeline.blobs, saved)
    assert (saved / "database.dump").stat().st_mode & 0o777 == 0o600
    name = "netatlas_restore_" + uuid4().hex
    subprocess.run([*compose_command(), "createdb", "-U", "postgres", name], check=True)
    restored_engine = create_engine(pipeline.engine.url.set(database=name), hide_parameters=True)
    try:
        store = BlobStore(tmp_path / "restored-blobs")
        assert restore(restored_engine, store, saved) == {"observations": 1, "derivations": 1}
        recovered = Pipeline(restored_engine, store)
        assert recovered.load(row.observation_id) == row
        assert recovered.ingest(canonical(row), synthetic=True) == "replayed"
        assert recovered.consume()["delivered"] == 1
        assert scalar(recovered, "SELECT count(*) FROM consumer_observations") == 1
        with pytest.raises(ValueError, match="empty"):
            restore(restored_engine, store, saved)
    finally:
        restored_engine.dispose()
        subprocess.run([*compose_command(), "dropdb", "-U", "postgres", name], check=True)


def test_cli_redacts_invalid_input_and_partial_file_replays(
    pipeline: Pipeline, tmp_path: Path
) -> None:
    # Exercise the installed CLI against the isolated database and private blob root.
    root = Path("data") / ("test-storage-" + uuid4().hex)
    root.mkdir(mode=0o700)
    import shutil

    try:
        shutil.copyfile("data/storage/postgres-password", root / "postgres-password")
        (root / "postgres-password").chmod(0o600)
        (root / "connection.json").write_text(
            json.dumps(
                {"host": "127.0.0.1", "port": 55432, "database": pipeline.engine.url.database}
            )
        )
        (root / "connection.json").chmod(0o600)
        source = tmp_path / "input.jsonl"
        row = observation()
        source.write_bytes(canonical(row) + b'\n{"secret":"DO_NOT_LOG"}\n')
        command = [
            "netatlas-store",
            "--root",
            str(root),
            "ingest",
            "--input",
            str(source),
            "--synthetic",
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        assert result.returncode == 2
        assert "DO_NOT_LOG" not in result.stderr + result.stdout
        assert json.loads(result.stdout)["status"] == "inserted"
        source.write_bytes(canonical(row) + b"\n")
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        assert json.loads(result.stdout.splitlines()[0])["status"] == "replayed"
    finally:
        shutil.rmtree(root)


def test_blob_fsync_failure_never_commits(
    pipeline: Pipeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    def failed_sync(fd: int) -> None:
        raise OSError("injected disk failure")

    monkeypatch.setattr("netatlas.storage.blobs.os.fsync", failed_sync)
    with pytest.raises(OSError):
        pipeline.ingest(canonical(observation()), synthetic=True)
    assert scalar(pipeline, "SELECT count(*) FROM observations") == 0
    assert scalar(pipeline, "SELECT count(*) FROM outbox") == 0
    assert list(pipeline.blobs.root.iterdir()) == []


def test_removal_transaction_failure_keeps_live_blobs(pipeline: Pipeline) -> None:
    row = observation()
    pipeline.ingest(canonical(row), synthetic=True)
    failed = Pipeline(pipeline.engine, pipeline.blobs, hook=fail_at("before_commit"))
    with pytest.raises(RuntimeError):
        failed.maintain(suppress="192.0.2.0/24")
    assert scalar(pipeline, "SELECT count(*) FROM suppressions") == 0
    assert pipeline.collect() == 0
    assert pipeline.load(row.observation_id) == row


def test_derivation_transaction_and_ack_failures_replay(pipeline: Pipeline) -> None:
    row = observation()
    pipeline.ingest(canonical(row), synthetic=True)
    for stage in ("before_commit", "after_commit"):
        failed = Pipeline(pipeline.engine, pipeline.blobs, hook=fail_at(stage))
        with pytest.raises(RuntimeError):
            failed.derive(row.observation_id, load_pack())
        assert scalar(pipeline, "SELECT count(*) FROM derivations") == int(stage == "after_commit")
    pipeline.derive(row.observation_id, load_pack())
    assert pipeline.verify()["derivations"] == 1
    assert scalar(pipeline, "SELECT count(*) FROM outbox") == 2


def test_restore_rejects_corrupt_archive_before_writing(pipeline: Pipeline, tmp_path: Path) -> None:
    saved = tmp_path / "backups" / "snapshot"
    backup(pipeline.engine, pipeline.blobs, saved)
    with (saved / "database.dump").open("ab") as stream:
        stream.write(b"corrupt")
    with pytest.raises(ValueError, match="integrity"):
        restore(pipeline.engine, pipeline.blobs, saved)


def test_negative_only_and_empty_evidence_have_no_success(pipeline: Pipeline) -> None:
    pipeline.ingest(canonical(observation(outcome="closed")), synthetic=True)
    assert scalar(pipeline, "SELECT last_open FROM current_services") is None
    pipeline.ingest(canonical(observation(body=b"")), synthetic=True)
    assert scalar(pipeline, "SELECT last_open FROM current_services") is not None
    assert scalar(pipeline, "SELECT last_evidence FROM current_services") is None


def test_backup_rejects_mismatched_compose_server(
    pipeline: Pipeline, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def wrong_server(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 0, stdout="different-server\n", stderr="")

    monkeypatch.setattr("netatlas.storage.backup.subprocess.run", wrong_server)
    output = tmp_path / "backups" / "snapshot"
    with pytest.raises(ValueError, match="does not match"):
        backup(pipeline.engine, pipeline.blobs, output)
    assert not output.exists()
    assert list(output.parent.iterdir()) == []
