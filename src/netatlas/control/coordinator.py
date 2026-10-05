"""Durable coordinator. All authority, pacing and ingestion share the pipeline lock."""

import json
from datetime import datetime, timedelta
from ipaddress import ip_network
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Connection, text

from netatlas.config import Settings
from netatlas.control.models import (
    DELIVERY_HOURS,
    LEASE_SECONDS,
    MAX_ATTEMPTS,
    MAX_JOBS,
    MAX_QUEUE,
    PERMIT_SECONDS,
    Abandon,
    Authority,
    Claim,
    ControlError,
    Deliver,
    Heartbeat,
    Lease,
    Permit,
    Register,
    Reply,
    Request,
    Resume,
    request_reader,
)
from netatlas.derivations.engine import canonical, digest
from netatlas.discovery.policy import POLICY_SHA256, denial
from netatlas.discovery.scope import Scope
from netatlas.domain import Endpoint
from netatlas.storage.database import transaction
from netatlas.storage.pipeline import Pipeline


def clock(connection: Connection) -> datetime:
    value: datetime = connection.execute(text("SELECT clock_timestamp()")).scalar_one()
    return value


def rows(connection: Connection, sql: str, **params: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in connection.execute(text(sql), params).mappings()]


def execute(connection: Connection, sql: str, **params: Any) -> None:
    connection.execute(text(sql), params)


class Coordinator:
    def __init__(self, pipeline: Pipeline):
        self.pipeline = pipeline

    def enqueue(self, settings: Settings, scope: Scope, *, measure: bool, synthetic: bool) -> UUID:
        settings = Settings.model_validate(settings.model_dump())
        scope = Scope.model_validate(scope.model_dump())
        # Phase 10's worker adapter is deliberately narrower than standalone discovery.
        if (
            not measure
            or not synthetic
            or not settings.measurement.enabled
            or not scope.lab_loopback
        ):
            raise ValueError("enabled explicit synthetic literal-loopback measurement required")
        endpoints = tuple(scope.endpoints(settings.measurement))
        if not endpoints or len(endpoints) > min(MAX_QUEUE, settings.measurement.queue_size):
            raise ValueError("bounded nonempty queue required")
        document = {
            "settings": settings.model_dump(mode="json"),
            "scope": scope.model_dump(mode="json"),
        }
        if len(json.dumps(document).encode()) > 12288:
            raise ValueError("bounded campaign envelope required")
        with transaction(self.pipeline.engine) as connection:
            now = clock(connection)
            return self.enqueue_in_transaction(connection, settings, scope, endpoints, now)

    def enqueue_in_transaction(
        self,
        connection: Connection,
        settings: Settings,
        scope: Scope,
        endpoints: tuple[Endpoint, ...],
        now: datetime,
        *,
        deadline: datetime | None = None,
    ) -> UUID:
        """Internal adapter. Caller validates lab scope and holds the pipeline lock."""
        self._reap(connection, now)
        if connection.execute(text("SELECT stopped FROM control_switch")).scalar_one():
            raise ControlError(410, "stopped")
        if rows(
            connection,
            "SELECT 1 FROM control_jobs WHERE state IN ('queued','leased','measuring') LIMIT 1",
        ):
            raise ControlError(409, "campaign_active")
        total: int = connection.execute(text("SELECT count(*) FROM control_jobs")).scalar_one()
        if total + len(endpoints) > MAX_JOBS:
            raise ControlError(429, "queue_full")
        identity = uuid4()
        execute(
            connection,
            """
            INSERT INTO control_campaigns
            (id, document, config_sha256, policy_sha256, created_at, deadline)
            VALUES (:id, CAST(:document AS jsonb), :sha, :policy, :now, :deadline)
        """,
            id=identity,
            document=json.dumps(
                {
                    "settings": settings.model_dump(mode="json"),
                    "scope": scope.model_dump(mode="json"),
                }
            ),
            sha=settings.sha256,
            policy=POLICY_SHA256,
            now=now,
            deadline=min(
                deadline or now + timedelta(seconds=settings.measurement.campaign_timeout_seconds),
                now + timedelta(seconds=settings.measurement.campaign_timeout_seconds),
            ),
        )
        for position, endpoint in enumerate(endpoints):
            if self._suppressed(connection, str(endpoint.address)):
                raise ControlError(410, "stopped")
            execute(
                connection,
                """
                INSERT INTO control_jobs (id, campaign_id, address, port, state, position)
                VALUES (:id, :campaign, CAST(:address AS inet), :port, 'queued', :position)
            """,
                id=uuid4(),
                campaign=identity,
                address=str(endpoint.address),
                port=endpoint.port,
                position=position,
            )
        return identity

    def stop(self) -> None:
        """Durable global stop. Reopening admission never revives cancelled work."""
        with transaction(self.pipeline.engine) as connection:
            execute(
                connection,
                """UPDATE control_switch SET stopped=true,
                generation=generation+1, changed_at=clock_timestamp()""",
            )
            execute(connection, "UPDATE control_campaigns SET cancelled=true")
            execute(connection, "UPDATE control_jobs SET state='cancelled'")

    def is_stopped(self) -> bool:
        with transaction(self.pipeline.engine) as connection:
            stopped: bool = connection.execute(
                text("SELECT stopped FROM control_switch")
            ).scalar_one()
            return stopped

    def allow_new_work(self) -> None:
        with transaction(self.pipeline.engine) as connection:
            execute(
                connection,
                """UPDATE control_switch SET stopped=false,
                generation=generation+1, changed_at=clock_timestamp()""",
            )

    def cancel(self, campaign: UUID) -> None:
        with transaction(self.pipeline.engine) as connection:
            execute(
                connection, "UPDATE control_campaigns SET cancelled=true WHERE id=:id", id=campaign
            )
            execute(
                connection,
                "UPDATE control_jobs SET state='cancelled' WHERE campaign_id=:id",
                id=campaign,
            )

    def status(self) -> dict[str, int]:
        with transaction(self.pipeline.engine) as connection:
            self._reap(connection, clock(connection))
            return {
                row["state"]: row["count"]
                for row in rows(
                    connection, "SELECT state, count(*) FROM control_jobs GROUP BY state"
                )
            }

    def prune(self) -> None:
        """Explicit bounded history maintenance; never resets pacing or worker generations."""
        with transaction(self.pipeline.engine) as connection:
            cutoff = clock(connection) - timedelta(days=90)
            execute(
                connection,
                """DELETE FROM control_jobs WHERE campaign_id IN
                (SELECT id FROM control_campaigns WHERE deadline < :cutoff)""",
                cutoff=cutoff,
            )
            execute(
                connection,
                """DELETE FROM control_campaigns WHERE deadline < :cutoff
                AND NOT EXISTS (SELECT 1 FROM control_jobs
                    WHERE campaign_id=control_campaigns.id)""",
                cutoff=cutoff,
            )

    @staticmethod
    def _suppressed(connection: Connection, address: str) -> bool:
        return bool(
            rows(
                connection,
                "SELECT 1 FROM suppressions WHERE CAST(:address AS inet) <<= network",
                address=address,
            )
        )

    def _reap(self, connection: Connection, now: datetime) -> None:
        execute(
            connection,
            """
            UPDATE control_jobs j SET state='cancelled' FROM control_campaigns c
            WHERE j.campaign_id=c.id AND j.state <> 'cancelled' AND
                (c.cancelled OR (SELECT stopped FROM control_switch)
                 OR EXISTS (SELECT 1 FROM suppressions s WHERE j.address <<= s.network))
        """,
        )
        execute(
            connection,
            """
            UPDATE control_jobs j SET state=CASE WHEN a.connections > 0 THEN 'uncertain'
                WHEN c.deadline <= :now THEN 'cancelled'
                WHEN j.fence >= :maximum THEN 'failed' ELSE 'queued' END
            FROM control_attempts a, control_campaigns c
            WHERE a.job_id=j.id AND a.fence=j.fence AND c.id=j.campaign_id
                AND j.state IN ('leased','measuring')
                AND (a.lease_until <= :now OR c.deadline <= :now
                     OR a.hard_until <= :now)
        """,
            now=now,
            maximum=MAX_ATTEMPTS,
        )
        execute(
            connection,
            """UPDATE control_jobs j SET state='cancelled'
            FROM control_campaigns c WHERE c.id=j.campaign_id
            AND j.state='queued' AND c.deadline <= :now""",
            now=now,
        )

    def exchange(self, request: Request) -> Reply:
        # Authenticate at the transport before this method. Revalidate library callers too.
        request = request_reader.validate_python(request.model_dump())
        with transaction(self.pipeline.engine) as connection:
            now = clock(connection)
            self._reap(connection, now)
            if isinstance(request, Register):
                result = self._register(connection, request, now)
            else:
                if not rows(
                    connection,
                    """SELECT 1 FROM control_workers
                    WHERE id=:worker AND session_id=:session""",
                    worker=request.worker_id,
                    session=request.session_id,
                ):
                    raise ControlError(409, "fenced")
                if isinstance(request, Claim):
                    result = self._claim(connection, request, now)
                else:
                    result = self._owned(connection, request, now)
            self.pipeline.hook("control_before_commit")
        self.pipeline.hook("control_after_commit")
        return result

    def _register(self, connection: Connection, request: Register, now: datetime) -> Reply:
        workers = rows(
            connection, "SELECT * FROM control_workers WHERE id=:id", id=request.worker_id
        )
        if workers:
            old = workers[0]
            if request.generation < old["generation"] or (
                request.generation == old["generation"] and request.session_id != old["session_id"]
            ):
                raise ControlError(409, "fenced")
            if request.generation == old["generation"]:
                return Reply()
            # A new boot revokes ALL prior measurement authority, including a lost claim ACK.
            execute(
                connection,
                """UPDATE control_attempts SET lease_until=:now
                WHERE worker_id=:id AND session_id=:session""",
                now=now,
                id=request.worker_id,
                session=old["session_id"],
            )
            self._reap(connection, now)
            execute(
                connection,
                """UPDATE control_workers SET session_id=:session,
                generation=:generation, heartbeat_at=:now WHERE id=:id""",
                session=request.session_id,
                generation=request.generation,
                now=now,
                id=request.worker_id,
            )
        else:
            if connection.execute(text("SELECT count(*) FROM control_workers")).scalar_one() >= 2:
                raise ControlError(429, "worker_limit")
            execute(
                connection,
                "INSERT INTO control_workers VALUES (:id,:session,:generation,:now)",
                id=request.worker_id,
                session=request.session_id,
                generation=request.generation,
                now=now,
            )
        return Reply()

    def _claim(self, connection: Connection, request: Claim, now: datetime) -> Reply:
        # Claim replay returns the same unstarted lease. It never grants a second active job.
        active = rows(
            connection,
            """SELECT j.id FROM control_jobs j JOIN control_attempts a
            ON a.job_id=j.id AND a.fence=j.fence WHERE a.worker_id=:worker
            AND j.state IN ('leased','measuring')""",
            worker=request.worker_id,
        )
        if active:
            return self._lease(connection, active[0]["id"], now)
        candidates = rows(
            connection,
            """SELECT j.*, c.document FROM control_jobs j
            JOIN control_campaigns c ON c.id=j.campaign_id WHERE j.state='queued'
            ORDER BY c.created_at,j.position,j.id LIMIT 1""",
        )
        if not candidates:
            return Reply(status="idle")
        job = candidates[0]
        settings = Settings.model_validate(job["document"]["settings"])
        # Uncertain/cancelled issued attempts keep their socket slots until the hard horizon.
        occupied: int = connection.execute(
            text("""SELECT count(*) FROM control_attempts a
            JOIN control_jobs j ON j.id=a.job_id AND j.fence=a.fence
            WHERE (j.state='leased' AND a.lease_until > :now)
            OR (a.hard_until > :now AND j.state <> 'delivered')"""),
            {"now": now},
        ).scalar_one()
        if occupied >= min(2, settings.measurement.max_concurrency):
            return Reply(status="wait", delay_seconds=1)
        attempt, observation = uuid4(), uuid4()
        fence = job["fence"] + 1
        execute(
            connection,
            "UPDATE control_jobs SET state='leased', fence=:fence WHERE id=:id",
            fence=fence,
            id=job["id"],
        )
        execute(
            connection,
            """INSERT INTO control_attempts
            (id,job_id,fence,observation_id,worker_id,session_id,delivery_session,
             lease_until,claimed_at,delivery_until)
            VALUES (:id,:job,:fence,:observation,:worker,:session,:session,:until,:now,:delivery)
        """,
            id=attempt,
            job=job["id"],
            fence=fence,
            observation=observation,
            worker=request.worker_id,
            session=request.session_id,
            now=now,
            until=now + timedelta(seconds=LEASE_SECONDS),
            delivery=now + timedelta(hours=DELIVERY_HOURS),
        )
        return self._lease(connection, job["id"], now)

    def _lease(self, connection: Connection, job: UUID, now: datetime) -> Reply:
        row = self._row(connection, job)
        return Reply(
            lease=Lease(
                job_id=job,
                attempt_id=row["id"],
                observation_id=row["observation_id"],
                campaign_id=row["campaign_id"],
                fence=row["fence"],
                endpoint=Endpoint.model_validate(
                    {"address": str(row["address"]), "port": row["port"]}
                ),
                settings=Settings.model_validate(row["document"]["settings"]),
                config_sha256=row["config_sha256"],
                policy_sha256=row["policy_sha256"],
                remaining_seconds=max(0.001, (row["deadline"] - now).total_seconds()),
            )
        )

    @staticmethod
    def _row(connection: Connection, job: UUID) -> dict[str, Any]:
        found = rows(
            connection,
            """SELECT a.*, j.state,j.address,j.port,j.campaign_id,
            c.document,c.config_sha256,c.policy_sha256,c.deadline,c.cancelled
            FROM control_jobs j JOIN control_attempts a ON a.job_id=j.id AND a.fence=j.fence
            JOIN control_campaigns c ON c.id=j.campaign_id WHERE j.id=:job""",
            job=job,
        )
        if not found:
            raise ControlError(409, "fenced")
        return found[0]

    def _owned(self, connection: Connection, request: Authority, now: datetime) -> Reply:
        row = self._row(connection, request.job_id)
        if (
            row["id"] != request.attempt_id
            or row["fence"] != request.fence
            or row["worker_id"] != request.worker_id
        ):
            raise ControlError(409, "fenced")
        if row["state"] in ("cancelled", "failed", "queued") or row["delivery_until"] <= now:
            raise ControlError(410, "stopped")
        if isinstance(request, Resume):
            if not row["connections"]:
                raise ControlError(410, "stopped")
            execute(
                connection,
                "UPDATE control_attempts SET delivery_session=:session WHERE id=:id",
                session=request.session_id,
                id=row["id"],
            )
            return Reply()
        if isinstance(request, Deliver):
            if row["delivery_session"] != request.session_id:
                raise ControlError(409, "fenced")
            return self._deliver(connection, request, row, now)
        if row["session_id"] != request.session_id:
            raise ControlError(409, "fenced")
        if isinstance(request, Abandon):
            execute(
                connection,
                "UPDATE control_attempts SET lease_until=:now WHERE id=:id",
                now=now,
                id=row["id"],
            )
            self._reap(connection, now)
            return Reply()
        if (
            row["state"] not in ("leased", "measuring")
            or row["lease_until"] <= now
            or row["deadline"] <= now
            or (row["hard_until"] and row["hard_until"] <= now)
        ):
            raise ControlError(410, "stopped")
        if isinstance(request, Heartbeat):
            execute(
                connection,
                "UPDATE control_attempts SET lease_until=:until WHERE id=:id",
                until=min(now + timedelta(seconds=LEASE_SECONDS), row["deadline"]),
                id=row["id"],
            )
            execute(
                connection,
                "UPDATE control_workers SET heartbeat_at=:now WHERE id=:id",
                now=now,
                id=request.worker_id,
            )
            return Reply()
        if isinstance(request, Permit):
            return self._permit(connection, request, row, now)
        raise ControlError(422, "invalid_request")

    def _permit(
        self, connection: Connection, request: Permit, row: dict[str, Any], now: datetime
    ) -> Reply:
        settings = Settings.model_validate(row["document"]["settings"])
        config = settings.measurement
        endpoint = Endpoint.model_validate({"address": str(row["address"]), "port": row["port"]})
        if (
            row["policy_sha256"] != POLICY_SHA256
            or settings.sha256 != row["config_sha256"]
            or denial(endpoint.address, config, lab=True)
        ):
            raise ControlError(410, "stopped")
        cap = config.max_connections_per_endpoint if config.protocol_evidence else 1
        if request.connection != row["connections"] + 1 or request.connection > cap:
            # A lost permit ACK is burned. Never replay it into another dial.
            raise ControlError(409, "permit_consumed")
        prefix = str(
            ip_network(
                f"{endpoint.address}/{24 if endpoint.address.version == 4 else 48}", strict=False
            )
        )
        budgets = (
            ("global", config.global_connections_per_second),
            (prefix, config.per_prefix_connections_per_second),
        )
        delay = 0.0
        for key, rate in budgets:
            found = rows(connection, "SELECT * FROM control_pacing WHERE key=:key", key=key)
            if found:
                if now < found[0]["last_at"]:
                    raise ControlError(503, "clock_regressed")
                delay = max(
                    delay,
                    (
                        max(
                            found[0]["next_at"],
                            found[0]["last_at"] + timedelta(seconds=PERMIT_SECONDS + 1 / rate),
                        )
                        - now
                    ).total_seconds(),
                )
        if delay > 0:
            return Reply(status="wait", delay_seconds=min(3600, delay))
        for key, rate in budgets:
            # Reserve the full start window PLUS spacing, so delayed responses cannot burst.
            execute(
                connection,
                """INSERT INTO control_pacing VALUES (:key,:next,:now)
                ON CONFLICT (key) DO UPDATE SET next_at=:next,last_at=:now""",
                key=key,
                next=now + timedelta(seconds=PERMIT_SECONDS + 1 / rate),
                now=now,
            )
        hard = row["hard_until"] or min(
            row["deadline"],
            now
            + timedelta(
                seconds=PERMIT_SECONDS
                + max(config.endpoint_timeout_seconds, config.connect_timeout_seconds)
            ),
        )
        if (hard - now).total_seconds() < PERMIT_SECONDS:
            raise ControlError(410, "stopped")
        execute(
            connection,
            """UPDATE control_attempts SET connections=connections+1,
            started_at=COALESCE(started_at,:now), hard_until=:hard WHERE id=:id""",
            now=now,
            hard=hard,
            id=row["id"],
        )
        execute(
            connection, "UPDATE control_jobs SET state='measuring' WHERE id=:id", id=request.job_id
        )
        return Reply(status="granted", valid_seconds=PERMIT_SECONDS)

    def _deliver(
        self, connection: Connection, request: Deliver, row: dict[str, Any], now: datetime
    ) -> Reply:
        source = request.observation
        config = Settings.model_validate(row["document"]["settings"]).measurement
        evidence = source.protocol_evidence
        if (
            not row["connections"]
            or digest(canonical(source)) != request.source_sha256
            or source.observation_id != row["observation_id"]
            or str(source.endpoint.address) != str(row["address"])
            or source.endpoint.port != row["port"]
            or source.endpoint.transport.value != "tcp"
            or source.target.campaign_id != str(row["campaign_id"])
            or source.target.source != "loopback-lab"
            or source.scanner.node_id != str(request.worker_id)
            or source.config_sha256 != row["config_sha256"]
            or source.started_at < row["claimed_at"] - timedelta(seconds=5)
            or source.finished_at > min(row["hard_until"], row["deadline"]) + timedelta(seconds=5)
            or source.network is not None
            or source.geolocation is not None
            or source.response is not None
            or (
                source.service is not None
                and (
                    source.service.fingerprints
                    or source.service.classifications
                    or source.service.protocol_name is not None
                )
            )
            or (config.protocol_evidence != (evidence is not None))
            or (
                evidence is not None
                and (
                    len(evidence.exchanges) != row["connections"]
                    or evidence.received_bytes > config.max_response_bytes
                    or evidence.retained_bytes > config.max_response_bytes
                    or evidence.sent_bytes > config.max_sent_bytes
                    or [e.probe for e in evidence.exchanges]
                    != ["greeting-http", "tls"][: row["connections"]]
                )
            )
            or (row["source_sha256"] is not None and row["source_sha256"] != request.source_sha256)
        ):
            raise ControlError(409, "identity_conflict")
        if source.finished_at + timedelta(days=30) <= now or rows(
            connection, "SELECT 1 FROM tombstones WHERE id=:id", id=source.observation_id
        ):
            raise ControlError(410, "source_rejected")
        try:
            result = self.pipeline.ingest_in_transaction(
                connection, canonical(source), synthetic=True, now=now
            )
        except ValueError:
            raise ControlError(503, "source_integrity") from None
        execute(
            connection,
            "UPDATE control_attempts SET source_sha256=:sha WHERE id=:id",
            sha=request.source_sha256,
            id=row["id"],
        )
        execute(
            connection, "UPDATE control_jobs SET state='delivered' WHERE id=:id", id=request.job_id
        )
        return Reply(status="inserted" if result == "inserted" else "replayed")
