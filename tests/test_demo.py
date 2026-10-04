"""The packaged offline demo is small, synthetic and uses the actual read pipeline."""

import json
from datetime import UTC, datetime
from pathlib import Path

from netatlas.demo import demo_dataset, seed
from netatlas.derivations.engine import canonical, digest
from netatlas.enrichment.engine import places_named
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
