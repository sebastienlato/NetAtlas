"""Disposable synthetic workload. Run from repository root; no target connections."""

import argparse
import base64
import json
import math
import platform
import statistics
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Engine, create_engine, text

from netatlas.config import Settings
from netatlas.derivations.engine import canonical, digest
from netatlas.derivations.models import RulePack
from netatlas.derivations.offline import load_pack
from netatlas.enrichment.models import Dataset
from netatlas.enrichment.offline import publish
from netatlas.examples import example_observation
from netatlas.observation import Observation
from netatlas.search.models import Box, Query, Radius
from netatlas.search.service import compile_query, search
from netatlas.storage.blobs import BlobStore
from netatlas.storage.database import local_engine, migrate, transaction
from netatlas.storage.enrichment import store_enrichment
from netatlas.storage.pipeline import Pipeline


def seed(pipeline: Pipeline, count: int, at: datetime) -> Query:
    """Three attempts/endpoint, half IPv6; fixed identities/order and source contents."""
    data = json.loads(Path("tests/fixtures/enrichment/synthetic.json").read_text())
    data.update(valid_from=at - timedelta(days=10), expires_at=at + timedelta(days=10))
    dataset = Dataset.model_validate(data)
    pack = load_pack()
    rare = pack.rules[0].model_dump() | {
        "rule_id": "synthetic.benchmark",
        "product": "NetAtlasBenchRare",
        "conditions": [
            {"selector": "http.server", "operator": "equals", "value": "NetAtlasBenchRare"}
        ],
        "provenance": "Authored benchmark fixture; no real product assertion",
    }
    pack = RulePack.model_validate(pack.model_dump() | {"rules": [*pack.rules, rare]})
    template = example_observation(Settings()).model_dump(mode="json")
    for i in range(count):
        address = f"192.0.2.{(i // 2) % 256}" if i % 2 == 0 else f"2001:db8::{i:x}"
        for attempt in range(3):
            row = json.loads(json.dumps(template))
            row["observation_id"] = str(UUID(int=1 + i * 3 + attempt))
            row["target"]["address"] = row["endpoint"]["address"] = address
            row["endpoint"]["port"] = 8000 + i // 512
            row["started_at"] = at - timedelta(days=2 - attempt, seconds=2)
            row["finished_at"] = at - timedelta(days=2 - attempt, seconds=1)
            server = "NetAtlasBenchRare" if i % 100 == 0 else "nginx"
            row["response"] = {
                "body_base64": base64.b64encode(
                    f"HTTP/1.1 200 OK\r\nServer: {server}\r\n\r\nfixture".encode()
                ).decode()
            }
            if attempt == 2 and i % 4 == 0:
                row.update(outcome="timeout", response=None, service=None)
            source = Observation.model_validate(row)
            pipeline.ingest(canonical(source), synthetic=True)
            pipeline.derive(source.observation_id, pack)
            store_enrichment(pipeline, source.observation_id, dataset, at)
    return Query(
        pack_sha256=digest(canonical(pack)),
        dataset_sha256=digest(canonical(dataset)),
        as_of=at,
        selection="evidence",
    )


def index_names(node: Any) -> set[str]:
    names: set[str] = set()
    if isinstance(node, dict):
        if "Index Name" in node:
            names.add(node["Index Name"])
        for value in node.values():
            names.update(index_names(value))
    elif isinstance(node, list):
        for value in node:
            names.update(index_names(value))
    return names


def measure(engine: Engine, query: Query, count: int, samples: int) -> dict[str, Any]:
    cases: dict[str, dict[str, Any]] = {
        "all_current": {},
        "all_history": {"mode": "history"},
        "network": {"network": "192.0.2.0/28"},
        "port": {"port": 8000},
        "text_rare": {"text": "NetAtlasBenchRare"},
        "category": {"category": "web_server"},
        "asn": {"asn": 64497},
        "radius": {"radius": Radius(longitude=179.5, latitude=-17.5, metres=1000)},
        "dateline_box": {"box": Box(west=170, south=-20, east=-170, north=-10)},
        "fresh": {"freshness": "fresh"},
    }
    measurements: dict[str, Any] = {}
    for name, changes in cases.items():
        selected = Query.model_validate(query.model_dump() | changes)
        first = search(engine, selected)  # warm-up and count oracle
        if name in ("all_current", "category", "dateline_box"):
            assert first["endpoints"] == count
        if name == "all_history":
            assert first["observations"] == 3 * count - (count + 3) // 4
        if name == "text_rare":
            assert first["endpoints"] == (count + 99) // 100
        timings = []
        for _ in range(samples):
            start = perf_counter()
            result = search(engine, selected)
            timings.append((perf_counter() - start) * 1000)
            assert result["hits"] == first["hits"] and result["facets"] == first["facets"]
        with transaction(engine) as connection:
            sql, params = compile_query(selected, datetime.now(UTC))
            plan: Any = connection.execute(
                text("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql), params
            ).scalar_one()
        measurements[name] = {
            "p50_ms": round(statistics.median(timings), 3),
            "p95_ms": round(sorted(timings)[math.ceil(samples * 0.95) - 1], 3),
            "endpoints": first["endpoints"],
            "observations": first["observations"],
            "indexes_used": sorted(index_names(plan)),
            "plan": plan,
        }
    with engine.connect() as connection:
        indexes = [
            dict(row)
            for row in connection.execute(
                text("""
            SELECT indexrelname AS name,pg_relation_size(indexrelid) AS bytes
            FROM pg_stat_user_indexes ORDER BY indexrelname
        """)
            ).mappings()
        ]
        version = connection.execute(text("SELECT version(),postgis_full_version()")).one()
    return {
        "workload": "synthetic-search-1",
        "endpoints": count,
        "observations": count * 3,
        "samples": samples,
        "query": query.model_dump(mode="json"),
        "host": platform.platform(),
        "python": platform.python_version(),
        "postgres": version[0],
        "postgis": version[1],
        "measurements": measurements,
        "indexes": indexes,
        "search_index_bytes": sum(x["bytes"] for x in indexes if x["name"].startswith("search_")),
        "all_index_bytes": sum(x["bytes"] for x in indexes),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoints", type=int, default=2048)
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument("--at", type=datetime.fromisoformat, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.endpoints <= 4096 or not 1 <= args.samples <= 50:
        parser.error("bounded workload required")
    if args.at.tzinfo is None or not datetime.now(UTC) - timedelta(
        days=20
    ) < args.at <= datetime.now(UTC):
        parser.error("recent aware evaluation clock required")
    admin = local_engine(Path("data/storage"))
    name = "netatlas_test_bench_" + uuid4().hex
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    engine = create_engine(admin.url.set(database=name), hide_parameters=True)
    try:
        migrate(engine)
        with tempfile.TemporaryDirectory() as directory:
            pipeline = Pipeline(engine, BlobStore(Path(directory) / "blobs"))
            start = perf_counter()
            query = seed(pipeline, args.endpoints, args.at)
            seeded_seconds = perf_counter() - start
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
                connection.execute(text("VACUUM ANALYZE"))
            report = measure(engine, query, args.endpoints, args.samples)
            report["seed_seconds"] = round(seeded_seconds, 3)
            publish(args.output, json.dumps(report, ensure_ascii=True, indent=2).encode())
            print(
                json.dumps(
                    {
                        "completed": True,
                        "endpoints": args.endpoints,
                        "search_index_bytes": report["search_index_bytes"],
                    }
                )
            )
    finally:
        engine.dispose()
        with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        admin.dispose()


if __name__ == "__main__":
    main()
