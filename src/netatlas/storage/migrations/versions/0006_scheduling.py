"""Schedule provenance, deterministic queue order and durable operator stop switch."""

from alembic import op

revision = "0006"
down_revision = "0005"


def upgrade() -> None:
    op.execute("""
    ALTER TABLE control_campaigns ADD COLUMN schedule_sha256 text UNIQUE;
    ALTER TABLE control_campaigns ADD COLUMN schedule_document jsonb;
    ALTER TABLE control_jobs ADD COLUMN position integer NOT NULL DEFAULT 0;
    ALTER TABLE control_jobs ADD COLUMN refresh_source_id uuid;
    ALTER TABLE control_jobs ADD COLUMN refresh_source_sha256 text;
    CREATE TABLE control_switch (
        singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
        stopped boolean NOT NULL DEFAULT false,
        generation bigint NOT NULL DEFAULT 0,
        changed_at timestamptz NOT NULL DEFAULT clock_timestamp()
    );
    INSERT INTO control_switch (singleton) VALUES (true);
    """)


def downgrade() -> None:
    raise RuntimeError("Destructive downgrade unsupported; restore a tested backup")
