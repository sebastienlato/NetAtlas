"""Bounded dependency checks and read-only aggregate operational snapshots."""

import os
import shutil
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Literal

from sqlalchemy import Engine, text

from netatlas.domain import Model
from netatlas.storage.blobs import BlobStore
from netatlas.storage.database import LOCK_ID, MIN_FREE_BYTES

HEAD = "0006"


class Ready(Model):
    status: Literal["ready", "degraded", "unavailable"]
    database: Literal["ok", "unavailable"]
    migration: Literal["ok", "mismatch", "unknown"]
    blobs: Literal["ok", "unavailable"]
    capacity: Literal["ok", "low", "unknown"]


class OperationsRequest(Model):
    schema_version: Literal[1]


class JobCounts(Model):
    queued: int = 0
    leased: int = 0
    measuring: int = 0
    delivered: int = 0
    uncertain: int = 0
    cancelled: int = 0
    failed: int = 0


class Snapshot(Model):
    schema_version: Literal[1] = 1
    checked_at: datetime
    global_stopped: bool
    stored_jobs: JobCounts
    overdue_leases: int
    permits_issued: int
    delivery_receipts: int
    retained_sources: int
    removal_due_sources: int
    outbox_events: int
    registered_workers: int
    recent_workers: int
    blob_free_bytes: int
    readiness: Ready


def readiness(engine: Callable[[], Engine], root: Path, *, writable: bool = False) -> Ready:
    database: Literal["ok", "unavailable"] = "unavailable"
    schema: Literal["ok", "mismatch", "unknown"] = "unknown"
    blobs: Literal["ok", "unavailable"] = "unavailable"
    capacity: Literal["ok", "low", "unknown"] = "unknown"
    try:
        with engine().begin() as connection:
            connection.execute(text("SET LOCAL statement_timeout = '1s'"))
            connection.execute(text("SET LOCAL lock_timeout = '1s'"))
            connection.execute(text("SELECT 1"))
            database = "ok"
            schema = "mismatch"
            versions: list[str] = list(
                connection.execute(text("SELECT version_num FROM alembic_version")).scalars()
            )
            if versions == [HEAD]:
                schema = "ok"
    except Exception:
        pass  # No exception values, paths, SQL or connection details cross this boundary.
    try:
        BlobStore(root, create=False)
        if os.access(root, os.R_OK | os.X_OK | (os.W_OK if writable else 0)):
            blobs = "ok"
            capacity = "ok" if shutil.disk_usage(root).free >= MIN_FREE_BYTES else "low"
    except OSError, ValueError:
        pass
    status: Literal["ready", "degraded", "unavailable"] = "ready"
    if database != "ok" or schema != "ok" or blobs != "ok":
        status = "unavailable"
    elif capacity != "ok":
        status = "degraded"
    return Ready(status=status, database=database, migration=schema, blobs=blobs, capacity=capacity)


def snapshot(engine: Engine, root: Path) -> Snapshot:
    # Never reap leases, expire sources, execute collectors, or mutate authority here.
    ready = readiness(lambda: engine, root)
    if ready.status == "unavailable":
        raise ValueError("dependencies unavailable")
    with engine.begin() as connection:
        connection.execute(text("SET TRANSACTION READ ONLY"))
        connection.execute(text("SET LOCAL statement_timeout = '5s'"))
        connection.execute(text("SET LOCAL lock_timeout = '1s'"))
        connection.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": LOCK_ID})
        at: datetime = connection.execute(text("SELECT clock_timestamp()")).scalar_one()
        jobs: dict[str, int] = {
            str(row[0]): int(row[1])
            for row in connection.execute(
                text("SELECT state, count(*) FROM control_jobs GROUP BY state")
            )
        }
        counts = (
            connection.execute(
                text("""
            SELECT
              (SELECT stopped FROM control_switch WHERE singleton=true) AS global_stopped,
              (SELECT count(*) FROM control_attempts a JOIN control_jobs j ON j.id=a.job_id
                WHERE a.fence=j.fence AND j.state IN ('leased','measuring')
                AND a.lease_until <= :at) AS overdue_leases,
              (SELECT coalesce(sum(connections),0) FROM control_attempts) AS permits_issued,
              (SELECT count(*) FROM control_attempts WHERE source_sha256 IS NOT NULL)
                AS delivery_receipts,
              (SELECT count(*) FROM observations o WHERE o.expires_at > :at AND NOT EXISTS
                (SELECT 1 FROM suppressions s WHERE o.address <<= s.network)) AS retained_sources,
              (SELECT count(*) FROM observations o WHERE o.expires_at <= :at OR EXISTS
                (SELECT 1 FROM suppressions s WHERE o.address <<= s.network))
                AS removal_due_sources,
              (SELECT count(*) FROM outbox) AS outbox_events,
              (SELECT count(*) FROM control_workers) AS registered_workers,
              (SELECT count(*) FROM control_workers WHERE heartbeat_at > :at - interval '10 seconds'
                AND heartbeat_at <= :at) AS recent_workers
        """),
                {"at": at},
            )
            .mappings()
            .one()
        )
        return Snapshot(
            checked_at=at,
            stored_jobs=JobCounts.model_validate(jobs),
            blob_free_bytes=shutil.disk_usage(root).free,
            readiness=ready,
            **counts,
        )
