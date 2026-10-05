"""Reproduce qualified authored thesis evaluation from the repository root."""

import argparse
import asyncio
import json
import os
import platform
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import Engine, create_engine, text

from netatlas import __version__
from netatlas.config import Settings
from netatlas.derivations.engine import canonical, digest
from netatlas.enrichment.offline import publish
from netatlas.evaluation import loopback
from netatlas.evaluation.corpus import load_corpus, source
from netatlas.evaluation.performance import trial
from netatlas.evaluation.scenarios import coverage, functional
from netatlas.evaluation.scoring import evaluate
from netatlas.storage.blobs import BlobStore
from netatlas.storage.database import local_engine, migrate
from netatlas.storage.pipeline import Pipeline


@contextmanager
def disposable(admin: Engine) -> Iterator[Pipeline]:
    """Only the freshly allocated name may be dropped, including on ordinary failure."""
    name = "netatlas_test_eval_" + uuid4().hex
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    engine = create_engine(
        admin.url.set(database=name),
        hide_parameters=True,
        pool_size=2,
        max_overflow=0,
        pool_timeout=2,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 2},
    )
    try:
        migrate(engine)
        with tempfile.TemporaryDirectory(prefix="netatlas-evaluation-") as directory:
            yield Pipeline(engine, BlobStore(Path(directory) / "blobs"))
    finally:
        engine.dispose()
        with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))


def provenance(admin: Engine) -> dict[str, Any]:
    def git(*args: str) -> str:
        return subprocess.check_output(["git", *args], text=True).strip()

    paths = sorted(
        {
            *Path("src/netatlas").rglob("*.py"),
            *Path("src/netatlas").rglob("*.json"),
            *Path("tests/fixtures").rglob("*.json"),
            Path("pyproject.toml"),
            Path("uv.lock"),
            Path("web/package-lock.json"),
        }
    )
    hashes = {str(p): digest(p.read_bytes()) for p in paths}
    with admin.connect() as conn:
        version = conn.execute(
            text("SELECT version(),postgis_full_version(),clock_timestamp()")
        ).one()
        settings: dict[str, str] = {
            name: conn.execute(text(f"SHOW {name}")).scalar_one()
            for name in ("shared_buffers", "max_connections", "fsync", "synchronous_commit")
        }
    return {
        "package": __version__,
        "git_revision": git("rev-parse", "HEAD"),
        "git_dirty": bool(git("status", "--porcelain")),
        "evaluated_tree_sha256": digest(json.dumps(hashes, sort_keys=True).encode()),
        "input_file_sha256": hashes,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "host_logical_cpus": os.cpu_count(),
        "postgres": version[0],
        "postgis": version[1],
        "db_checked_at": version[2].isoformat(),
        "db_settings": settings,
        "default_settings_sha256": Settings().sha256,
        "enrichment_engine": "enrichment-1",
        "migration": "0006",
        "pool": {"connections": 2, "overflow": 0, "wait_seconds": 2},
        "duration_clock": "perf_counter monotonic seconds",
        "limits_record": "See docs/EVALUATION_REPORT.md for inspected container/VM limits",
    }


def backpressure(pipeline: Pipeline, at: datetime) -> dict[str, Any]:
    row = source(load_corpus().cases[0], 990001, at)
    with patch("netatlas.storage.blobs.require_capacity", side_effect=OSError("injected reserve")):
        try:
            pipeline.ingest(canonical(row), synthetic=True)
        except OSError:
            pass
        else:
            raise ValueError("injected reserve failed to reject")
    with pipeline.engine.connect() as conn:
        counts: list[int] = [
            conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
            for table in ("observations", "outbox", "evidence_refs")
        ]
    if counts != [0, 0, 0]:
        raise ValueError("failed source partially committed")
    status = pipeline.ingest(canonical(row), synthetic=True)
    replay = pipeline.ingest(canonical(row), synthetic=True)
    if status != "inserted" or replay != "replayed":
        raise ValueError("recovery/replay oracle mismatch")
    return {
        "fault": "injected_blob_reserve_denial",
        "rejected": 1,
        "acknowledged_during_fault": 0,
        "rows_outbox_refs_during_fault": counts,
        "recovery": status,
        "delivery_only_replay": replay,
        "physical_disk_exhaustion_tested": False,
    }


def run(at: datetime, repetitions: int, samples: int, measure: bool) -> dict[str, Any]:
    if at.tzinfo is None or not 1 <= repetitions <= 3 or not 2 <= samples <= 10:
        raise ValueError("bounded experiment and aware clock required")
    if not datetime.now(UTC) - timedelta(days=20) < at <= datetime.now(UTC):
        raise ValueError("recent evaluation clock required")
    admin = local_engine(Path("data/storage"))
    try:
        info = provenance(admin)
        if (
            not datetime.fromisoformat(info["db_checked_at"]) - timedelta(days=20)
            < at
            <= datetime.fromisoformat(info["db_checked_at"])
        ):
            raise ValueError("evaluation clock outside database window")
        report: dict[str, Any] = {
            "schema_version": 1,
            "workload": "thesis-evaluation-1",
            "at": at.isoformat(),
            "provenance": info,
            "classification": evaluate(load_corpus(), at),
            "coverage": coverage(at),
            "repetitions": repetitions,
            "samples_per_query": samples,
        }
        with disposable(admin) as pipeline:
            report["functional"] = functional(pipeline, at)
        with disposable(admin) as pipeline:
            report["backpressure"] = backpressure(pipeline, at)
        report["performance"] = []
        for _ in range(repetitions):
            with disposable(admin) as pipeline:
                report["performance"].append(trial(pipeline, at, samples))
        report["loopback"] = {"executed": False}
        if measure:
            runs = []
            for _ in range(repetitions + 1):
                with disposable(admin) as pipeline, tempfile.TemporaryDirectory() as directory:
                    runs.append(asyncio.run(loopback.trial(pipeline, Path(directory) / "spool")))
            report["loopback"] = {
                "executed": True,
                "warmup_excluded": runs[0],
                "measured": runs[1:],
            }
        report["completed_at"] = datetime.now(UTC).isoformat()
        return report
    finally:
        admin.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--at", type=datetime.fromisoformat, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=3, choices=range(1, 4))
    parser.add_argument("--samples", type=int, default=10, choices=range(2, 11))
    parser.add_argument("--synthetic", action="store_true", required=True)
    parser.add_argument(
        "--measure", action="store_true", help="Explicitly run four-service loopback fixture"
    )
    args = parser.parse_args()
    # Refuse unsafe/existing destinations before any experiment starts.
    root = Path("data")
    if (
        root.is_symlink()
        or args.output.exists()
        or args.output.is_symlink()
        or not args.output.resolve().is_relative_to(root.resolve())
    ):
        parser.error("new output under ignored data required")
    try:
        report = run(args.at, args.repetitions, args.samples, args.measure)
        publish(args.output, json.dumps(report, ensure_ascii=True, indent=2).encode())
    except Exception:
        parser.exit(2, "evaluation failed; no completed report published\n")
    print(
        json.dumps(
            {
                "completed": True,
                "workload": report["workload"],
                "repetitions": args.repetitions,
                "loopback": args.measure,
            }
        )
    )


if __name__ == "__main__":
    main()
