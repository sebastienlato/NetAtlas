"""Endpoint/source-bound inspection reads inside the caller's pipeline lock."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Connection, text

from netatlas.derivations.engine import canonical, digest
from netatlas.derivations.models import Derivation
from netatlas.domain import ObservationV1
from netatlas.observation import Observation
from netatlas.storage.pipeline import Pipeline

AnyObservation = ObservationV1 | Observation


def eligible(
    conn: Connection,
    observation_id: UUID,
    source_sha256: str,
    endpoint_key: str,
) -> datetime | None:
    """Recheck actual time and persistent suppression, including before cleanup."""
    return conn.execute(
        text("""SELECT expires_at FROM observations o
        WHERE id=:id AND source_sha256=:sha AND endpoint_key=:endpoint
        AND expires_at>:now AND NOT EXISTS (
            SELECT 1 FROM suppressions s WHERE o.address <<= s.network)"""),
        {
            "id": observation_id,
            "sha": source_sha256,
            "endpoint": endpoint_key,
            "now": datetime.now(UTC),
        },
    ).scalar_one_or_none()


def load_bound(
    pipeline: Pipeline,
    conn: Connection,
    observation_id: UUID,
    source_sha256: str,
    endpoint_key: str,
) -> AnyObservation | None:
    if eligible(conn, observation_id, source_sha256, endpoint_key) is None:
        return None
    # Reconstruction verifies all stored pointer/blob identities and canonical digest.
    return pipeline._load(conn, observation_id)


def load_derivation(
    conn: Connection,
    identity: str,
    observation_id: UUID,
    source_sha256: str,
) -> Derivation | None:
    document = conn.execute(
        text("""SELECT document FROM derivations
        WHERE id=:id AND observation_id=:source AND source_sha256=:sha"""),
        {"id": identity, "source": observation_id, "sha": source_sha256},
    ).scalar_one_or_none()
    if document is None:
        return None
    result = Derivation.model_validate(document)
    if (
        digest(canonical(result)) != identity
        or result.source_observation_id != observation_id
        or result.source_sha256 != source_sha256
    ):
        raise ValueError("derivation integrity failure")
    return result
