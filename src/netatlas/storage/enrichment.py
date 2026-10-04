"""Transactional adapter for pure enrichment and replayable spatial projections."""

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Connection, text

from netatlas.derivations.engine import canonical, digest
from netatlas.enrichment.engine import enrich
from netatlas.enrichment.models import Dataset, Enrichment, Place, Position
from netatlas.enrichment.offline import DATASET_BYTES
from netatlas.storage.database import transaction

if TYPE_CHECKING:
    from netatlas.storage.pipeline import Pipeline


def point_json(point: Position | None) -> str | None:
    return json.dumps({"type": "Point", "coordinates": point}) if point is not None else None


def save_dataset(connection: Connection, dataset: Dataset) -> str:
    data = canonical(dataset)
    if len(data) > DATASET_BYTES:
        raise ValueError("dataset limit")
    sha = digest(data)
    inserted = connection.execute(
        text("""
        INSERT INTO enrichment_datasets VALUES (:sha, CAST(:document AS jsonb))
        ON CONFLICT DO NOTHING RETURNING sha256
    """),
        {"sha": sha, "document": data.decode()},
    ).scalar_one_or_none()
    if inserted:
        for place in dataset.places:
            connection.execute(
                text("""
                INSERT INTO places (dataset_sha256, id, name, country_code, admin_code,
                                    point, boundary, document)
                VALUES (:sha, :id, :name, :country, :admin,
                    ST_GeomFromGeoJSON(:point)::geography, ST_GeomFromGeoJSON(:boundary),
                    CAST(:document AS jsonb))
            """),
                {
                    "sha": sha,
                    "id": place.id,
                    "name": place.name,
                    "country": place.country_code,
                    "admin": place.admin_code,
                    "point": point_json(place.point),
                    "boundary": place.boundary.model_dump_json() if place.boundary else None,
                    "document": place.model_dump_json(),
                },
            )
    return sha


def store_enrichment(pipeline: Pipeline, identity: UUID, dataset: Dataset, at: datetime) -> str:
    with transaction(pipeline.engine) as connection:
        source = pipeline._load(connection, identity)
        record = enrich(source, dataset, at)
        sha = save_dataset(connection, dataset)
        encoded = canonical(record)
        result_id = digest(encoded)
        params = {
            "id": result_id,
            "source": identity,
            "source_sha": record.source_sha256,
            "dataset": sha,
            "engine": record.engine_version,
            "at": record.evaluated_at,
            "place": record.place.id if record.place else None,
            "point": point_json(record.place.point if record.place else None),
            "document": encoded.decode(),
        }
        inserted = connection.execute(
            text("""
            INSERT INTO enrichments (id, observation_id, source_sha256, dataset_sha256,
                                     engine_version, evaluated_at, place_id, point, document)
            VALUES (:id, :source, :source_sha, :dataset, :engine, :at, :place,
                    ST_GeomFromGeoJSON(:point)::geography, CAST(:document AS jsonb))
            ON CONFLICT DO NOTHING RETURNING id
        """),
            params,
        ).scalar_one_or_none()
        existing: str = connection.execute(
            text("""
            SELECT id FROM enrichments WHERE observation_id=:source AND source_sha256=:source_sha
            AND dataset_sha256=:dataset AND engine_version=:engine AND evaluated_at=:at
        """),
            params,
        ).scalar_one()
        if existing != result_id:
            raise ValueError("enrichment identity conflict; engine version review required")
        if inserted:
            pipeline._event(connection, identity, "derivation")
        pipeline.hook("before_commit")
    pipeline.hook("after_commit")
    return result_id


def same_point(stored: Any, expected: Position | None) -> bool:
    return bool(stored == json.loads(point_json(expected) or "null"))


def verify_enrichments(pipeline: Pipeline, connection: Connection) -> int:
    datasets: dict[str, Dataset] = {}
    for row in connection.execute(text("SELECT * FROM enrichment_datasets")).mappings():
        dataset = Dataset.model_validate(row["document"])
        if digest(canonical(dataset)) != row["sha256"]:
            raise ValueError("dataset integrity failure")
        datasets[row["sha256"]] = dataset
        stored_places = (
            connection.execute(
                text("""
            SELECT *, ST_AsGeoJSON(point::geometry, 17)::jsonb AS point_json,
                      ST_AsGeoJSON(boundary, 17)::jsonb AS boundary_json
            FROM places WHERE dataset_sha256=:sha ORDER BY id
        """),
                {"sha": row["sha256"]},
            )
            .mappings()
            .all()
        )
        if len(stored_places) != len(dataset.places):
            raise ValueError("gazetteer integrity failure")
        for stored, expected in zip(
            sorted(stored_places, key=lambda p: p["id"]),
            sorted(dataset.places, key=lambda p: p.id),
            strict=True,
        ):
            if (
                Place.model_validate(stored["document"]) != expected
                or stored["id"] != expected.id
                or stored["name"] != expected.name
                or stored["country_code"] != expected.country_code
                or stored["admin_code"] != expected.admin_code
                or not same_point(stored["point_json"], expected.point)
                or stored["boundary_json"]
                != (expected.boundary.model_dump(mode="json") if expected.boundary else None)
            ):
                raise ValueError("gazetteer projection integrity failure")
    count = 0
    for row in connection.execute(
        text("""
        SELECT *, ST_AsGeoJSON(point::geometry, 17)::jsonb AS point_json FROM enrichments
    """)
    ).mappings():
        record = Enrichment.model_validate(row["document"])
        replayed = enrich(
            pipeline._load(connection, row["observation_id"]),
            datasets[row["dataset_sha256"]],
            row["evaluated_at"],
        )
        if (
            record != replayed
            or digest(canonical(record)) != row["id"]
            or row["source_sha256"] != replayed.source_sha256
            or row["engine_version"] != replayed.engine_version
            or row["place_id"] != (replayed.place.id if replayed.place else None)
            or not same_point(row["point_json"], replayed.place.point if replayed.place else None)
        ):
            raise ValueError("enrichment integrity failure")
        count += 1
    return count
