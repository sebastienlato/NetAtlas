"""Bounded local worker identities, fenced attempts and durable connection pacing."""

from alembic import op

revision = "0005"
down_revision = "0004"


def upgrade() -> None:
    op.execute("""
    CREATE TABLE control_workers (
        id uuid PRIMARY KEY, session_id uuid NOT NULL, generation integer NOT NULL,
        heartbeat_at timestamptz NOT NULL
    );
    CREATE TABLE control_campaigns (
        id uuid PRIMARY KEY, document jsonb NOT NULL, config_sha256 text NOT NULL,
        policy_sha256 text NOT NULL, created_at timestamptz NOT NULL,
        deadline timestamptz NOT NULL, cancelled boolean NOT NULL DEFAULT false
    );
    CREATE TABLE control_jobs (
        id uuid PRIMARY KEY, campaign_id uuid NOT NULL REFERENCES control_campaigns(id),
        address inet NOT NULL, port integer NOT NULL CHECK (port BETWEEN 1 AND 65535),
        state text NOT NULL CHECK (state IN
            ('queued','leased','measuring','uncertain','delivered','cancelled','failed')),
        fence integer NOT NULL DEFAULT 0 CHECK (fence BETWEEN 0 AND 3),
        UNIQUE (campaign_id, address, port)
    );
    CREATE TABLE control_attempts (
        id uuid PRIMARY KEY, job_id uuid NOT NULL REFERENCES control_jobs(id) ON DELETE CASCADE,
        fence integer NOT NULL CHECK (fence BETWEEN 1 AND 3),
        observation_id uuid NOT NULL UNIQUE,
        worker_id uuid NOT NULL REFERENCES control_workers(id), session_id uuid NOT NULL,
        delivery_session uuid NOT NULL, lease_until timestamptz NOT NULL,
        claimed_at timestamptz NOT NULL, started_at timestamptz,
        hard_until timestamptz, delivery_until timestamptz NOT NULL,
        connections integer NOT NULL DEFAULT 0 CHECK (connections BETWEEN 0 AND 2),
        source_sha256 text, UNIQUE (job_id, fence)
    );
    CREATE INDEX control_queue ON control_jobs (state, campaign_id);
    CREATE INDEX control_attempt_owner ON control_attempts (worker_id, session_id);
    CREATE TABLE control_pacing (
        key text PRIMARY KEY, next_at timestamptz NOT NULL, last_at timestamptz NOT NULL
    );
    """)


def downgrade() -> None:
    raise RuntimeError("Destructive downgrade unsupported; restore a tested backup")
