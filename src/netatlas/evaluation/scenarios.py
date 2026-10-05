"""Small independent source/count and authored scheduling oracles."""

import json
from collections import Counter
from datetime import datetime, timedelta
from ipaddress import ip_address
from pathlib import Path
from typing import Any
from uuid import UUID

from netatlas.derivations.engine import canonical, digest
from netatlas.derivations.offline import load_pack
from netatlas.enrichment.models import Dataset
from netatlas.evaluation.corpus import load_corpus, source
from netatlas.inspection.models import InspectionRequest
from netatlas.read_api.cursors import ReadError
from netatlas.read_api.inspection import inspect_source
from netatlas.scheduler.models import PlanningInput
from netatlas.scheduler.planner import plan
from netatlas.search.models import Query
from netatlas.search.service import search
from netatlas.storage.enrichment import store_enrichment
from netatlas.storage.pipeline import Pipeline


def dataset(at: datetime) -> Dataset:
    data = json.loads(Path("tests/fixtures/enrichment/synthetic.json").read_bytes())
    data.update(valid_from=at - timedelta(days=10), expires_at=at + timedelta(days=10))
    return Dataset.model_validate(data)


def functional(pipeline: Pipeline, at: datetime) -> dict[str, Any]:
    cases = {c.id: c for c in load_corpus().cases}
    # ID, corpus scenario, address, seconds before evaluation cutoff.
    authored = [
        (1, "http-exact", "192.0.2.10", 200000),
        (2, "timeout", "192.0.2.10", 10),
        (3, "http-exact", "192.0.2.200", 20),
        (4, "ssh", "2001:db8::1", 20),
        (5, "unknown-bytes", "203.0.113.1", 20),
        (6, "empty-open", "198.51.100.1", 20),
        (7, "two-products", "2001:db8:1::1", 20),
    ]
    bundle = dataset(at)
    rows = [
        source(cases[name], i, at - timedelta(seconds=age), address=address)
        for i, name, address, age in authored
    ]
    for row in reversed(rows):
        pipeline.ingest(canonical(row), synthetic=True)
        pipeline.derive(row.observation_id, load_pack())
        store_enrichment(pipeline, row.observation_id, bundle, at)
    base = {"as_of": at, "dataset_sha256": digest(canonical(bundle)), "limit": 50}
    # Each oracle states exact source identities AND candidate-record count.
    oracles: list[tuple[str, dict[str, Any], list[int], int]] = [
        ("attempt", {}, [2, 3, 4, 5, 6, 7], 4),
        ("evidence", {"selection": "evidence"}, [1, 3, 4, 5, 7], 5),
        ("history", {"mode": "history"}, [1, 2, 3, 4, 5, 6, 7], 5),
        ("negative_no_fallback", {"text": "nginx"}, [3, 7], 3),
        ("old_evidence", {"selection": "evidence", "freshness": "stale"}, [1], 1),
        ("fresh_attempt", {"freshness": "fresh"}, [2, 3, 4, 5, 6, 7], 4),
        ("no_point_or_mapping", {"geography": "unknown"}, [5, 6], 0),
        ("country_association", {"country": "FJ"}, [2, 5, 7], 2),
        ("same_name_west", {"place_id": "fixture:west"}, [3, 4], 2),
        ("ipv6", {"network": "2001:db8::/32"}, [4, 7], 3),
    ]
    output = {}
    for name, changes, ids, candidates in oracles:
        result = search(pipeline.engine, Query.model_validate(base | changes))
        expected_ids = {str(UUID(int=i)) for i in ids}
        expected_endpoints = len({rows[i - 1].endpoint.key for i in ids})
        if {h["id"] for h in result["hits"]} != expected_ids or (
            result["endpoints"],
            result["observations"],
            result["candidates"],
        ) != (expected_endpoints, len(ids), candidates):
            raise ValueError("functional source/count oracle mismatch")
        output[name] = {
            "endpoints": expected_endpoints,
            "sources": len(ids),
            "candidates": candidates,
        }
    result = search(pipeline.engine, Query.model_validate(base))
    expected_facets = {
        ("category", "unknown"): (3, 3),
        ("category", "web_server"): (2, 2),
        ("category", "ssh_server"): (2, 2),
        ("asn", "64497"): (1, 1),
        ("asn", "64498"): (1, 1),
        ("asn", "64496"): (2, 2),
        ("asn", "64499"): (1, 1),
        ("asn", "unknown"): (2, 2),
        ("country", "FJ"): (3, 3),
        ("country", "US"): (2, 2),
        ("country", "unknown"): (1, 1),
        ("geography", "known"): (4, 4),
        ("geography", "unknown"): (2, 2),
    }
    actual_facets = {
        (f["kind"], f["value"]): (f["endpoints"], f["observations"])
        for f in result["facets"]
        if f["kind"] in {"category", "asn", "country", "geography"}
    }
    if actual_facets != expected_facets:
        raise ValueError("facet source/endpoint oracle mismatch")
    hits = result["hits"]
    points = [h for h in hits if h["place"] and h["place"]["point"]]
    observed_geo = {
        "selected_sources": len(hits),
        "with_points": len(points),
        "without_points": len(hits) - len(points),
        "missing_radius_among_points": sum(h["city"]["accuracy_radius_km"] is None for h in points),
        "ipv4_points": [
            sum(ip_address(h["address"]).version == 4 for h in group) for group in (points, hits)
        ],
        "ipv6_points": [
            sum(ip_address(h["address"]).version == 6 for h in group) for group in (points, hits)
        ],
        "country_associations": dict(
            Counter(h["place"]["country_code"] if h["place"] else "unknown" for h in hits)
        ),
    }
    if observed_geo != {
        "selected_sources": 6,
        "with_points": 4,
        "without_points": 2,
        "missing_radius_among_points": 3,
        "ipv4_points": [2, 4],
        "ipv6_points": [2, 2],
        "country_associations": {"FJ": 3, "US": 2, "unknown": 1},
    }:
        raise ValueError("geographic availability oracle mismatch")
    ages = {}
    for selection, expected_ages in (
        ("attempt", [10, 20, 20, 20, 20, 20]),
        ("evidence", [20, 20, 20, 20, 200000]),
    ):
        selected = search(pipeline.engine, Query.model_validate(base | {"selection": selection}))
        actual_ages = sorted(
            (at - datetime.fromisoformat(h["finished_at"])).total_seconds()
            for h in selected["hits"]
        )
        if actual_ages != expected_ages:
            raise ValueError("freshness age oracle mismatch")
        ages[selection] = actual_ages
    hit = next(h for h in result["hits"] if h["id"] == str(UUID(int=7)))
    body = InspectionRequest.model_validate(
        {
            "schema_version": 1,
            "query": {
                "observation_id": hit["id"],
                "source_sha256": hit["source_sha256"],
                "derivation_id": hit["derivation_id"],
            },
        }
    )
    inspection = inspect_source(pipeline, rows[6].endpoint, body)
    if (
        inspection.trace_integrity != "checked"
        or inspection.derivation is None
        or len(inspection.derivation.candidates) != 2
    ):
        raise ValueError("source-bound ambiguity oracle mismatch")
    try:
        inspect_source(pipeline, rows[0].endpoint, body)
    except ReadError as error:
        if error.status != 404:
            raise
    else:
        raise ValueError("wrong source binding admitted")
    states = {}
    for name, update in (
        ("stale", {"expires_at": at - timedelta(seconds=5)}),
        ("not_yet_valid", {"valid_from": at + timedelta(days=1)}),
    ):
        changed = Dataset.model_validate(bundle.model_dump() | update)
        for row in rows:
            store_enrichment(pipeline, row.observation_id, changed, at - timedelta(seconds=6))
        q = Query(as_of=at, dataset_sha256=digest(canonical(changed)))
        found = search(pipeline.engine, q)
        if any(
            h["geography_state"] != name or h["place"] is not None or h["network"] is not None
            for h in found["hits"]
        ):
            raise ValueError("dataset validity oracle mismatch")
        states[name] = found["observations"]
    # Approximate location availability is not geographic accuracy.
    return {
        "queries": output,
        "dataset_states": states,
        "inspection_candidates": 2,
        "dataset_sha256": digest(canonical(bundle)),
        "source_sha256": [digest(canonical(row)) for row in rows],
        "age_seconds": ages,
        "geography": observed_geo,
    }


def coverage(at: datetime) -> dict[str, Any]:
    regions = [
        ("192.0.2.0/29", "routed"),
        ("198.51.100.0/30", "routed"),
        ("203.0.113.0/31", "unrouted"),
        ("203.0.113.4/30", "unknown"),
        ("2001:db8:1::/48", "routed"),
        ("2001:db8:2::/48", "routed"),
        ("2001:db8:3::/48", "unknown"),
    ]
    seeds = ["2001:db8:1::1", "2001:db8:1::2", "2001:db8:3::1"]
    document = {"regions": regions, "seeds": seeds}
    content_hash = digest(json.dumps(document, sort_keys=True).encode())
    request = PlanningInput.model_validate(
        {
            "schema_version": 1,
            "at": at,
            "universe": {
                "id": "thesis-authored-regions",
                "version": "1",
                "valid_from": at - timedelta(days=1),
                "expires_at": at + timedelta(days=1),
                "origins": [
                    {
                        "id": "fixture",
                        "version": "1",
                        "content_sha256": content_hash,
                        "attribution": "Authored scenario; no live routing",
                        "license": "repository terms",
                    }
                ],
                "regions": [{"network": n, "state": s, "origin_id": "fixture"} for n, s in regions],
                "seeds": [{"address": a, "origin_id": "fixture"} for a in seeds],
                "ports": [49152],
            },
        }
    )
    baseline = plan(request)
    expected = {
        "candidate_endpoints": 14,
        "ipv4_routed_addresses": 12,
        "ipv4_unrouted_addresses": 2,
        "ipv4_unknown_addresses": 4,
        "ipv6_routed_seeds": 2,
        "ipv6_nonrouted_seeds": 1,
        "ipv6_seedless_routed_regions": 1,
        "scheduled": 14,
    }
    if any(baseline.counts[k] != v for k, v in expected.items()):
        raise ValueError("authored universe denominator mismatch")
    trials = []
    for seed in (7, 8, 9):
        r = PlanningInput.model_validate(
            request.model_dump()
            | {
                "policy": {"seed": seed, "shards": 3, "sample_per_prefix": 3, "queue_size": 7},
            }
        )
        p = plan(r)
        if (p.counts["sampled_out"], p.counts["queue_deferred"], p.counts["scheduled"]) != (
            6,
            1,
            7,
        ):
            raise ValueError("sampling denominator mismatch")
        if Counter(e.prefix for e in p.entries[:6]) != {
            "192.0.2.0/24": 2,
            "198.51.100.0/24": 2,
            "2001:db8:1::/48": 2,
        }:
            raise ValueError("dispatch prefix fairness mismatch")
        trials.append(
            {
                "seed": seed,
                "input_sha256": digest(canonical(r)),
                "plan_sha256": digest(canonical(p)),
                "counts": p.counts,
                "selected": [str(e.endpoint.address) for e in p.entries],
                "shards": [sum(e.shard == i for e in p.entries) for i in range(3)],
            }
        )
    # Exact cooldown boundary on latest timeout, with an older open attempt retained.
    history = [
        {
            "endpoint": {"address": "192.0.2.1", "port": 49152},
            "observation_id": UUID(int=i),
            "source_sha256": str(i) * 64,
            "started_at": at - timedelta(days=days, seconds=1),
            "finished_at": at - timedelta(days=days),
            "outcome": outcome,
        }
        for i, days, outcome in ((1, 3, "open"), (2, 2, "timeout"))
    ]
    r = PlanningInput.model_validate(request.model_dump() | {"history": history})
    due = plan(r)
    previous = next(e.previous for e in due.entries if e.kind == "refresh")
    before = plan(PlanningInput.model_validate(r.model_dump() | {"at": at - timedelta(seconds=1)}))
    if (
        previous is None
        or previous.observation_id != UUID(int=2)
        or before.counts["fresh"] != 1
        or due.counts["refresh"] != 1
    ):
        raise ValueError("latest-negative cooldown mismatch")
    excluded = plan(
        PlanningInput.model_validate(
            request.model_dump()
            | {
                "suppressions": ["192.0.2.0/31"],
                "blocked": [{"address": "198.51.100.0", "port": 49152}],
            }
        )
    )
    if (excluded.counts["excluded"], excluded.counts["blocked"], excluded.counts["scheduled"]) != (
        2,
        1,
        11,
    ):
        raise ValueError("exclusion denominator mismatch")
    return {
        "input_sha256": digest(canonical(request)),
        "universe_sha256": digest(canonical(request.universe)),
        "policy_sha256": digest(canonical(request.policy)),
        "settings_sha256": request.settings.sha256,
        "seeds_sha256": baseline.seeds_sha256,
        "connection_policy_sha256": baseline.connection_policy_sha256,
        "baseline": baseline.counts,
        "exclusions": excluded.counts,
        "trials": trials,
        "refresh_boundary": {"before_fresh": 1, "at_due_refresh": 1, "latest_outcome": "timeout"},
    }
