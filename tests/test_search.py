"""Authored truth for local PostgreSQL search; no measurement or external datasets."""

import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, create_engine, text
from test_storage import observation

from netatlas.derivations.engine import canonical, digest
from netatlas.derivations.models import RulePack
from netatlas.derivations.offline import load_pack
from netatlas.domain import Category
from netatlas.enrichment.models import Dataset
from netatlas.observation import Observation
from netatlas.search.cli import main, read_query
from netatlas.search.models import Box, Query, Radius
from netatlas.search.service import compile_query, search
from netatlas.storage.backup import backup, compose_command, restore
from netatlas.storage.blobs import BlobStore
from netatlas.storage.database import migrate
from netatlas.storage.enrichment import store_enrichment
from netatlas.storage.pipeline import Pipeline

pytest_plugins = ["test_storage"]


def bundle(at: datetime) -> Dataset:
    data = json.loads(Path("tests/fixtures/enrichment/synthetic.json").read_text())
    data.update(valid_from=at - timedelta(days=10), expires_at=at + timedelta(days=10))
    return Dataset.model_validate(data)


def ambiguous_pack() -> RulePack:
    core = load_pack()
    rule = core.rules[0]
    other = rule.model_copy(update={"rule_id": "fixture.router", "category": Category.ROUTER})
    return RulePack.model_validate(core.model_dump() | {"rules": (*core.rules, other)})


def ingest(p: Pipeline, row: Observation, data: Dataset, at: datetime) -> None:
    p.ingest(canonical(row), synthetic=True)
    p.derive(row.observation_id, ambiguous_pack())
    store_enrichment(p, row.observation_id, data, at)


@pytest.fixture
def truth(pipeline: Pipeline) -> tuple[Pipeline, Query, dict[str, Observation]]:
    at = datetime.now(UTC) - timedelta(seconds=1)
    data = bundle(at)
    rows = {
        "east_old": observation(identity=UUID(int=1), age=200000, address="192.0.2.10"),
        "east_new": observation(identity=UUID(int=2), age=30, address="192.0.2.10"),
        "east_negative": observation(
            identity=UUID(int=3), age=10, address="192.0.2.10", outcome="timeout"
        ),
        "west": observation(identity=UUID(int=4), age=20, address="192.0.2.200"),
        "v6": observation(identity=UUID(int=5), age=20, address="2001:db8::1"),
        "no_point": observation(identity=UUID(int=6), age=20, address="203.0.113.1", body=b"?"),
        "no_mapping": observation(identity=UUID(int=7), age=20, address="198.51.100.1", body=None),
    }
    for row in reversed(tuple(rows.values())):
        ingest(pipeline, row, data, at)
    query = Query(
        dataset_sha256=digest(canonical(data)), pack_sha256=digest(canonical(ambiguous_pack()))
    )
    return pipeline, query, rows


def run(truth: tuple[Pipeline, Query, dict[str, Observation]], **changes: Any) -> dict[str, Any]:
    p, q, _ = truth
    return search(p.engine, Query.model_validate(q.model_dump() | changes))


def ids(result: dict[str, Any]) -> set[str]:
    return {row["id"] for row in result["hits"]}


def test_counts_facets_and_ambiguity(truth: tuple[Pipeline, Query, dict[str, Observation]]) -> None:
    current = run(truth)
    assert (current["endpoints"], current["observations"], current["candidates"]) == (5, 5, 4)
    evidence = run(truth, selection="evidence")
    assert (evidence["endpoints"], evidence["observations"], evidence["candidates"]) == (4, 4, 6)
    history = run(truth, mode="history")
    assert (history["endpoints"], history["observations"], history["candidates"]) == (5, 7, 8)
    facets = {
        (x["kind"], x["value"]): (x["endpoints"], x["observations"]) for x in history["facets"]
    }
    assert facets["category", "web_server"] == (3, 4)
    assert facets["category", "router"] == (3, 4)
    assert facets["category", "unknown"] == (3, 3)
    assert facets["asn", "64497"] == (1, 3)
    assert facets["asn", "64498"] == (1, 3)
    assert facets["asn", "unknown"] == (2, 2)
    assert facets["geography", "unknown"] == (2, 2)
    assert run(truth, category="web_server")["endpoints"] == 2
    assert run(truth, category="unknown")["endpoints"] == 3
    assert run(truth, selection="evidence", category="router")["endpoints"] == 3
    # Counts and facets cover the full matched set, not the result page.
    page = run(truth, mode="history", limit=1, facet_limit=1)
    assert page["observations"] == 7 and len(page["hits"]) == 1
    assert all(item["rank"] == 1 for item in page["facets"])
    assert any(item["total_buckets"] > 1 for item in page["facets"])
    assert run(truth, limit=1, offset=100)["hits"] == []


def test_filters_selection_order_and_freshness(
    truth: tuple[Pipeline, Query, dict[str, Observation]],
) -> None:
    _, _, rows = truth
    assert run(truth, text="nginx")["endpoints"] == 2
    assert run(truth, text="NGINX", selection="evidence")["endpoints"] == 3
    assert run(truth, text="nginx OR nothing")["endpoints"] == 0  # plain AND terms
    assert run(truth, text="'); DROP TABLE observations; --")["endpoints"] == 0
    assert run(truth, network="2001:db8::/32")["endpoints"] == 1
    assert run(truth, network="192.0.2.0/25", outcome="open")["endpoints"] == 0
    assert run(truth, network="192.0.2.0/25", selection="open")["endpoints"] == 1
    assert run(truth, port=1)["endpoints"] == 0
    assert run(truth, transport="udp")["endpoints"] == 0
    assert run(truth, has_evidence=False)["endpoints"] == 2
    assert ids(run(truth, mode="history", freshness="stale")) == {
        str(rows["east_old"].observation_id)
    }
    assert run(truth, freshness="stale")["endpoints"] == 0
    assert run(truth, mode="history", freshness="fresh")["observations"] == 6
    cutoff = rows["east_new"].finished_at
    assert run(truth, before=cutoff)["endpoints"] == 0  # no fallback after filtering
    past = run(truth, as_of=cutoff)
    assert ids(past) == {str(rows["east_new"].observation_id)}
    assert run(truth, mode="history", after=cutoff)["observations"] == 6
    assert run(truth, pack_sha256="0" * 64)["candidates"] == 0
    assert run(truth, dataset_sha256=None)["facets"]


def test_geography_and_network_truth(truth: tuple[Pipeline, Query, dict[str, Observation]]) -> None:
    assert run(truth, asn=64498)["endpoints"] == 1
    assert run(truth, country="FJ")["endpoints"] == 2  # includes known place without point
    assert run(truth, geography="known")["endpoints"] == 3
    assert run(truth, geography="unknown")["endpoints"] == 2
    assert run(truth, place_id="fixture:east")["endpoints"] == 1
    assert run(truth, place_id="fixture:west")["endpoints"] == 2  # same name, distinct ID
    assert run(truth, radius=Radius(longitude=180, latitude=-17.5, metres=60000))["endpoints"] == 3
    assert run(truth, radius=Radius(longitude=180, latitude=-17.5, metres=50000))["endpoints"] == 0
    assert run(truth, box=Box(west=170, south=-20, east=-170, north=-10))["endpoints"] == 3
    assert run(truth, box=Box(west=-10, south=-20, east=10, north=-10))["endpoints"] == 0
    assert run(truth, boundary_place_id="fixture:east")["endpoints"] == 3
    assert run(truth, boundary_place_id="fixture:west")["endpoints"] == 0
    result = run(truth)
    assert result["dataset"]["origins"][0]["attribution"].startswith("NetAtlas")
    assert "places" not in result["dataset"] and "rules" not in result["pack"]
    hits = result["hits"]
    west = next(h for h in hits if h["address"] == "192.0.2.200")
    assert west["city"]["accuracy_radius_km"] == 250
    east = next(h for h in hits if h["address"] == "192.0.2.10")
    assert east["city"]["accuracy_radius_km"] is None
    assert "boundary" not in east["place"]


def test_dataset_expiry_latest_evaluation_and_version_choice(pipeline: Pipeline) -> None:
    now = datetime.now(UTC)
    data = bundle(now)
    stale = Dataset.model_validate(data.model_dump() | {"expires_at": now - timedelta(seconds=5)})
    row = observation(age=100)
    ingest(pipeline, row, stale, now - timedelta(seconds=10))
    q = Query(dataset_sha256=digest(canonical(stale)))
    result = search(pipeline.engine, q)
    assert result["hits"][0]["geography_state"] == "stale"
    assert result["hits"][0]["network"] is None and result["hits"][0]["place"] is None
    assert (
        search(pipeline.engine, Query.model_validate(q.model_dump() | {"asn": 64497}))["endpoints"]
        == 0
    )
    historical = Query.model_validate(q.model_dump() | {"as_of": now - timedelta(seconds=7)})
    assert search(pipeline.engine, historical)["hits"][0]["geography_state"] == "known"
    # A later evaluation of the same expired dataset cannot revive old geography.
    store_enrichment(pipeline, row.observation_id, stale, now)
    assert search(pipeline.engine, q)["hits"][0]["geography_state"] == "stale"
    store_enrichment(pipeline, row.observation_id, data, now)
    assert search(pipeline.engine, q)["hits"][0]["geography_state"] == "stale"
    fresh = Query(dataset_sha256=digest(canonical(data)))
    assert search(pipeline.engine, fresh)["hits"][0]["geography_state"] == "known"
    future = Dataset.model_validate(data.model_dump() | {"valid_from": now + timedelta(days=1)})
    store_enrichment(pipeline, row.observation_id, future, now)
    assert (
        search(pipeline.engine, Query(dataset_sha256=digest(canonical(future))))["hits"][0][
            "geography_state"
        ]
        == "not_yet_valid"
    )


def test_removal_expiry_replay_and_query_without_blob_reads(
    truth: tuple[Pipeline, Query, dict[str, Observation]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    p, q, rows = truth
    before = run(truth, mode="history")
    p.consume(replay=True)
    assert run(truth, mode="history")["hits"] == before["hits"]
    p.maintain(suppress="192.0.2.0/24")
    p.consume(replay=True)
    assert run(truth, mode="history")["observations"] == 3
    with pytest.raises(ValueError):
        p.ingest(canonical(rows["east_new"]), synthetic=True)

    def no_blob_reads(*args: Any, **kwargs: Any) -> bytes:
        raise AssertionError("search must not read raw evidence")

    monkeypatch.setattr(BlobStore, "read", no_blob_reads)
    assert run(truth)["endpoints"] == 3

    # Clock advance excludes sources even without physical maintenance, for both modes.
    class Later:
        @classmethod
        def now(cls, tz: Any = None) -> datetime:
            return datetime.now(UTC) + timedelta(days=31)

    monkeypatch.setattr("netatlas.search.service.datetime", Later)
    assert search(p.engine, q)["observations"] == 0
    assert search(p.engine, Query(mode="history", as_of=datetime.now(UTC)))["observations"] == 0


@pytest.mark.parametrize(
    "values",
    [
        {"limit": 201},
        {"offset": 10001},
        {"facet_limit": 51},
        {"fresh_seconds": 0},
        {"network": "example.org"},
        {"network": "192.0.2.1/24"},
        {"network": "fe80::1%lo0"},
        {"text": "\x1b[31m"},
        {"text": " "},
        {"text": "x" * 257},
        {"asn": 64496},
        {"radius": {"longitude": 0, "latitude": 0, "metres": 0}},
        {"unknown": True},
        {"box": {"west": 0, "south": 1, "east": 0, "north": 1}},
        {"as_of": "2026-01-01"},
    ],
)
def test_query_bounds(values: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        Query.model_validate(values)


def test_query_file_boundary(tmp_path: Path) -> None:
    path = tmp_path / "query.json"
    for raw in (b"{}", b'{"schema_version":1,"limit":1,"limit":2}', b"x" * 16385):
        path.write_bytes(raw)
        with pytest.raises(ValueError):
            read_query(path)
    path.write_text('{"schema_version":1,"limit":2}')
    assert read_query(path).limit == 2
    link = tmp_path / "link"
    link.symlink_to(path)
    with pytest.raises(OSError):
        read_query(link)
    with pytest.raises(ValueError):
        compile_query(Query(as_of=datetime.now(UTC) + timedelta(days=1)), datetime.now(UTC))


def test_private_cli(
    truth: tuple[Pipeline, Query, dict[str, Observation]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    p, q, _ = truth
    query = tmp_path / "query.json"
    query.write_text(q.model_dump_json())
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("netatlas.search.cli.local_engine", lambda _: p.engine)
    monkeypatch.setattr(
        "sys.argv", ["netatlas-search", "--query", str(query), "--output", "data/result.json"]
    )
    main()
    output = tmp_path / "data/result.json"
    assert output.stat().st_mode & 0o777 == 0o600
    assert json.loads(output.read_text())["endpoints"] == 5
    assert json.loads(capsys.readouterr().out) == {
        "endpoints": 5,
        "observations": 5,
        "candidates": 4,
    }
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    assert "192.0.2" not in capsys.readouterr().err


@pytest.mark.parametrize("revision", ["0003", "head"])
def test_search_upgrade_and_restore(empty_engine: Engine, tmp_path: Path, revision: str) -> None:
    migrate(empty_engine, revision)
    p = Pipeline(empty_engine, BlobStore(tmp_path / "original"))
    now = datetime.now(UTC)
    row = observation()
    data = bundle(now)
    ingest(p, row, data, now)
    saved = tmp_path / "archive"
    backup(empty_engine, p.blobs, saved)
    name = "netatlas_restore_" + uuid4().hex
    subprocess.run([*compose_command(), "createdb", "-U", "postgres", name], check=True)
    target = create_engine(empty_engine.url.set(database=name), hide_parameters=True)
    try:
        restore(target, BlobStore(tmp_path / "restored"), saved)
        migrate(empty_engine)
        query = Query(
            dataset_sha256=digest(canonical(data)), pack_sha256=digest(canonical(ambiguous_pack()))
        )
        a, b = search(empty_engine, query), search(target, query)
        assert a["hits"] == b["hits"] and a["facets"] == b["facets"]
        assert b["candidates"] == 2
        with target.connect() as conn:
            assert (
                conn.execute(
                    text("SELECT count(*) FROM pg_indexes WHERE indexname LIKE 'search_%'")
                ).scalar_one()
                == 9
            )
    finally:
        target.dispose()
        subprocess.run([*compose_command(), "dropdb", "-U", "postgres", name], check=True)


def test_deterministic_ties_and_reindex(pipeline: Pipeline) -> None:
    row = observation(identity=UUID(int=10))
    other = Observation.model_validate(row.model_dump() | {"observation_id": UUID(int=11)})
    for item in (other, row):
        pipeline.ingest(canonical(item), synthetic=True)
    current = search(pipeline.engine, Query())
    assert ids(current) == {str(other.observation_id)}
    first = search(pipeline.engine, Query(mode="history", limit=1))
    second = search(pipeline.engine, Query(mode="history", limit=1, offset=1))
    assert ids(first) == {str(other.observation_id)} and ids(second) == {str(row.observation_id)}
    with pipeline.engine.begin() as connection:
        for table in ("observations", "derivations", "enrichments"):
            connection.execute(text(f"REINDEX TABLE {table}"))
    assert search(pipeline.engine, Query())["hits"] == current["hits"]


def test_search_index_paths(truth: tuple[Pipeline, Query, dict[str, Observation]]) -> None:
    from netatlas.search.benchmark import index_names
    from netatlas.search.service import TEXT_VECTOR

    p, _, _ = truth
    cases = [
        ("SELECT id FROM observations WHERE address <<= '192.0.2.10'::inet", "search_address"),
        ("SELECT id FROM observations WHERE port=80", "search_port_time"),
        (
            f"SELECT id FROM derivations d WHERE {TEXT_VECTOR} "
            "@@ plainto_tsquery('simple','nginx')",
            "search_product_text",
        ),
        (
            """SELECT id FROM derivations
            WHERE document @> '{"candidates":[{"category":"router"}]}'::jsonb""",
            "search_fingerprint",
        ),
        (
            """SELECT id FROM enrichments
            WHERE document @> '{"network":{"asns":[64497]}}'::jsonb""",
            "search_enrichment_fields",
        ),
        (
            """SELECT id FROM enrichments WHERE ST_DWithin(point,
            ST_SetSRID(ST_MakePoint(179.5,-17.5),4326)::geography,1000)""",
            "search_enrichment_point",
        ),
        (
            """SELECT id FROM enrichments WHERE ST_Covers(
            ST_MakeEnvelope(179,-18,180,-17,4326),point::geometry)""",
            "search_enrichment_geometry",
        ),
    ]
    with p.engine.begin() as connection:
        # Prove predicate/index compatibility independently of join-cost choices.
        # The benchmark records actual complete unforced query plans.
        connection.execute(text("SET LOCAL enable_seqscan=off"))
        for sql, expected in cases:
            plan: Any = connection.execute(text("EXPLAIN (FORMAT JSON) " + sql)).scalar_one()
            assert expected in index_names(plan), (expected, index_names(plan))


def test_read_time_suppression_even_before_cleanup(pipeline: Pipeline) -> None:
    row = observation()
    pipeline.ingest(canonical(row), synthetic=True)
    with pipeline.engine.begin() as connection:
        connection.execute(text("INSERT INTO suppressions (network) VALUES ('192.0.2.0/24')"))
    assert search(pipeline.engine, Query())["observations"] == 0
    assert search(pipeline.engine, Query(mode="history"))["observations"] == 0


def test_geographic_holes_and_area_edges(pipeline: Pipeline) -> None:
    at = datetime.now(UTC)
    data = bundle(at).model_dump(mode="json")
    # A hole in the eastern component removes its representative point only.
    data["places"][0]["boundary"]["coordinates"][0].append(
        [[179, -18], [179, -17], [179.9, -17], [179.9, -18], [179, -18]]
    )
    selected = Dataset.model_validate(data)
    for address in ("192.0.2.10", "192.0.2.200", "2001:db8::1"):
        ingest(pipeline, observation(address=address), selected, at)
    q = Query(dataset_sha256=digest(canonical(selected)), boundary_place_id="fixture:east")
    assert search(pipeline.engine, q)["endpoints"] == 2
    world = Query(
        dataset_sha256=q.dataset_sha256, box=Box(west=-180, south=-90, east=180, north=90)
    )
    assert search(pipeline.engine, world)["endpoints"] == 3
    edge = Query(
        dataset_sha256=q.dataset_sha256, box=Box(west=179.5, south=-17.5, east=180, north=0)
    )
    assert search(pipeline.engine, edge)["endpoints"] == 1
