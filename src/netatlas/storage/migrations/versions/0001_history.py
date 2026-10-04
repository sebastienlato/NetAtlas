"""Initial immutable history, references, projections and transactional delivery."""

from alembic import op

revision = "0001"
down_revision = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE blobs (
        sha256 text PRIMARY KEY CHECK (sha256 ~ '^[0-9a-f]{64}$'),
        size integer NOT NULL CHECK (size BETWEEN 0 AND 65536)
    );
    CREATE TABLE observations (
        id uuid PRIMARY KEY,
        source_sha256 text NOT NULL CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),
        schema_version smallint NOT NULL CHECK (schema_version IN (1, 2)),
        endpoint_key text NOT NULL,
        address inet NOT NULL,
        transport text NOT NULL CHECK (transport IN ('tcp', 'udp')),
        port integer NOT NULL CHECK (port BETWEEN 1 AND 65535),
        started_at timestamptz NOT NULL,
        finished_at timestamptz NOT NULL CHECK (finished_at >= started_at),
        outcome text NOT NULL CHECK (outcome IN ('open', 'closed', 'timeout', 'error')),
        has_evidence boolean NOT NULL,
        document jsonb NOT NULL,
        ingested_at timestamptz NOT NULL DEFAULT clock_timestamp()
    );
    CREATE INDEX observation_endpoint_order ON observations
        (endpoint_key, finished_at DESC, started_at DESC, id DESC);
    CREATE TABLE evidence_refs (
        observation_id uuid NOT NULL REFERENCES observations ON DELETE CASCADE,
        pointer text NOT NULL,
        blob_sha256 text NOT NULL REFERENCES blobs,
        PRIMARY KEY (observation_id, pointer)
    );
    CREATE INDEX evidence_blob ON evidence_refs (blob_sha256);
    CREATE TABLE packs (
        sha256 text PRIMARY KEY CHECK (sha256 ~ '^[0-9a-f]{64}$'),
        document jsonb NOT NULL
    );
    CREATE TABLE derivations (
        id text PRIMARY KEY CHECK (id ~ '^[0-9a-f]{64}$'),
        observation_id uuid NOT NULL REFERENCES observations ON DELETE CASCADE,
        source_sha256 text NOT NULL,
        pack_sha256 text NOT NULL REFERENCES packs,
        engine_version text NOT NULL,
        taxonomy_version text NOT NULL,
        schema_version smallint NOT NULL,
        document jsonb NOT NULL,
        created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
        UNIQUE (observation_id, source_sha256, pack_sha256, engine_version, taxonomy_version)
    );
    CREATE TABLE current_services (
        endpoint_key text PRIMARY KEY,
        last_attempt uuid NOT NULL REFERENCES observations,
        last_open uuid REFERENCES observations,
        last_evidence uuid REFERENCES observations
    );
    CREATE TABLE outbox (
        id bigserial PRIMARY KEY,
        subject uuid NOT NULL,
        kind text NOT NULL CHECK (kind IN ('observation', 'derivation', 'removal')),
        created_at timestamptz NOT NULL DEFAULT clock_timestamp()
    );
    CREATE INDEX outbox_subject ON outbox (subject);
    CREATE TABLE consumer_receipts (
        consumer text NOT NULL,
        event_id bigint NOT NULL REFERENCES outbox ON DELETE CASCADE,
        PRIMARY KEY (consumer, event_id)
    );
    CREATE TABLE consumer_observations (
        consumer text NOT NULL,
        observation_id uuid NOT NULL REFERENCES observations ON DELETE CASCADE,
        source_sha256 text NOT NULL,
        PRIMARY KEY (consumer, observation_id)
    );
    CREATE FUNCTION reject_history_update() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'immutable history'; END $$;
    CREATE TRIGGER immutable_observation BEFORE UPDATE ON observations
        FOR EACH ROW EXECUTE FUNCTION reject_history_update();
    CREATE TRIGGER immutable_evidence BEFORE UPDATE ON evidence_refs
        FOR EACH ROW EXECUTE FUNCTION reject_history_update();
    CREATE TRIGGER immutable_blob BEFORE UPDATE ON blobs
        FOR EACH ROW EXECUTE FUNCTION reject_history_update();
    CREATE TRIGGER immutable_pack BEFORE UPDATE ON packs
        FOR EACH ROW EXECUTE FUNCTION reject_history_update();
    CREATE TRIGGER immutable_derivation BEFORE UPDATE ON derivations
        FOR EACH ROW EXECUTE FUNCTION reject_history_update();
    """)


def downgrade() -> None:
    raise RuntimeError("Destructive downgrade unsupported; restore a tested backup")
