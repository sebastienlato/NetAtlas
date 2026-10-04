"""Backfill bounded evidence lifetime; durable suppression and replay tombstones."""

from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade() -> None:
    op.execute("""
    ALTER TABLE observations DISABLE TRIGGER immutable_observation;
    ALTER TABLE observations ADD COLUMN expires_at timestamptz;
    UPDATE observations SET expires_at = finished_at + interval '30 days';
    ALTER TABLE observations ALTER COLUMN expires_at SET NOT NULL;
    ALTER TABLE observations ADD CHECK (
        expires_at > finished_at AND expires_at <= finished_at + interval '30 days'
    );
    ALTER TABLE observations ENABLE TRIGGER immutable_observation;
    CREATE INDEX observation_expiry ON observations (expires_at);
    CREATE TABLE suppressions (
        network cidr PRIMARY KEY,
        created_at timestamptz NOT NULL DEFAULT clock_timestamp()
    );
    CREATE TABLE tombstones (
        id uuid PRIMARY KEY,
        source_sha256 text NOT NULL,
        expires_at timestamptz NOT NULL
    );
    """)


def downgrade() -> None:
    raise RuntimeError("Destructive downgrade unsupported; restore a tested backup")
