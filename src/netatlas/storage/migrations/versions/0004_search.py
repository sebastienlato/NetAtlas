"""Search indexes over authoritative immutable rows; no asynchronous copies."""

from alembic import op

revision = "0004"
down_revision = "0003"


def upgrade() -> None:
    op.execute("""
    CREATE INDEX search_address ON observations USING gist (address inet_ops);
    CREATE INDEX search_port_time ON observations (port, finished_at DESC, id DESC);
    CREATE INDEX search_time ON observations (finished_at DESC, started_at DESC, id DESC);
    CREATE INDEX search_fingerprint ON derivations USING gin (document jsonb_path_ops);
    CREATE INDEX search_product_text ON derivations USING gin
        (to_tsvector('simple', jsonb_path_query_array(document, '$.candidates[*].product')::text));
    CREATE INDEX search_enrichment_choice ON enrichments
        (observation_id, dataset_sha256, engine_version, evaluated_at DESC, id DESC);
    CREATE INDEX search_enrichment_point ON enrichments USING gist (point);
    CREATE INDEX search_enrichment_fields ON enrichments USING gin (document jsonb_path_ops);
    CREATE INDEX search_enrichment_geometry ON enrichments USING gist ((point::geometry));
    """)


def downgrade() -> None:
    raise RuntimeError("Destructive downgrade unsupported; restore a tested backup")
