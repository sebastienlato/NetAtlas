"""Read orchestration and explicit transport projection, separate from SQL search."""

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from sqlalchemy import Engine, text

from netatlas.domain import Model
from netatlas.read_api.cursors import Cursors, ReadError, query_hash
from netatlas.read_api.models import (
    Counts,
    DatasetMetadata,
    Facet,
    Hit,
    PackMetadata,
    PlacesRequest,
    PlacesResponse,
    PlaceSummary,
    SearchQuery,
    SearchRequest,
    SearchResponse,
)
from netatlas.search.service import search_connection
from netatlas.storage.database import transaction


def project[T: Model](model: type[T], row: dict[str, Any]) -> T:
    """Allowlist fields rather than serialize private result dictionaries wholesale."""
    return model.model_validate({key: row[key] for key in model.model_fields if key in row})


class Reader:
    def __init__(self, engine: Engine, cursors: Cursors) -> None:
        self.engine, self.cursors = engine, cursors

    def search(self, request: SearchRequest, scope: str = "search") -> SearchResponse:
        q = request.query
        identity = query_hash(q.model_dump_json())
        with transaction(self.engine) as conn:
            now = datetime.now(UTC)
            cursor = (
                self.cursors.decode(request.cursor, scope, identity, now)
                if request.cursor
                else None
            )
            cutoff = datetime.fromisoformat(cursor["cutoff"]) if cursor else now
            after = tuple(cursor["after"]) if cursor else None
            limit = min(q.limit, 10000 - (cursor["seen"] if cursor else 0))
            result = search_connection(
                conn,
                q.model_copy(
                    update={
                        "limit": limit,
                        "pack_sha256": cursor["pack"] if cursor else q.pack_sha256,
                    }
                ),
                now,
                cutoff=cutoff,
                page_after=after,
                extra_hit=True,
            )
            hits = result["hits"][:limit]
            seen = (cursor["seen"] if cursor else 0) + len(hits)
            more = len(result["hits"]) > limit
            token = None
            if more and seen < 10000:
                last = hits[-1]
                token = self.cursors.encode(
                    {
                        "v": 1,
                        "scope": scope,
                        "query": identity,
                        "expires": cursor["expires"]
                        if cursor
                        else (now + timedelta(minutes=15)).timestamp(),
                        "cutoff": cutoff.isoformat(),
                        "pack": result["selection"]["pack_sha256"],
                        "seen": seen,
                        "after": [last["finished_at"], last["started_at"], last["id"]],
                    }
                )
            return SearchResponse(
                selection=SearchQuery.model_validate(result["selection"] | {"limit": q.limit}),
                retention_checked_at=now,
                dataset_checked_at=q.as_of or now,
                dataset=project(DatasetMetadata, result["dataset"]) if result["dataset"] else None,
                pack=project(PackMetadata, result["pack"]) if result["pack"] else None,
                counts=Counts(**{key: result[key] for key in Counts.model_fields}),
                facets=tuple(project(Facet, row) for row in result["facets"]),
                hits=tuple(project(Hit, row) for row in hits),
                next_cursor=token,
                page_limit_reached=more and seen >= 10000,
            )

    def places(self, request: PlacesRequest) -> PlacesResponse:
        q = request.query
        identity = query_hash(q.model_dump_json())
        with transaction(self.engine) as conn:
            now = datetime.now(UTC)
            cursor = (
                self.cursors.decode(request.cursor, "places", identity, now)
                if request.cursor
                else None
            )
            conn.execute(text("SET LOCAL statement_timeout = '5s'"))
            # A dataset is visible only while at least one associated source remains readable.
            doc = conn.execute(
                text("""SELECT d.document - 'places' - 'asn_prefixes' - 'city_prefixes'
                FROM enrichment_datasets d WHERE sha256=:dataset AND EXISTS (
                    SELECT 1 FROM enrichments e JOIN observations o ON o.id=e.observation_id
                    WHERE e.dataset_sha256=d.sha256 AND o.expires_at>:now
                    AND NOT EXISTS (SELECT 1 FROM suppressions s
                        WHERE o.address <<= s.network))"""),
                {"dataset": q.dataset_sha256, "now": now},
            ).scalar_one_or_none()
            if doc is None:
                raise ReadError(404, "not_found")
            metadata = project(DatasetMetadata, doc)
            state: Literal["valid", "stale", "not_yet_valid"] = (
                "not_yet_valid"
                if now < metadata.valid_from
                else "stale"
                if now >= metadata.expires_at
                else "valid"
            )
            rows = []
            if state == "valid":
                rows = list(
                    conn.execute(
                        text("""SELECT document - 'boundary' AS document,
                    boundary IS NOT NULL AS has_boundary FROM places WHERE dataset_sha256=:dataset
                    ORDER BY id COLLATE "C" LIMIT 4096"""),
                        {"dataset": q.dataset_sha256},
                    ).mappings()
                )
            places = [
                project(PlaceSummary, row["document"] | {"has_boundary": row["has_boundary"]})
                for row in rows
                if (q.name is None or row["document"]["name"].casefold() == q.name.casefold())
                and (q.country is None or row["document"]["country_code"] == q.country)
                and (q.kind is None or row["document"]["kind"] == q.kind)
            ]
            remaining = [p for p in places if cursor is None or p.id > cursor["after"]]
            page = remaining[: q.limit]
            token = None
            if len(remaining) > q.limit:
                token = self.cursors.encode(
                    {
                        "v": 1,
                        "scope": "places",
                        "query": identity,
                        "expires": cursor["expires"]
                        if cursor
                        else (now + timedelta(minutes=15)).timestamp(),
                        "after": page[-1].id,
                    }
                )
            return PlacesResponse(
                dataset_sha256=q.dataset_sha256,
                dataset=metadata,
                dataset_state=state,
                retention_checked_at=now,
                places=tuple(page),
                total=len(places),
                next_cursor=token,
            )
