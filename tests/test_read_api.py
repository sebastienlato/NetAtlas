"""HTTP acceptance against authored synthetic PostgreSQL, including hostile metadata."""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from test_search import ambiguous_pack, bundle, ingest
from test_storage import observation

from netatlas.api import create_app
from netatlas.derivations.engine import canonical, digest
from netatlas.enrichment.models import Dataset
from netatlas.observation import Observation
from netatlas.read_api.boundary import ReadBoundary, SafeJSONResponse
from netatlas.read_api.cursors import Cursors, ReadError
from netatlas.read_api.models import SearchResponse
from netatlas.search.models import Query
from netatlas.storage.blobs import BlobStore
from netatlas.storage.pipeline import Pipeline

pytest_plugins = ["test_storage", "test_search"]
HEADERS = {"X-NetAtlas-Read": "1"}


def client_for(pipeline: Pipeline | None = None) -> TestClient:
    return TestClient(
        create_app(
            engine=pipeline.engine if pipeline else None, blobs=pipeline.blobs if pipeline else None
        ),
        base_url="http://127.0.0.1:8000",
        client=("127.0.0.1", 51000),
        headers=HEADERS,
    )


def post(
    client: TestClient,
    path: str = "search",
    query: dict[str, Any] | None = None,
    cursor: str | None = None,
) -> Any:
    return client.post(
        "/api/v1/" + path, json={"schema_version": 1, "query": query or {}, "cursor": cursor}
    )


def test_http_truth_and_all_read_routes(
    truth: tuple[Pipeline, Query, dict[str, Observation]],
) -> None:
    p, q, rows = truth
    with client_for(p) as client:
        body = q.model_dump(mode="json")
        result = post(client, query=body)
        assert result.status_code == 200, result.text
        parsed = SearchResponse.model_validate(result.json())
        assert parsed.counts.endpoints == 5 and parsed.counts.observations == 5
        assert parsed.counts.candidates == 4
        assert parsed.location_semantics == "approximate_area_not_person_or_device"
        facets = post(client, "facets", body).json()
        assert facets["counts"] == result.json()["counts"]
        assert facets["facets"] == result.json()["facets"]
        assert "hits" not in facets
        assert post(client, query=body | {"text": "nginx"}).json()["counts"]["endpoints"] == 2
        evidence = post(client, query=body | {"selection": "evidence"}).json()
        assert evidence["counts"]["candidates"] == 6
        assert any(h["category_state"] == "multiple" for h in evidence["hits"])
        assert any(h["geography_state"] == "unknown" for h in evidence["hits"])
        assert any(h["city"] and h["city"]["accuracy_radius_km"] is None for h in evidence["hits"])
        identities = {key: body[key] for key in ("pack_sha256", "dataset_sha256")}
        base = "endpoints/192.0.2.10/tcp/80/"
        detail = post(client, base + "detail", identities).json()
        assert detail["hits"][0]["id"] == str(rows["east_negative"].observation_id)
        detail = post(client, base + "detail", identities | {"selection": "evidence"}).json()
        assert detail["hits"][0]["id"] == str(rows["east_new"].observation_id)
        history = post(client, base + "history", identities).json()
        assert history["counts"]["observations"] == 3
        assert post(client, "endpoints/2001:db8::1/tcp/80/detail").status_code == 200
        assert post(client, "endpoints/192.0.2.99/tcp/80/detail").status_code == 404
        assert post(client, "endpoints/192.0.2.99/tcp/80/history").json()["hits"] == []
        assert post(client, "endpoints/example.org/tcp/80/detail").status_code == 422
        assert post(client, "scan").status_code == 404
        assert client.get("/api/v1/search").status_code == 405
        assert result.headers["cache-control"] == "no-store"
        assert result.headers["x-content-type-options"] == "nosniff"
        assert "access-control-allow-origin" not in result.headers


def test_cursor_order_binding_mutations_and_expiry(
    pipeline: Pipeline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row = observation(identity=UUID(int=1), age=100)
    for i in range(1, 7):
        pipeline.ingest(
            canonical(
                Observation.model_validate(row.model_dump() | {"observation_id": UUID(int=i)})
            ),
            synthetic=True,
        )
    with client_for(pipeline) as client:
        query = {"mode": "history", "limit": 2}
        first = post(client, query=query).json()
        assert [h["id"] for h in first["hits"]] == [str(UUID(int=i)) for i in (6, 5)]
        cursor = first["next_cursor"]
        assert (
            post(client, query=query, cursor=cursor).json()["hits"]
            == post(client, query=query, cursor=cursor).json()["hits"]
        )
        # A late source ahead of the keyset must not shift the second page or repeat rows.
        pipeline.ingest(
            canonical(
                Observation.model_validate(row.model_dump() | {"observation_id": UUID(int=7)})
            ),
            synthetic=True,
        )
        monkeypatch.setattr("netatlas.search.service.load_pack", ambiguous_pack)
        second = post(client, query=query, cursor=cursor).json()
        assert second["selection"]["pack_sha256"] == first["selection"]["pack_sha256"]
        assert [h["id"] for h in second["hits"]] == [str(UUID(int=i)) for i in (4, 3)]
        third = post(client, query=query, cursor=second["next_cursor"]).json()
        assert [h["id"] for h in third["hits"]] == [str(UUID(int=i)) for i in (2, 1)]
        assert third["next_cursor"] is None
        for changes in ({"limit": 3}, {"selection": "open"}, {"network": "192.0.2.0/24"}):
            assert post(client, query=query | changes, cursor=cursor).json() == {
                "error": {"code": "invalid_cursor"}
            }
        assert post(client, query=query, cursor=cursor[:-2] + "AA").status_code == 400
        endpoint = "endpoints/192.0.2.10/tcp/80/history"
        assert post(client, endpoint, {"limit": 2}, cursor).status_code == 400
        with client_for(pipeline) as restarted:
            assert post(restarted, query=query, cursor=cursor).status_code == 400

        class Later(datetime):
            @classmethod
            def now(cls, tz: Any = None) -> datetime:  # type: ignore[override]
                return datetime.now(UTC) + timedelta(minutes=16)

        monkeypatch.setattr("netatlas.read_api.service.datetime", Later)
        assert post(client, query=query, cursor=cursor).status_code == 410


def test_places_disambiguation_and_cursor(
    truth: tuple[Pipeline, Query, dict[str, Observation]],
) -> None:
    p, q, _ = truth
    with client_for(p) as client:
        query = {"dataset_sha256": q.dataset_sha256, "limit": 1, "name": "Example Harbor"}
        a = post(client, "places", query).json()
        b = post(client, "places", query, a["next_cursor"]).json()
        assert a["places"][0]["id"] != b["places"][0]["id"]
        assert a["places"][0]["name"] == b["places"][0]["name"]
        name = a["places"][0]["name"]
        both = post(client, "places", query | {"name": name.upper(), "limit": 200}).json()
        assert both["total"] == 2
        assert all("boundary" not in p for p in both["places"])
        assert both["dataset"]["origins"][0]["license"]
        assert post(client, "places", query | {"country": "ZZ"}).json()["total"] == 0
        assert post(client, "places", {"dataset_sha256": "0" * 64}).status_code == 404


@pytest.mark.parametrize("state", ["stale", "not_yet_valid"])
def test_stale_and_future_dataset(pipeline: Pipeline, state: str) -> None:
    now = datetime.now(UTC)
    patch = (
        {"expires_at": now - timedelta(seconds=1)}
        if state == "stale"
        else {"valid_from": now + timedelta(days=1)}
    )
    data = Dataset.model_validate(bundle(now).model_dump() | patch)
    ingest(pipeline, observation(age=100), data, now - timedelta(seconds=5))
    with client_for(pipeline) as client:
        q = {"dataset_sha256": digest(canonical(data))}
        result = post(client, query=q).json()
        assert result["hits"][0]["geography_state"] == state
        assert result["hits"][0]["network"] is None
        places = post(client, "places", q).json()
        assert places["dataset_state"] == state and places["places"] == []


def test_removal_and_expiry_on_every_route(
    truth: tuple[Pipeline, Query, dict[str, Observation]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    p, q, _ = truth
    with client_for(p) as client:
        query = q.model_dump(mode="json") | {"mode": "history", "limit": 1}
        first = post(client, query=query).json()
        with p.engine.begin() as conn:
            conn.execute(text("INSERT INTO suppressions (network) VALUES ('0.0.0.0/0'), ('::/0')"))
        assert post(client, query=query, cursor=first["next_cursor"]).json()["hits"] == []
        assert post(client, "facets", query).json()["counts"]["observations"] == 0
        assert post(client, "endpoints/192.0.2.10/tcp/80/detail").status_code == 404
        assert post(client, "endpoints/192.0.2.10/tcp/80/history").json()["hits"] == []
        assert post(client, "places", {"dataset_sha256": q.dataset_sha256}).status_code == 404
        p.maintain(suppress="0.0.0.0/0")
        p.maintain(suppress="::/0")
        p.consume(replay=True)
        assert post(client, query=query).json()["counts"]["observations"] == 0


def test_actual_expiry_and_cursor_dataset_clock(
    pipeline: Pipeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime.now(UTC)
    data = Dataset.model_validate(
        bundle(now).model_dump() | {"expires_at": now + timedelta(seconds=3)}
    )
    for addr in ("192.0.2.10", "192.0.2.200"):
        ingest(pipeline, observation(age=100, address=addr), data, now)
    with client_for(pipeline) as client:
        q = {"dataset_sha256": digest(canonical(data)), "limit": 1}
        first = post(client, query=q).json()

        class Later(datetime):
            @classmethod
            def now(cls, tz: Any = None) -> datetime:  # type: ignore[override]
                return now + timedelta(seconds=10)

        monkeypatch.setattr("netatlas.read_api.service.datetime", Later)
        page = post(client, query=q, cursor=first["next_cursor"]).json()
        assert page["hits"][0]["geography_state"] == "stale"
        assert page["dataset_checked_at"] != first["dataset_checked_at"]

        class Expired(datetime):
            @classmethod
            def now(cls, tz: Any = None) -> datetime:  # type: ignore[override]
                return now + timedelta(days=31)

        monkeypatch.setattr("netatlas.read_api.service.datetime", Expired)
        past = q | {"as_of": now.isoformat()}
        assert post(client, query=past).json()["hits"] == []
        assert post(client, "places", {"dataset_sha256": q["dataset_sha256"]}).status_code == 404


@pytest.mark.parametrize(
    "query",
    [
        {"limit": 201},
        {"offset": 1},
        {"facet_limit": 51},
        {"text": "x" * 257},
        {"network": "https://example.org"},
        {"as_of": "2999-01-01T00:00:00Z"},
        {"unknown": "secret"},
        {"limit": True},
        {"country": "FJ"},
    ],
)
def test_cost_input_bounds(query: dict[str, Any], pipeline: Pipeline) -> None:
    with client_for(pipeline) as client:
        response = post(client, query=query)
        assert response.status_code == 422
        assert response.json() == {"error": {"code": "invalid_request"}}


@pytest.mark.parametrize(
    "raw,status",
    [
        ('{"schema_version":1,"query":{"limit":1,"limit":2}}', 422),
        ('{"schema_version":1,"query":' + "[" * 40 + "0" + "]" * 40 + "}", 422),
        ('{"schema_version":1,' + " " * 16384 + "}", 413),
        ('{"schema_version":1,"private":"DO-NOT-ECHO"}', 422),
        ("{}", 422),
        ("not json", 422),
    ],
)
def test_json_boundary(raw: str, status: int) -> None:
    with client_for() as client:
        result = client.post(
            "/api/v1/search", content=raw, headers={"content-type": "application/json"}
        )
        assert result.status_code == status
        assert "DO-NOT-ECHO" not in result.text
        assert result.headers["cache-control"] == "no-store"


def test_access_policy_and_generic_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    with client_for() as client:
        for headers in (
            {"host": "evil.example"},
            {"origin": "https://evil.example"},
            {"origin": "null"},
            {"x-netatlas-read": "0"},
        ):
            result = client.post("/api/v1/search", json={"schema_version": 1}, headers=headers)
            assert result.status_code == 403
        assert client.post("/api/v1/search", content="{}").status_code == 415

        def unavailable(*args: Any, **kwargs: Any) -> Any:
            raise OSError("private credential")

        monkeypatch.setattr("netatlas.api.local_engine", unavailable)
        assert post(client).json() == {"error": {"code": "unavailable"}}
    with TestClient(create_app(), base_url="http://127.0.0.1", client=("192.0.2.1", 1)) as client:
        assert client.get("/healthz", headers={"x-forwarded-for": "127.0.0.1"}).status_code == 403


def test_metadata_allowlist_no_blob_or_target_access(
    pipeline: Pipeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime.now(UTC)
    raw = b"HTTP/1.1 200 OK\r\nServer: nginx\r\nSet-Cookie: DO-NOT-EXPORT\r\n\r\nPRIVATE-BODY"
    data = bundle(now).model_dump()
    data["places"][0]["name"] = '<img src="https://example.org/track">\x1b\u202e'
    data["origins"][0]["source_url"] = "javascript:alert(1)"
    pack = ambiguous_pack().model_dump()
    pack["rules"][0]["product"] = "<script>alert(1)</script>"
    from netatlas.derivations.models import RulePack

    p = RulePack.model_validate(pack)
    row = observation(body=raw)
    ingest(pipeline, row, Dataset.model_validate(data), now)
    pipeline.derive(row.observation_id, p)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("raw reads or target interaction prohibited")

    monkeypatch.setattr(BlobStore, "read", forbidden)
    monkeypatch.setattr("socket.getaddrinfo", forbidden)
    monkeypatch.setattr("netatlas.discovery.engine.run_campaign", forbidden)
    with client_for(pipeline) as client:
        result = post(
            client,
            query={
                "pack_sha256": digest(canonical(p)),
                "dataset_sha256": digest(canonical(Dataset.model_validate(data))),
            },
        )
        assert result.status_code == 200, result.text
        assert "<script>" not in result.text and "<img" not in result.text
        assert "\\u001b" in result.text and "\\u202e" in result.text
        assert "PRIVATE-BODY" not in result.text and "DO-NOT-EXPORT" not in result.text
        assert "body_base64" not in result.text and "evidence" not in result.json()["hits"][0]
        assert "<script>alert(1)</script>" in result.json()["hits"][0]["products"]


def test_openapi_contract() -> None:
    schema = create_app().openapi()
    expected = {"search", "facets", "places", "endpointDetail", "endpointHistory"}
    ops = {op["operationId"]: op for route in schema["paths"].values() for op in route.values()}
    assert expected <= ops.keys()
    for name in expected:
        op = ops[name]
        assert op["requestBody"]["required"]
        assert op["parameters"][-1]["name"] == "X-NetAtlas-Read"
        assert op["responses"]["422"]["content"]["application/json"]["schema"]["$ref"].endswith(
            "ErrorResponse"
        )
    assert "additionalProperties" in schema["components"]["schemas"]["SearchResponse"]
    assert "Observation" not in json.dumps(schema["components"]["schemas"]["SearchResponse"])


def test_response_cap_and_cursor_lifetime() -> None:
    with pytest.raises(ReadError) as exc:
        SafeJSONResponse({"text": "x" * (4 * 1024 * 1024)})
    assert exc.value.code == "response_too_large"
    cursor = Cursors()
    token = cursor.encode({"v": 1, "scope": "search", "query": "hash", "expires": 0})
    with pytest.raises(ReadError) as exc:
        cursor.decode(token, "search", "hash", datetime.now(UTC))
    assert exc.value.code == "cursor_expired"


def test_stream_bound_and_busy_admission() -> None:
    async def exercise() -> None:
        entered, release = asyncio.Event(), asyncio.Event()

        async def app(scope: Any, receive: Any, send: Any) -> None:
            entered.set()
            await release.wait()
            await SafeJSONResponse({"ok": True})(scope, receive, send)

        boundary = ReadBoundary(app, 8000)
        scope = {
            "type": "http",
            "path": "/api/v1/search",
            "method": "POST",
            "client": ("127.0.0.1", 1),
            "headers": [
                (b"host", b"127.0.0.1"),
                (b"x-netatlas-read", b"1"),
                (b"content-type", b"application/json"),
            ],
        }

        async def receive() -> Any:
            return {"type": "http.request", "body": b'{"schema_version":1}', "more_body": False}

        sent: list[Any] = []

        async def send(message: Any) -> None:
            sent.append(message)

        task = asyncio.create_task(boundary(scope, receive, send))
        await entered.wait()
        await boundary(scope, receive, send)
        assert sent[0]["status"] == 429
        release.set()
        await task
        sent.clear()

        async def large() -> Any:
            return {"type": "http.request", "body": b"x" * 9000, "more_body": True}

        await boundary(scope, large, send)
        assert sent[0]["status"] == 413

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "changes",
    [
        {"mode": "history"},
        {"selection": "evidence", "category": "router"},
        {"freshness": "stale"},
        {"category": "unknown"},
        {"asn": 64498},
        {"geography": "unknown"},
        {"country": "FJ"},
        {"place_id": "fixture:west"},
        {"radius": {"longitude": 180, "latitude": -17.5, "metres": 60000}},
        {"box": {"west": 170, "south": -20, "east": -170, "north": -10}},
        {"boundary_place_id": "fixture:east"},
        {"text": "'); DROP TABLE observations; --"},
    ],
)
def test_http_preserves_search_semantics(
    truth: tuple[Pipeline, Query, dict[str, Observation]],
    changes: dict[str, Any],
) -> None:
    from netatlas.search.service import search

    p, base, _ = truth
    query = Query.model_validate(base.model_dump() | changes)
    expected = search(p.engine, query)
    with client_for(p) as client:
        response = post(client, query=query.model_dump(mode="json"))
        assert response.status_code == 200
        result = response.json()
        assert result["counts"] == {
            key: expected[key] for key in ("endpoints", "observations", "candidates")
        }
        assert result["facets"] == expected["facets"]
        assert [h["id"] for h in result["hits"]] == [h["id"] for h in expected["hits"]]


def test_database_timeout_is_generic_and_releases_admission(
    pipeline: Pipeline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from netatlas.search.service import compile_query

    def slow(*args: Any, **kwargs: Any) -> Any:
        sql, params = compile_query(*args, **kwargs)
        return "SELECT pg_sleep(6)", params

    with client_for(pipeline) as client:
        monkeypatch.setattr("netatlas.search.service.compile_query", slow)
        response = post(client)
        assert response.status_code == 503
        assert response.json() == {"error": {"code": "unavailable"}}
        monkeypatch.setattr("netatlas.search.service.compile_query", compile_query)
        assert post(client).status_code == 200


def test_cursor_total_page_budget(pipeline: Pipeline) -> None:
    from netatlas.read_api.cursors import query_hash
    from netatlas.read_api.models import SearchQuery, SearchRequest
    from netatlas.read_api.service import Reader

    for _ in range(3):
        pipeline.ingest(canonical(observation()), synthetic=True)
    cursors = Cursors()
    reader = Reader(pipeline.engine, cursors)
    query = SearchQuery(mode="history", limit=2)
    now = datetime.now(UTC)
    # Signed boundary fixture represents 9999 already-consumed hits, with two remaining.
    token = cursors.encode(
        {
            "v": 1,
            "scope": "search",
            "query": query_hash(query.model_dump_json()),
            "expires": (now + timedelta(minutes=15)).timestamp(),
            "cutoff": now.isoformat(),
            "seen": 9999,
            "pack": None,
            "after": [now.isoformat(), now.isoformat(), str(UUID(int=99))],
        }
    )
    result = reader.search(SearchRequest(schema_version=1, query=query, cursor=token))
    assert len(result.hits) == 1 and result.page_limit_reached
    assert result.next_cursor is None and result.counts.observations == 3


def test_api_import_cannot_load_collectors() -> None:
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import netatlas.api, sys; "
            "assert not any(n.startswith('netatlas.collectors') or "
            "n.startswith('netatlas.discovery') for n in sys.modules)",
        ],
        check=False,
    )
    assert result.returncode == 0
