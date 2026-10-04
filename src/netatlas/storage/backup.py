"""Consistent local database/blob backup and restore to an explicitly empty database."""

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from sqlalchemy import Connection, Engine, text

from netatlas.storage.blobs import BlobStore
from netatlas.storage.database import migrate, private_directory, sync_directory, transaction
from netatlas.storage.pipeline import Pipeline


def file_digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def compose_command() -> list[str]:
    # Homebrew also supplies the standalone Compose executable.
    if shutil.which("docker-compose"):
        return ["docker-compose", "exec", "-T", "db"]
    return ["docker", "compose", "exec", "-T", "db"]


def verify_compose_server(engine: Engine, connection: Connection) -> None:
    """Do not mix a custom local DB connection with a different Compose server."""
    expected = str(
        connection.execute(text("SELECT system_identifier FROM pg_control_system()")).scalar_one()
    )
    result = subprocess.run(
        [
            *compose_command(),
            "psql",
            "--username=postgres",
            "--dbname",
            str(engine.url.database),
            "--no-align",
            "--tuples-only",
            "--command",
            "SELECT system_identifier FROM pg_control_system()",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    if result.stdout.strip() != expected:
        raise ValueError("Compose database does not match connection")


def backup(engine: Engine, blobs: BlobStore, destination: Path) -> None:
    if destination.exists() or destination.is_symlink():
        raise ValueError("new backup directory required")
    private_directory(destination.parent)
    stage = Path(tempfile.mkdtemp(prefix=".backup-", dir=destination.parent))
    try:
        copied = BlobStore(stage / "blobs")
        with transaction(engine) as connection:
            verify_compose_server(engine, connection)
            referenced: set[str] = set(
                connection.execute(text("SELECT DISTINCT blob_sha256 FROM evidence_refs")).scalars()
            )
            for sha in sorted(referenced):
                copied.put(blobs.read(sha))
            archive = stage / "database.dump"
            fd = os.open(archive, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as stream:
                subprocess.run(
                    [
                        *compose_command(),
                        "pg_dump",
                        "--format=custom",
                        "--no-owner",
                        "--username=postgres",
                        "--dbname",
                        str(engine.url.database),
                    ],
                    stdout=stream,
                    stderr=subprocess.PIPE,
                    check=True,
                    timeout=120,
                )
                stream.flush()
                os.fsync(stream.fileno())
            manifest = stage / "manifest.json"
            fd = os.open(manifest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as stream:
                json.dump(
                    {
                        "version": 1,
                        "database_sha256": file_digest(archive),
                        "blobs": sorted(referenced),
                    },
                    stream,
                )
                stream.flush()
                os.fsync(stream.fileno())
            sync_directory(stage)
            os.rename(stage, destination)
            sync_directory(destination.parent)
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def restore(engine: Engine, blobs: BlobStore, source: Path) -> dict[str, int]:
    """Trusted operator backups only; SQL archives are executable, never upload inputs."""
    manifest = json.loads((source / "manifest.json").read_text())
    if (
        manifest["version"] != 1
        or file_digest(source / "database.dump") != manifest["database_sha256"]
    ):
        raise ValueError("backup integrity failure")
    saved_blobs = BlobStore(source / "blobs")
    with transaction(engine) as connection:
        verify_compose_server(engine, connection)
        if connection.execute(
            text("""
            SELECT count(*) FROM information_schema.tables WHERE table_schema='public'
        """)
        ).scalar_one():
            raise ValueError("restore requires an empty database")
        for sha in manifest["blobs"]:
            blobs.put(saved_blobs.read(sha))
        with (source / "database.dump").open("rb") as stream:
            subprocess.run(
                [
                    *compose_command(),
                    "pg_restore",
                    "--single-transaction",
                    "--exit-on-error",
                    "--no-owner",
                    "--username=postgres",
                    "--dbname",
                    str(engine.url.database),
                ],
                stdin=stream,
                capture_output=True,
                check=True,
                timeout=120,
            )
    migrate(engine)  # Older Phase 4 archives gain spatial tables without rewriting sources.
    pipeline = Pipeline(engine, blobs)
    # Expired evidence is not made readable on restoration. Reapply any newer opt-outs
    # from the operator's separate suppression register before other use.
    pipeline.maintain()
    return pipeline.verify()
