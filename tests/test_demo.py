"""The packaged offline demo is small, synthetic and uses the actual read pipeline."""

import json
from datetime import UTC, datetime
from pathlib import Path

from netatlas.demo import demo_dataset, seed
from netatlas.derivations.engine import canonical, digest
from netatlas.enrichment.engine import places_named
from netatlas.inspection.models import InspectionRequest
from netatlas.read_api.inspection import inspect_source
from netatlas.search.models import Query
from netatlas.search.service import search
from netatlas.storage.pipeline import Pipeline

pytest_plugins = ["test_storage"]


def test_packaged_geography_and_authored_disambiguation() -> None:
    at = datetime(2026, 10, 4, tzinfo=UTC)
    data = demo_dataset(at)
    assert canonical(data) == canonical(demo_dataset(at))
    assert len(places_named(data, "Example Harbor")) == 2
    country = next(p for p in data.places if p.kind == "country")
    assert country.boundary is not None
    asset = json.loads(Path("web/src/assets/fiji.json").read_text())
    assert asset["features"][0]["geometry"] == country.boundary.model_dump(mode="json")
    assert data.origins[0].license == "Public domain"
    assert all(p.origin == "synthetic" for p in data.places if p.id.startswith("demo:"))
    assert digest(canonical(data)) != digest(canonical(demo_dataset(at.replace(day=5))))


def test_demo_through_real_search_and_removal(pipeline: Pipeline) -> None:
    at = datetime.now(UTC)
    sha = seed(pipeline, at)
    q = Query(dataset_sha256=sha)
    result = search(pipeline.engine, q)
    assert result["endpoints"] == 12 and result["observations"] == 12
    assert len([h for h in result["hits"] if h["geography_state"] == "known"]) == 11
    assert search(pipeline.engine, Query(dataset_sha256=sha, mode="history"))["observations"] == 13
    assert search(pipeline.engine, Query(dataset_sha256=sha, text="nginx"))["endpoints"] == 6
    assert (
        search(pipeline.engine, Query(dataset_sha256=sha, text="nginx", selection="evidence"))[
            "endpoints"
        ]
        == 7
    )
    pipeline.maintain(suppress="192.0.2.0/24")
    assert search(pipeline.engine, q)["endpoints"] == 2
    assert pipeline.verify()["observations"] == 2


def test_thesis_profile_preserves_unknowns_stale_history_and_exact_ambiguity(
    pipeline: Pipeline,
) -> None:
    at = datetime.now(UTC)
    sha = seed(pipeline, at, thesis=True)
    result = search(pipeline.engine, Query(dataset_sha256=sha))
    assert (result["endpoints"], result["observations"], result["candidates"]) == (15, 15, 13)
    assert sum(h["geography_state"] == "known" for h in result["hits"]) == 11
    assert search(pipeline.engine, Query(mode="history"))["observations"] == 16
    stale = search(pipeline.engine, Query(freshness="stale"))["hits"]
    assert len(stale) == 1 and stale[0]["address"] == "203.0.113.14"
    assert search(pipeline.engine, Query(outcome="closed"))["endpoints"] == 1
    assert search(pipeline.engine, Query(text="nginx"))["endpoints"] == 8
    assert search(pipeline.engine, Query(text="nginx", selection="evidence"))["endpoints"] == 9
    hit = next(h for h in result["hits"] if h["address"] == "203.0.113.15")
    source = pipeline.load(hit["id"])
    request = InspectionRequest.model_validate(
        {
            "schema_version": 1,
            "query": {
                "observation_id": hit["id"],
                "source_sha256": hit["source_sha256"],
                "derivation_id": hit["derivation_id"],
            },
        }
    )
    inspection = inspect_source(pipeline, source.endpoint, request)
    assert inspection.trace_integrity == "checked"
    assert inspection.derivation is not None
    assert len(inspection.derivation.candidates) == 2
    assert pipeline.load(hit["id"]) == source
    assert pipeline.verify() == {"observations": 16, "derivations": 16, "enrichments": 16}
