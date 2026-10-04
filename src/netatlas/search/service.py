"""Exact PostgreSQL search. Selection precedes filters; no fan-out joins in counts."""

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Connection, Engine, text

from netatlas.derivations.engine import canonical, digest
from netatlas.derivations.offline import load_pack
from netatlas.enrichment.geometry import bounding_boundary
from netatlas.search.models import Query
from netatlas.storage.database import transaction

TEXT_VECTOR = (
    "to_tsvector('simple', jsonb_path_query_array(d.document, '$.candidates[*].product')::text)"
)
VALID = """(e.document->>'dataset_state' = 'valid'
    AND CAST(ds.document->>'valid_from' AS timestamptz) <= :geo_at
    AND CAST(ds.document->>'expires_at' AS timestamptz) > :geo_at)"""
GEO_STATE = f"""CASE WHEN ds.sha256 IS NULL THEN 'unknown'
    WHEN CAST(ds.document->>'valid_from' AS timestamptz) > :geo_at THEN 'not_yet_valid'
    WHEN CAST(ds.document->>'expires_at' AS timestamptz) <= :geo_at THEN 'stale'
    WHEN {VALID} AND e.point IS NOT NULL THEN 'known' ELSE 'unknown' END"""


def compile_query(
    query: Query,
    now: datetime,
    *,
    cutoff: datetime | None = None,
    page_after: tuple[str, str, str] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Build parameterized SQL; only constant field/operator fragments are interpolated."""
    at = query.as_of or cutoff or now
    if at > now:
        raise ValueError("as_of cannot be in the future")
    params: dict[str, Any] = {
        "now": now,
        "geo_at": (query.as_of or now),
        "at": at,
        "fresh_after": at - timedelta(seconds=query.fresh_seconds),
        "pack": query.pack_sha256 or digest(canonical(load_pack())),
        "dataset": query.dataset_sha256,
        "fp_engine": query.fingerprint_engine,
        "taxonomy": query.taxonomy,
        "en_engine": query.enrichment_engine,
        "limit": query.limit,
        "offset": query.offset,
        "facet_limit": query.facet_limit,
    }
    page_filter = ""
    if page_after is not None:
        page_filter = """WHERE (finished_at,started_at,id) <
            (CAST(:page_finish AS timestamptz),CAST(:page_start AS timestamptz),
             CAST(:page_id AS uuid))"""
        params.update(zip(("page_finish", "page_start", "page_id"), page_after, strict=True))
    scope = {"attempt": "true", "open": "o.outcome='open'", "evidence": "o.has_evidence"}[
        query.selection
    ]
    filters = [
        scope,
        "o.expires_at > :now",
        "o.finished_at <= :at",
        "NOT EXISTS (SELECT 1 FROM suppressions s WHERE o.address <<= s.network)",
    ]
    if query.mode == "current":
        newer_scope = scope.replace("o.", "n.")
        filters.append(f"""NOT EXISTS (SELECT 1 FROM observations n
            WHERE n.endpoint_key=o.endpoint_key AND n.expires_at>:now AND n.finished_at<=:at
            AND {newer_scope}
            AND (n.finished_at,n.started_at,n.id)>(o.finished_at,o.started_at,o.id))""")
    for name in ("port", "transport", "outcome", "has_evidence"):
        value = getattr(query, name)
        if value is not None:
            filters.append(f"o.{name}=:{name}")
            params[name] = value
    for name, operator in (("after", ">="), ("before", "<")):
        value = getattr(query, name)
        if value is not None:
            filters.append(f"o.finished_at {operator} :{name}")
            params[name] = value
    if query.network:
        filters.append("o.address <<= CAST(:network AS inet)")
        params["network"] = query.network
    if query.freshness != "any":
        filters.append(
            "o.finished_at " + (">=" if query.freshness == "fresh" else "<") + " :fresh_after"
        )
    if query.category is not None:
        if query.category.value == "unknown":
            filters.append("COALESCE(d.document->>'category_state','unknown')='unknown'")
        else:
            filters.append("d.document @> CAST(:category AS jsonb)")
            params["category"] = json.dumps({"candidates": [{"category": query.category.value}]})
    if query.text:
        filters.append(f"{TEXT_VECTOR} @@ plainto_tsquery('simple', :text)")
        params["text"] = query.text
    for name, document in (
        ("asn", {"network": {"asns": [query.asn]}}),
        ("country", {"place": {"country_code": query.country}}),
        ("place_id", {"place": {"id": query.place_id}}),
    ):
        if getattr(query, name) is not None:
            filters.extend([VALID, f"e.document @> CAST(:{name} AS jsonb)"])
            params[name] = json.dumps(document)
    if query.geography != "any":
        filters.append(f"({GEO_STATE})=:geography")
        params["geography"] = query.geography
    if query.radius:
        filters.extend(
            [
                VALID,
                """ST_DWithin(e.point,
            ST_SetSRID(ST_MakePoint(:longitude,:latitude),4326)::geography,:metres)""",
            ]
        )
        params.update(query.radius.model_dump())
    if query.box:
        b = query.box
        boundary = bounding_boundary(b.west, b.south, b.east, b.north)
        params["box"] = boundary.model_dump_json()
        filters.extend([VALID, "ST_Covers(ST_GeomFromGeoJSON(:box),e.point::geometry)"])
    if query.boundary_place_id:
        filters.extend(
            [
                VALID,
                """EXISTS (SELECT 1 FROM places p
            WHERE p.dataset_sha256=:dataset AND p.id=:boundary
            AND ST_Covers(p.boundary,e.point::geometry))""",
            ]
        )
        params["boundary"] = query.boundary_place_id
    # One derivation per explicit identity; one latest enrichment per source/dataset/engine.
    # No filtering on a result until after the result has been selected.
    sql = f"""WITH matched AS MATERIALIZED (
        SELECT o.id,o.endpoint_key,host(o.address) AS address,o.port,o.transport,o.outcome,
            o.finished_at,o.started_at,o.has_evidence,o.source_sha256,
            o.finished_at >= :fresh_after AS fresh,
            d.id AS derivation_id,e.id AS enrichment_id,
            COALESCE(d.document->>'category_state','unknown') AS category_state,
            COALESCE(d.document->'candidates','[]'::jsonb) AS candidates,
            {GEO_STATE} AS geography_state,
            CASE WHEN {VALID} THEN e.document->'network' ELSE NULL END AS network,
            CASE WHEN {VALID} AND e.place_id IS NOT NULL THEN jsonb_build_object(
                'id',e.place_id,'name',e.document#>'{{place,name}}',
                'country_code',e.document#>'{{place,country_code}}',
                'point',e.document#>'{{place,point}}') ELSE NULL END AS place,
            CASE WHEN {VALID} THEN e.document->'city' ELSE NULL END AS city
        FROM observations o
        LEFT JOIN derivations d ON d.observation_id=o.id AND d.pack_sha256=:pack
            AND d.engine_version=:fp_engine AND d.taxonomy_version=:taxonomy
        LEFT JOIN enrichment_datasets ds ON ds.sha256=:dataset
        LEFT JOIN enrichments e ON e.observation_id=o.id AND e.dataset_sha256=:dataset
            AND e.engine_version=:en_engine AND e.evaluated_at<=:at
            AND NOT EXISTS (SELECT 1 FROM enrichments newer WHERE
                newer.observation_id=e.observation_id AND newer.dataset_sha256=e.dataset_sha256
                AND newer.engine_version=e.engine_version AND newer.evaluated_at<=:at
                AND (newer.evaluated_at,newer.id)>(e.evaluated_at,e.id))
        WHERE {" AND ".join(filters)}
    ), buckets AS (
        SELECT m.id,m.endpoint_key,f.kind,f.value FROM matched m CROSS JOIN LATERAL (
            SELECT 'category' AS kind, value #>> '{{}}' AS value FROM
                jsonb_path_query_array(m.candidates,'$[*].category ? (@ != null)') a,
                jsonb_array_elements(a) value
            UNION SELECT 'category','unknown' WHERE m.category_state='unknown'
            UNION SELECT 'asn',value FROM jsonb_array_elements_text(
                COALESCE(m.network->'asns','[]'::jsonb)) value
            UNION SELECT 'asn','unknown' WHERE m.network IS NULL OR m.network='null'::jsonb
            UNION SELECT 'country',COALESCE(m.place->>'country_code','unknown')
            UNION SELECT 'prefix',COALESCE(m.network->>'prefix','unknown')
            UNION SELECT 'geography',m.geography_state
        ) f
    ), grouped AS (
        SELECT kind,value,count(DISTINCT endpoint_key) AS endpoints,
            count(DISTINCT id) AS observations FROM buckets GROUP BY kind,value
    ), ranked AS (
        SELECT *,row_number() OVER (PARTITION BY kind ORDER BY endpoints DESC,value COLLATE "C")
            AS rank,count(*) OVER (PARTITION BY kind) AS total_buckets FROM grouped
    ), page AS (
        SELECT id,source_sha256,address,port,transport,outcome,finished_at,started_at,
            has_evidence,fresh,
            derivation_id,enrichment_id,category_state,geography_state,network,place,city,
            jsonb_array_length(candidates) AS candidate_count,
            jsonb_path_query_array(candidates,'$[*].product ? (@ != null)') AS products,
            jsonb_path_query_array(candidates,'$[*].category ? (@ != null)') AS categories
        FROM matched {page_filter} ORDER BY finished_at DESC,started_at DESC,id DESC
        LIMIT :limit OFFSET :offset
    ) SELECT jsonb_build_object(
        'dataset',(SELECT document - 'places' - 'asn_prefixes' - 'city_prefixes'
            FROM enrichment_datasets WHERE sha256=:dataset),
        'pack',(SELECT document - 'rules' FROM packs WHERE sha256=:pack),
        'endpoints',(SELECT count(DISTINCT endpoint_key) FROM matched),
        'observations',(SELECT count(*) FROM matched),
        'candidates',(SELECT COALESCE(sum(jsonb_array_length(candidates)),0) FROM matched),
        'hits',COALESCE((SELECT jsonb_agg(to_jsonb(page)
            ORDER BY finished_at DESC,started_at DESC,id DESC) FROM page),'[]'::jsonb),
        'facets',COALESCE((SELECT jsonb_agg(to_jsonb(ranked) ORDER BY kind,rank)
            FROM ranked WHERE rank<=:facet_limit),'[]'::jsonb))"""
    return sql, params


def search_connection(
    connection: Connection,
    query: Query,
    now: datetime,
    *,
    cutoff: datetime | None = None,
    page_after: tuple[str, str, str] | None = None,
    extra_hit: bool = False,
) -> dict[str, Any]:
    """Caller holds the pipeline lock; one SQL snapshot supplies counts and page."""
    sql, params = compile_query(query, now, cutoff=cutoff, page_after=page_after)
    if extra_hit:
        params["limit"] += 1
    connection.execute(text("SET LOCAL statement_timeout = '5s'"))
    result: dict[str, Any] = connection.execute(text(sql), params).scalar_one()
    result["selection"] = query.model_dump(mode="json") | {
        "as_of": params["at"].isoformat(),
        "pack_sha256": params["pack"],
    }
    result["retention_checked_at"] = now.isoformat()
    return result


def search(engine: Engine, query: Query) -> dict[str, Any]:
    """Return exact counts and bounded metadata in one serialized DB snapshot."""
    with transaction(engine) as connection:
        return search_connection(connection, query, datetime.now(UTC))
