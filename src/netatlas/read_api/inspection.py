"""Read-only inspection orchestration with live source checks and explicit projection."""

from datetime import UTC, datetime

from netatlas.domain import Endpoint
from netatlas.inspection.models import InspectionRequest, InspectionResponse
from netatlas.inspection.preview import capture_view
from netatlas.inspection.project import check_trace, exchanges
from netatlas.read_api.cursors import ReadError
from netatlas.storage.database import transaction
from netatlas.storage.inspection import eligible, load_bound, load_derivation
from netatlas.storage.pipeline import Pipeline


def inspect_source(
    pipeline: Pipeline,
    endpoint: Endpoint,
    body: InspectionRequest,
) -> InspectionResponse:
    q = body.query
    with transaction(pipeline.engine) as conn:
        from sqlalchemy import text

        conn.execute(text("SET LOCAL statement_timeout = '5s'"))
        source = load_bound(pipeline, conn, q.observation_id, q.source_sha256, endpoint.key)
        if source is None:
            raise ReadError(404, "not_found")
        derived = None
        if q.derivation_id:
            derived = load_derivation(conn, q.derivation_id, q.observation_id, q.source_sha256)
            if derived is None:
                raise ReadError(404, "not_found")
            check_trace(source, derived)
        legacy = capture_view(source.response, "/response/body_base64") if source.response else None
        projected = exchanges(source)
        # Parsing/blob reads may cross the expiry instant; check again before returning.
        expires = eligible(conn, q.observation_id, q.source_sha256, endpoint.key)
        if expires is None:
            raise ReadError(404, "not_found")
        return InspectionResponse(
            observation_id=source.observation_id,
            source_sha256=q.source_sha256,
            source_schema_version=source.schema_version,
            address=str(source.endpoint.address),
            transport=source.endpoint.transport.value,
            port=source.endpoint.port,
            started_at=source.started_at,
            finished_at=source.finished_at,
            expires_at=expires,
            retention_checked_at=datetime.now(UTC),
            outcome=source.outcome.value,
            legacy_capture=legacy,
            exchanges=projected,
            derivation_id=q.derivation_id,
            derivation=derived,
            trace_integrity="checked" if derived else "not_requested",
        )
