"""Explicit additive service accounts. Never rotate or replace owner credentials."""

import json
import os
import secrets
from pathlib import Path
from uuid import uuid4

from sqlalchemy import Engine, text

from netatlas.storage.database import private_directory, sync_directory, transaction

READ_TABLES = (
    "alembic_version",
    "observations",
    "evidence_refs",
    "blobs",
    "packs",
    "derivations",
    "current_services",
    "suppressions",
    "enrichment_datasets",
    "places",
    "enrichments",
    "outbox",
    "control_jobs",
    "control_attempts",
    "control_workers",
    "control_switch",
)
WRITE_GRANTS = {
    "observations": "INSERT",
    "evidence_refs": "INSERT",
    "blobs": "INSERT",
    "current_services": "INSERT, DELETE",
    "outbox": "INSERT",
    "control_workers": "INSERT, UPDATE",
    "control_jobs": "UPDATE",
    "control_attempts": "INSERT, UPDATE",
    "control_pacing": "INSERT, UPDATE",
}
CONTROL_READ = (*READ_TABLES, "control_campaigns", "control_pacing", "tombstones")


def private_file(path: Path, data: str) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    sync_directory(path.parent)


def provision_access(engine: Engine, destination: Path) -> None:
    """New generated roles and files; existing privileges/owner state are untouched.

    Files precede the DB transaction. A failure leaves private recovery files; no
    existing directory is overwritten or silently reused. Runbook covers recovery.
    """
    if destination.exists() or destination.is_symlink():
        raise ValueError("new service credential directory required")
    private_directory(destination)
    roles: list[tuple[str, str, str]] = []
    for kind in ("read", "control"):
        role, password = f"netatlas_{kind}_{uuid4().hex[:16]}", secrets.token_urlsafe(32)
        root = destination / kind
        private_directory(root)
        private_file(root / "postgres-password", password)
        private_file(
            root / "connection.json",
            json.dumps(
                {
                    "host": engine.url.host,
                    "port": engine.url.port,
                    "database": engine.url.database,
                    "username": role,
                }
            ),
        )
        roles.append((kind, role, password))
    with transaction(engine) as connection:
        # Existing PUBLIC CREATE is incompatible with a non-DDL service role. Fail
        # rather than revoking an owner's existing policy behind their back.
        if connection.execute(
            text("""SELECT EXISTS (
            SELECT 1 FROM pg_namespace n,
            aclexplode(coalesce(n.nspacl, acldefault('n',n.nspowner))) a
            WHERE n.nspname='public' AND a.grantee=0 AND a.privilege_type='CREATE')""")
        ).scalar_one():
            raise ValueError("public schema permits creation")
        for kind, role, password in roles:
            # Bind secrets as parameters, never interpolate them into SQL or exceptions.
            connection.execute(
                text(
                    "SELECT set_config('netatlas.new_role', :role, true), "
                    "set_config('netatlas.new_password', :password, true)"
                ),
                {"role": role, "password": password},
            )
            connection.execute(
                text("""DO $$ BEGIN
                EXECUTE format('CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE '
                  'NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 4 PASSWORD %L',
                  current_setting('netatlas.new_role'), current_setting('netatlas.new_password'));
                END $$""")
            )
            connection.execute(text(f'GRANT USAGE ON SCHEMA public TO "{role}"'))
            tables = READ_TABLES if kind == "read" else CONTROL_READ
            connection.execute(text(f'GRANT SELECT ON {", ".join(tables)} TO "{role}"'))
            if kind == "control":
                for table, privileges in WRITE_GRANTS.items():
                    connection.execute(text(f'GRANT {privileges} ON {table} TO "{role}"'))
                connection.execute(text(f'GRANT USAGE ON SEQUENCE outbox_id_seq TO "{role}"'))
            connection.execute(text(f"ALTER ROLE \"{role}\" SET statement_timeout = '60s'"))
            connection.execute(
                text(f"ALTER ROLE \"{role}\" SET idle_in_transaction_session_timeout = '15s'")
            )
            if kind == "read":
                connection.execute(
                    text(f'ALTER ROLE "{role}" SET default_transaction_read_only = on')
                )
    # Written only after commit. Uncertain outcomes need owner verification, never a reset.
    private_file(destination / "complete.json", '{"schema_version":1,"provisioned":true}\n')
