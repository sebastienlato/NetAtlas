"""Complete bounded operations; independent algebra for the fixed Phase 6 workload."""

import json
import math
import statistics
from datetime import datetime
from time import perf_counter
from typing import Any
from uuid import UUID

from sqlalchemy import text

from netatlas.search.benchmark import seed
from netatlas.search.models import Box, Query, Radius
from netatlas.search.service import search
from netatlas.storage.pipeline import Pipeline


def distribution(values: list[float]) -> dict[str, Any]:
    if not values:
        raise ValueError("nonempty timings required")
    return {
        "samples": values,
        "n": len(values),
        "median": statistics.median(values),
        "p95_nearest_rank": sorted(values)[math.ceil(0.95 * len(values)) - 1],
        "min": min(values),
        "max": max(values),
    }


def footprint(pipeline: Pipeline) -> dict[str, int]:
    with pipeline.engine.connect() as conn:
        sizes = conn.execute(
            text("""
            SELECT coalesce(sum(pg_total_relation_size(c.oid)),0),
                   coalesce(sum(pg_indexes_size(c.oid)),0)
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND c.relkind='r' AND c.relname!='spatial_ref_sys'
        """)
        ).one()
        allocated, indexes = int(str(sizes[0])), int(str(sizes[1]))
        sources: int = conn.execute(text("SELECT count(*) FROM observations")).scalar_one()
    blobs = list(pipeline.blobs.root.iterdir())
    return {
        "relation_bytes_including_indexes": int(allocated),
        "index_bytes": int(indexes),
        "blob_logical_bytes": sum(p.stat().st_size for p in blobs),
        "blob_files": len(blobs),
        "sources": sources,
    }


def expected(name: str) -> tuple[int, int, list[str]]:
    """Independent fixture arithmetic: 128 endpoints, three ordered attempts.

    No prediction/search/derivation call is allowed in this oracle. Source IDs encode
    endpoint index and attempt. Current evidence survives each fourth latest timeout.
    """
    indices = list(range(128))
    if name == "network":
        indices = list(range(0, 32, 2))
    elif name in ("asn", "radius"):
        indices = list(range(0, 128, 2))
    elif name == "text_rare":
        indices = [0, 100]
    elif name == "fresh":
        indices = [i for i in indices if i % 4 != 0]
    elif name not in ("all_current", "all_history", "port", "category", "dateline_box"):
        raise ValueError("unknown benchmark oracle")
    selected = [
        (i, a)
        for i in indices
        for a in (range(3) if name == "all_history" else [1 if i % 4 == 0 else 2])
        if not (a == 2 and i % 4 == 0)
    ]
    selected.sort(key=lambda pair: (pair[1], pair[0]), reverse=True)
    return len(indices), len(selected), [str(UUID(int=1 + i * 3 + a)) for i, a in selected[:50]]


def trial(pipeline: Pipeline, at: datetime, samples: int) -> dict[str, Any]:
    checkpoints = [{"endpoints": 0, **footprint(pipeline)}]
    writes = []
    start_index = 0
    for count in (32, 128):
        start = perf_counter()
        query = seed(pipeline, count, at, start=start_index)
        seconds = perf_counter() - start
        added = (count - start_index) * 3
        writes.append(
            {
                "new_sources": added,
                "commits": added * 3,
                "seconds": seconds,
                "sources_per_second": added / seconds,
            }
        )
        with pipeline.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text("VACUUM ANALYZE"))
        checkpoints.append({"endpoints": count, **footprint(pipeline)})
        start_index = count
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
    reads = {}
    for name, changes in cases.items():
        q = Query.model_validate(query.model_dump() | changes)
        timings = []
        endpoints, sources, page = expected(name)
        for sample in range(samples + 1):
            start = perf_counter()
            result = search(pipeline.engine, q)
            encoded = json.dumps(result, ensure_ascii=True, separators=(",", ":")).encode()
            elapsed = (perf_counter() - start) * 1000
            if (result["endpoints"], result["observations"], result["candidates"]) != (
                endpoints,
                sources,
                sources,
            ) or [h["id"] for h in result["hits"]] != page:
                raise ValueError("benchmark source/count oracle mismatch")
            if sample:
                timings.append(elapsed)
        reads[name] = {
            "milliseconds": distribution(timings),
            "endpoints": endpoints,
            "sources": sources,
            "candidates": sources,
            "page_rows": len(page),
            "last_serialized_bytes": len(encoded),
        }
    verified = pipeline.verify()
    if verified != {"observations": 384, "derivations": 384, "enrichments": 384}:
        raise ValueError("benchmark durable population mismatch")
    with pipeline.engine.connect() as conn:
        hashes: list[str] = list(
            conn.execute(text("SELECT source_sha256 FROM observations ORDER BY id")).scalars()
        )
    from netatlas.derivations.engine import digest

    return {
        "writes": writes,
        "footprint": checkpoints,
        "reads": reads,
        "query": query.model_dump(mode="json"),
        "verified": verified,
        "population_sha256": digest("\n".join(hashes).encode()),
        "failures": 0,
        "warmups_per_query": 1,
        "clients": 1,
    }
