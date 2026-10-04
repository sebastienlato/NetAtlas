"""Bounded synthetic ingestion, immutable history, replay and removal transactions."""

import base64
import json
import re
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from ipaddress import ip_network
from typing import Any
from uuid import UUID

from sqlalchemy import Connection, Engine, text

from netatlas.derivations.engine import canonical, derive, digest
from netatlas.derivations.models import Derivation, RulePack
from netatlas.derivations.offline import LINE_BYTES, PACK_BYTES, read_observation
from netatlas.domain import ObservationV1
from netatlas.observation import Observation
from netatlas.storage.blobs import BlobStore
from netatlas.storage.database import transaction
from netatlas.storage.enrichment import verify_enrichments

ObservationRecord = ObservationV1 | Observation
Hook = Callable[[str], None]
Handler = Callable[[Connection, str, UUID], None]
SYNTHETIC_NETWORKS = tuple(
    map(
        ip_network,
        (
            "192.0.2.0/24",
            "198.51.100.0/24",
            "203.0.113.0/24",
            "2001:db8::/32",
            "127.0.0.1/32",
            "::1/128",
        ),
    )
)


def no_hook(stage: str) -> None:
    pass


def raw_fields(document: Any, pointer: str = "") -> Iterator[tuple[dict[str, Any], str, str]]:
    """Only schema-validated base64 fields, including certificate DER, are extracted."""
    if isinstance(document, dict):
        for key, value in document.items():
            path = f"{pointer}/{key}"
            if key in ("body_base64", "der_base64") and isinstance(value, str):
                yield document, key, path
            else:
                yield from raw_fields(value, path)
    elif isinstance(document, list):
        for index, value in enumerate(document):
            yield from raw_fields(value, f"{pointer}/{index}")


def rebuild_current(connection: Connection, endpoint_key: str) -> None:
    connection.execute(
        text("DELETE FROM current_services WHERE endpoint_key=:key"), {"key": endpoint_key}
    )
    # Independent order statistics preserve positive evidence through negative attempts.
    connection.execute(
        text("""
        INSERT INTO current_services (endpoint_key, last_attempt, last_open, last_evidence)
        SELECT :key,
            (array_agg(id ORDER BY finished_at DESC, started_at DESC, id DESC))[1],
            (array_agg(id ORDER BY finished_at DESC, started_at DESC, id DESC)
                FILTER (WHERE outcome='open'))[1],
            (array_agg(id ORDER BY finished_at DESC, started_at DESC, id DESC)
                FILTER (WHERE has_evidence))[1]
        FROM observations WHERE endpoint_key=:key HAVING count(*) > 0
    """),
        {"key": endpoint_key},
    )


def mirror_handler(connection: Connection, consumer: str, subject: UUID) -> None:
    """An idempotent example DB consumer reads live truth, even for reordered events."""
    connection.execute(
        text("""
        DELETE FROM consumer_observations WHERE consumer=:consumer AND observation_id=:id
    """),
        {"consumer": consumer, "id": subject},
    )
    connection.execute(
        text("""
        INSERT INTO consumer_observations (consumer, observation_id, source_sha256)
        SELECT :consumer, id, source_sha256 FROM observations
        WHERE id=:id AND expires_at > clock_timestamp()
    """),
        {"consumer": consumer, "id": subject},
    )


class Pipeline:
    def __init__(self, engine: Engine, blobs: BlobStore, *, hook: Hook = no_hook):
        self.engine = engine
        self.blobs = blobs
        self.hook = hook

    def ingest(self, raw: bytes, *, synthetic: bool = False, now: datetime | None = None) -> str:
        if len(raw) > LINE_BYTES or not synthetic:
            raise ValueError("bounded synthetic ingestion only")
        observation = read_observation(raw)
        if not any(observation.endpoint.address in net for net in SYNTHETIC_NETWORKS):
            raise ValueError("synthetic documentation or literal loopback address required")
        source_sha = digest(canonical(observation))
        timestamp = now or datetime.now(UTC)
        expiry = observation.finished_at + timedelta(days=30)
        if expiry <= timestamp or observation.finished_at > timestamp + timedelta(minutes=5):
            raise ValueError("expired or future observation")
        with transaction(self.engine) as connection:
            if connection.execute(
                text("SELECT 1 FROM tombstones WHERE id=:id"), {"id": observation.observation_id}
            ).first():
                raise ValueError("removed observation")
            if connection.execute(
                text("""
                SELECT 1 FROM suppressions WHERE CAST(:address AS inet) <<= network
            """),
                {"address": str(observation.endpoint.address)},
            ).first():
                raise ValueError("suppressed address")
            previous = connection.execute(
                text("""
                SELECT source_sha256 FROM observations WHERE id=:id
            """),
                {"id": observation.observation_id},
            ).scalar_one_or_none()
            if previous is not None:
                if previous != source_sha:
                    raise ValueError("observation identity conflict")
                # Never acknowledge a replay when its durable bytes are missing/corrupt.
                self._load(connection, observation.observation_id)
                result = "replayed"
            else:
                document = observation.model_dump(mode="json")
                references: list[tuple[str, str, int]] = []
                for parent, key, pointer in raw_fields(document):
                    data = base64.b64decode(parent[key], validate=True)
                    sha = self.blobs.put(data)
                    parent[key] = sha
                    references.append((pointer, sha, len(data)))
                self.hook("after_blobs")
                connection.execute(
                    text("""
                    INSERT INTO observations (id, source_sha256, schema_version, endpoint_key,
                        address, transport, port, started_at, finished_at, outcome, has_evidence,
                        document, expires_at)
                    VALUES (:id, :sha, :schema, :key, CAST(:address AS inet), :transport, :port,
                        :started, :finished, :outcome, :evidence,
                        CAST(:document AS jsonb), :expires)
                """),
                    {
                        "id": observation.observation_id,
                        "sha": source_sha,
                        "schema": observation.schema_version,
                        "key": observation.endpoint.key,
                        "address": str(observation.endpoint.address),
                        "transport": observation.endpoint.transport.value,
                        "port": observation.endpoint.port,
                        "started": observation.started_at,
                        "finished": observation.finished_at,
                        "outcome": observation.outcome.value,
                        "evidence": any(size > 0 for _, _, size in references),
                        "document": json.dumps(document),
                        "expires": expiry,
                    },
                )
                for pointer, sha, size in references:
                    connection.execute(
                        text("""
                        INSERT INTO blobs (sha256, size) VALUES (:sha, :size)
                        ON CONFLICT DO NOTHING
                    """),
                        {"sha": sha, "size": size},
                    )
                    connection.execute(
                        text("""
                        INSERT INTO evidence_refs VALUES (:id, :pointer, :sha)
                    """),
                        {"id": observation.observation_id, "pointer": pointer, "sha": sha},
                    )
                rebuild_current(connection, observation.endpoint.key)
                self._event(connection, observation.observation_id, "observation")
                self.hook("before_commit")
                result = "inserted"
        self.hook("after_commit")
        return result

    def _load(self, connection: Connection, observation_id: UUID) -> ObservationRecord:
        row = (
            connection.execute(
                text("""
            SELECT document, source_sha256, expires_at FROM observations WHERE id=:id
        """),
                {"id": observation_id},
            )
            .mappings()
            .one()
        )
        if row["expires_at"] <= datetime.now(UTC):
            raise ValueError("expired observation")
        document = row["document"]
        references: dict[str, str] = dict(
            connection.execute(
                text("""
            SELECT pointer, blob_sha256 FROM evidence_refs WHERE observation_id=:id
        """),
                {"id": observation_id},
            ).all()
        )
        seen = set()
        for parent, key, pointer in raw_fields(document):
            sha = references.get(pointer)
            if sha is None or sha != parent[key]:
                raise ValueError("evidence reference mismatch")
            parent[key] = base64.b64encode(self.blobs.read(sha)).decode("ascii")
            seen.add(pointer)
        if seen != set(references):
            raise ValueError("unresolved evidence references")
        observation = read_observation(json.dumps(document).encode())
        if digest(canonical(observation)) != row["source_sha256"]:
            raise ValueError("source integrity failure")
        return observation

    def load(self, observation_id: UUID) -> ObservationRecord:
        with transaction(self.engine) as connection:
            return self._load(connection, observation_id)

    def derive(self, observation_id: UUID, pack: RulePack) -> str:
        pack_bytes = canonical(pack)
        if len(pack_bytes) > PACK_BYTES:
            raise ValueError("pack limit")
        with transaction(self.engine) as connection:
            source = self._load(connection, observation_id)
            record = derive(source, pack)
            encoded = canonical(record)
            identity = digest(encoded)
            connection.execute(
                text("""
                INSERT INTO packs VALUES (:sha, CAST(:document AS jsonb)) ON CONFLICT DO NOTHING
            """),
                {"sha": record.pack_sha256, "document": pack_bytes.decode()},
            )
            inserted = connection.execute(
                text("""
                INSERT INTO derivations (id, observation_id, source_sha256, pack_sha256,
                    engine_version, taxonomy_version, schema_version, document)
                VALUES (:id, :source, :sha, :pack, :engine, :taxonomy, :schema,
                    CAST(:document AS jsonb)) ON CONFLICT DO NOTHING RETURNING id
            """),
                {
                    "id": identity,
                    "source": observation_id,
                    "sha": record.source_sha256,
                    "pack": record.pack_sha256,
                    "engine": record.engine_version,
                    "taxonomy": record.taxonomy_version,
                    "schema": record.schema_version,
                    "document": encoded.decode(),
                },
            ).scalar_one_or_none()
            existing: str = connection.execute(
                text("""
                SELECT id FROM derivations WHERE observation_id=:source AND source_sha256=:sha
                AND pack_sha256=:pack AND engine_version=:engine AND taxonomy_version=:taxonomy
            """),
                {
                    "source": observation_id,
                    "sha": record.source_sha256,
                    "pack": record.pack_sha256,
                    "engine": record.engine_version,
                    "taxonomy": record.taxonomy_version,
                },
            ).scalar_one()
            if existing != identity:
                raise ValueError("derivation identity conflict; engine version review required")
            if inserted:
                self._event(connection, observation_id, "derivation")
            self.hook("before_commit")
        self.hook("after_commit")
        return identity

    def verify(self) -> dict[str, int]:
        """Check durable bytes and independently replay every retained derivation."""
        with transaction(self.engine) as connection:
            count = 0
            ids: Any = connection.execute(text("SELECT id FROM observations ORDER BY id")).scalars()
            for identity in ids:
                self._load(connection, identity)
                count += 1
            derived = 0
            for row in connection.execute(
                text("""
                SELECT d.id, d.observation_id, d.document, p.document AS pack
                FROM derivations d JOIN packs p ON p.sha256=d.pack_sha256
            """)
            ).mappings():
                record = Derivation.model_validate(row["document"])
                expected = derive(
                    self._load(connection, row["observation_id"]),
                    RulePack.model_validate(row["pack"]),
                )
                if record != expected or digest(canonical(record)) != row["id"]:
                    raise ValueError("derivation integrity failure")
                derived += 1
            return {
                "observations": count,
                "derivations": derived,
                "enrichments": verify_enrichments(self, connection),
            }

    @staticmethod
    def _event(connection: Connection, subject: UUID, kind: str) -> None:
        connection.execute(
            text("INSERT INTO outbox (subject, kind) VALUES (:id, :kind)"),
            {"id": subject, "kind": kind},
        )

    def consume(
        self,
        consumer: str = "local-mirror",
        *,
        limit: int = 100,
        handler: Handler = mirror_handler,
        replay: bool = False,
        after: int = 0,
    ) -> dict[str, int]:
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", consumer) or after < 0:
            raise ValueError("invalid consumer or cursor")
        if not 1 <= limit <= 1024:
            raise ValueError("consumer limit")
        with transaction(self.engine) as connection:
            events = connection.execute(
                text("""
                SELECT id, subject FROM outbox o WHERE id > :after AND (:replay OR NOT EXISTS (
                    SELECT 1 FROM consumer_receipts r WHERE r.event_id=o.id AND r.consumer=:consumer
                )) ORDER BY id LIMIT :limit
            """),
                {"consumer": consumer, "limit": limit, "replay": replay, "after": after},
            ).all()
            for event in events:
                handler(connection, consumer, event.subject)
                self.hook("after_consumer_effect")
                connection.execute(
                    text("""
                    INSERT INTO consumer_receipts VALUES (:consumer, :event) ON CONFLICT DO NOTHING
                """),
                    {"consumer": consumer, "event": event.id},
                )
            self.hook("before_commit")
        self.hook("after_commit")
        return {"delivered": len(events), "cursor": int(events[-1].id) if events else after}

    def maintain(
        self, *, suppress: str | None = None, now: datetime | None = None
    ) -> dict[str, int]:
        timestamp = now or datetime.now(UTC)
        network = str(ip_network(suppress, strict=True)) if suppress else None
        with transaction(self.engine) as connection:
            if network:
                connection.execute(
                    text("""
                    INSERT INTO suppressions (network) VALUES (CAST(:network AS cidr))
                    ON CONFLICT DO NOTHING
                """),
                    {"network": network},
                )
            removed = (
                connection.execute(
                    text("""
                SELECT id, source_sha256, endpoint_key FROM observations
                WHERE expires_at <= :now OR EXISTS (
                    SELECT 1 FROM suppressions s WHERE observations.address <<= s.network)
            """),
                    {"now": timestamp},
                )
                .mappings()
                .all()
            )
            keys = {row["endpoint_key"] for row in removed}
            for key in keys:
                connection.execute(
                    text("DELETE FROM current_services WHERE endpoint_key=:key"), {"key": key}
                )
            for row in removed:
                connection.execute(
                    text("""
                    INSERT INTO tombstones VALUES (:id, :sha, :expires) ON CONFLICT DO NOTHING
                """),
                    {
                        "id": row["id"],
                        "sha": row["source_sha256"],
                        "expires": timestamp + timedelta(days=90),
                    },
                )
                # No payload-bearing dead letters; stale events can't resurrect deleted rows.
                connection.execute(text("DELETE FROM observations WHERE id=:id"), {"id": row["id"]})
                self._event(connection, row["id"], "removal")
            for key in keys:
                rebuild_current(connection, key)
            connection.execute(
                text("""
                DELETE FROM packs WHERE NOT EXISTS (
                    SELECT 1 FROM derivations WHERE pack_sha256=packs.sha256)
            """)
            )
            connection.execute(
                text("""
                DELETE FROM enrichment_datasets WHERE NOT EXISTS (
                    SELECT 1 FROM enrichments WHERE dataset_sha256=enrichment_datasets.sha256)
            """)
            )
            connection.execute(
                text("DELETE FROM tombstones WHERE expires_at <= :now"), {"now": timestamp}
            )
            connection.execute(
                text("""
                DELETE FROM outbox WHERE created_at <= :cutoff AND NOT EXISTS (
                    SELECT 1 FROM observations WHERE id=outbox.subject)
            """),
                {"cutoff": timestamp - timedelta(days=90)},
            )
            self.hook("before_commit")
        # Delete files only after history deletion commits. A crash here leaves recoverable orphans.
        self.hook("after_removal_commit")
        collected = self.collect()
        return {"removed": len(removed), "blobs_collected": collected}

    def collect(self) -> int:
        with transaction(self.engine) as connection:
            referenced: set[str] = set(
                connection.execute(text("SELECT DISTINCT blob_sha256 FROM evidence_refs")).scalars()
            )
            removed = self.blobs.collect(referenced)
            connection.execute(
                text("""
                DELETE FROM blobs WHERE NOT EXISTS (
                    SELECT 1 FROM evidence_refs WHERE blob_sha256=blobs.sha256)
            """)
            )
            return removed
