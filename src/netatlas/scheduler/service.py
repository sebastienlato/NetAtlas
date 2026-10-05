"""Trusted local adapters. No scheduler operation dials targets or bypasses permits."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Connection, text

from netatlas.control.coordinator import Coordinator, clock, execute, rows
from netatlas.control.models import ControlError
from netatlas.derivations.engine import canonical, digest
from netatlas.discovery.policy import denial
from netatlas.discovery.scope import Scope
from netatlas.domain import Endpoint
from netatlas.scheduler.models import PlanningInput, Source
from netatlas.scheduler.planner import plan
from netatlas.storage.database import transaction

DOCUMENT_BYTES = 1048576


def source_row(row: dict[str, object]) -> Source:
    return Source.model_validate(
        {
            "endpoint": {"address": str(row["address"]), "port": row["port"]},
            "observation_id": row["id"],
            "source_sha256": row["source_sha256"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "outcome": row["outcome"],
        }
    )


def latest(connection: Connection, endpoint: Endpoint, now: datetime) -> Source | None:
    found = rows(
        connection,
        """SELECT id,source_sha256,address,port,started_at,finished_at,outcome
        FROM observations WHERE endpoint_key=:key
        AND expires_at > :now ORDER BY finished_at DESC, started_at DESC, id DESC LIMIT 1""",
        key=endpoint.key,
        now=now,
    )
    return source_row(found[0]) if found else None


def snapshot(coordinator: Coordinator, request: PlanningInput) -> PlanningInput:
    """Explicit bounded retained-history snapshot, separate from pure offline planning."""
    request = PlanningInput.model_validate(request.model_dump())
    with transaction(coordinator.pipeline.engine) as connection:
        now = clock(connection)
        networks = [r.network for r in request.universe.regions]
        history = rows(
            connection,
            """SELECT DISTINCT ON (endpoint_key)
            id,source_sha256,address,port,started_at,finished_at,outcome FROM observations
            WHERE address <<= ANY(CAST(:networks AS cidr[])) AND port=ANY(:ports)
            AND transport='tcp' AND expires_at > :now AND finished_at <= :now
            AND NOT EXISTS (SELECT 1 FROM suppressions s WHERE address <<= s.network)
            ORDER BY endpoint_key, finished_at DESC, started_at DESC, id DESC LIMIT 4097""",
            networks=networks,
            ports=list(request.universe.ports),
            now=now,
        )
        blocked = rows(
            connection,
            """SELECT DISTINCT j.address,j.port FROM control_jobs j
            LEFT JOIN control_attempts a ON a.job_id=j.id AND a.fence=j.fence
            WHERE j.state IN ('queued','leased','measuring')
            OR (a.connections > 0 AND a.source_sha256 IS NULL)
            ORDER BY j.address,j.port LIMIT 1025""",
        )
        suppressions = rows(
            connection, "SELECT network FROM suppressions ORDER BY network LIMIT 1025"
        )
        result = PlanningInput.model_validate(
            request.model_dump()
            | {
                "at": now,
                "history": [source_row(row) for row in history],
                "blocked": [
                    {"address": str(row["address"]), "port": row["port"]} for row in blocked
                ],
                "suppressions": [str(row["network"]) for row in suppressions],
            }
        )

        plan(result)  # Current universe validity and all bounds still apply.
        if len(canonical(result)) > DOCUMENT_BYTES:
            raise ValueError("snapshot document bound")
        return result


def enqueue(
    coordinator: Coordinator, request: PlanningInput, *, measure: bool, synthetic: bool
) -> UUID:
    """Replay-safe all-or-nothing admission. Plans are never a worker authority token."""
    request = PlanningInput.model_validate(request.model_dump())
    schedule = plan(request)
    endpoints = tuple(entry.endpoint for entry in schedule.entries)
    settings = request.settings
    if (
        not measure
        or not synthetic
        or not settings.measurement.enabled
        or not endpoints
        or not request.lab_loopback
        or any(r.network not in ("127.0.0.1/32", "::1/128") for r in request.universe.regions)
    ):
        raise ValueError("explicit enabled synthetic measurement and nonempty plan required")
    # No address translation: the exact planned endpoint must itself be literal loopback.
    scope = Scope(
        targets=tuple(sorted({str(e.address) for e in endpoints})),
        ports=tuple(sorted({e.port for e in endpoints})),
        lab_loopback=True,
    )
    scope.networks(settings.measurement)
    if len(endpoints) > min(32, 128, settings.measurement.queue_size) or any(
        denial(e.address, settings.measurement, lab=True) for e in endpoints
    ):
        raise ValueError("bounded loopback policy required")
    document = canonical(request)
    if len(document) > DOCUMENT_BYTES or len(canonical(settings)) + len(canonical(scope)) > 12288:
        raise ValueError("schedule or campaign document bound")
    sha = digest(canonical(schedule))
    with transaction(coordinator.pipeline.engine) as connection:
        now = clock(connection)
        existing = rows(
            connection, "SELECT id FROM control_campaigns WHERE schedule_sha256=:sha", sha=sha
        )
        if existing:
            # Exact replay acknowledges the old identity, including stopped/expired runs.
            return UUID(str(existing[0]["id"]))
        if not request.at <= now < schedule.expires_at:
            raise ControlError(410, "schedule_expired")
        for entry in schedule.entries:
            if coordinator._suppressed(connection, str(entry.endpoint.address)):
                raise ControlError(410, "stopped")
            if latest(connection, entry.endpoint, now) != entry.previous:
                raise ControlError(409, "history_changed")
            if rows(
                connection,
                """SELECT 1 FROM control_jobs j
                JOIN control_attempts a ON a.job_id=j.id AND a.fence=j.fence
                WHERE j.address=CAST(:address AS inet) AND j.port=:port
                AND a.connections > 0 AND a.source_sha256 IS NULL LIMIT 1""",
                address=str(entry.endpoint.address),
                port=entry.endpoint.port,
            ):
                raise ControlError(409, "unresolved_attempt")
        campaign = coordinator.enqueue_in_transaction(
            connection, settings, scope, endpoints, now, deadline=schedule.expires_at
        )
        execute(
            connection,
            """UPDATE control_campaigns SET schedule_sha256=:sha,
            schedule_document=CAST(:document AS jsonb) WHERE id=:id""",
            sha=sha,
            document=document.decode(),
            id=campaign,
        )
        for entry in schedule.entries:
            if entry.previous:
                execute(
                    connection,
                    """UPDATE control_jobs SET refresh_source_id=:source,
                    refresh_source_sha256=:sha WHERE campaign_id=:campaign
                    AND address=CAST(:address AS inet) AND port=:port""",
                    source=entry.previous.observation_id,
                    sha=entry.previous.source_sha256,
                    campaign=campaign,
                    address=str(entry.endpoint.address),
                    port=entry.endpoint.port,
                )
        # Recheck actual expiry after the bounded writes/lock; failure rolls back all work.
        if clock(connection) >= schedule.expires_at:
            raise ControlError(410, "schedule_expired")
        coordinator.pipeline.hook("schedule_before_commit")
    coordinator.pipeline.hook("schedule_after_commit")
    return campaign


def report(coordinator: Coordinator, campaign: UUID) -> dict[str, object]:
    with transaction(coordinator.pipeline.engine) as connection:
        now = clock(connection)
        coordinator._reap(connection, now)
        campaigns = rows(connection, "SELECT * FROM control_campaigns WHERE id=:id", id=campaign)
        if not campaigns or campaigns[0]["schedule_document"] is None:
            raise ValueError("schedule not found")
        request = PlanningInput.model_validate(campaigns[0]["schedule_document"])
        schedule = plan(request)
        if digest(canonical(schedule)) != campaigns[0]["schedule_sha256"]:
            raise ValueError("schedule integrity")
        counts = rows(
            connection,
            """SELECT count(*) AS scheduled,
            count(*) FILTER (WHERE a.connections > 0) AS admitted,
            COALESCE(sum(a.connections),0) AS permits_issued,
            count(*) FILTER (WHERE a.source_sha256 IS NOT NULL) AS measured,
            count(*) FILTER (WHERE j.state IN ('uncertain','cancelled','failed')
                AND a.connections > 0 AND a.source_sha256 IS NULL) AS incomplete_or_uncertain,
            count(*) FILTER (WHERE j.state IN ('cancelled','failed')
                AND COALESCE(a.connections,0)=0) AS not_admitted,
            count(*) FILTER (WHERE j.state='queued') AS queued,
            count(*) FILTER (WHERE j.state IN ('leased','measuring')) AS active,
            count(*) FILTER (WHERE a.source_sha256 IS NOT NULL
                AND j.refresh_source_id IS NOT NULL) AS refreshed,
            count(*) FILTER (WHERE o.expires_at > :now AND NOT EXISTS
                (SELECT 1 FROM suppressions s WHERE o.address <<= s.network)) AS retained
            FROM control_jobs j LEFT JOIN control_attempts a ON a.job_id=j.id AND a.fence=j.fence
            LEFT JOIN observations o ON o.id=a.observation_id AND o.source_sha256=a.source_sha256
            WHERE j.campaign_id=:id""",
            id=campaign,
            now=now,
        )[0]
        stopped: bool = connection.execute(text("SELECT stopped FROM control_switch")).scalar_one()
        return {
            "schema_version": 1,
            "campaign_id": str(campaign),
            "schedule_sha256": campaigns[0]["schedule_sha256"],
            "checked_at": now.isoformat(),
            "global_stopped": stopped,
            "cancelled": campaigns[0]["cancelled"],
            "expired": now >= campaigns[0]["deadline"],
            "planning": schedule.counts,
            "execution": counts,
        }
