"""Add independent enrichment history and WGS84 gazetteer; never rewrite sources."""

from alembic import op

revision = "0003"
down_revision = "0002"


def upgrade() -> None:
    op.execute("""
    CREATE EXTENSION IF NOT EXISTS postgis;
    CREATE TABLE enrichment_datasets (
        sha256 text PRIMARY KEY CHECK (sha256 ~ '^[0-9a-f]{64}$'),
        document jsonb NOT NULL
    );
    CREATE TABLE places (
        dataset_sha256 text NOT NULL REFERENCES enrichment_datasets ON DELETE CASCADE,
        id text NOT NULL,
        name text NOT NULL,
        country_code text NOT NULL,
        admin_code text,
        point geography(Point, 4326),
        boundary geometry(MultiPolygon, 4326),
        document jsonb NOT NULL,
        PRIMARY KEY (dataset_sha256, id),
        CHECK (boundary IS NULL OR (ST_IsValid(boundary, 0) AND NOT ST_IsEmpty(boundary)))
    );
    CREATE TABLE enrichments (
        id text PRIMARY KEY CHECK (id ~ '^[0-9a-f]{64}$'),
        observation_id uuid NOT NULL REFERENCES observations ON DELETE CASCADE,
        source_sha256 text NOT NULL,
        dataset_sha256 text NOT NULL REFERENCES enrichment_datasets,
        engine_version text NOT NULL,
        evaluated_at timestamptz NOT NULL,
        place_id text,
        point geography(Point, 4326),
        document jsonb NOT NULL,
        created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
        FOREIGN KEY (dataset_sha256, place_id) REFERENCES places (dataset_sha256, id),
        UNIQUE (observation_id, source_sha256, dataset_sha256, engine_version, evaluated_at)
    );
    CREATE INDEX enrichment_source ON enrichments (observation_id);
    CREATE INDEX enrichment_dataset ON enrichments (dataset_sha256);
    CREATE TRIGGER immutable_enrichment_dataset BEFORE UPDATE ON enrichment_datasets
        FOR EACH ROW EXECUTE FUNCTION reject_history_update();
    CREATE TRIGGER immutable_place BEFORE UPDATE ON places
        FOR EACH ROW EXECUTE FUNCTION reject_history_update();
    CREATE TRIGGER immutable_enrichment BEFORE UPDATE ON enrichments
        FOR EACH ROW EXECUTE FUNCTION reject_history_update();
    """)


def downgrade() -> None:
    raise RuntimeError("Destructive downgrade unsupported; restore a tested backup")
