"""Explicit private local connection settings and serialized durable transactions."""

import json
import os
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import URL, Connection, Engine, create_engine, text

# One local pipeline lock, including filesystem publication and maintenance.
LOCK_ID = 0x4E455441544C4153


def sync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def private_directory(path: Path) -> None:
    if path.is_symlink():
        raise ValueError("private directory required")
    if not path.exists():
        if not path.parent.exists():
            private_directory(path.parent)
        path.mkdir(mode=0o700, exist_ok=True)
        sync_directory(path.parent)
    if path.stat().st_mode & 0o077:
        raise ValueError("private directory permissions required")


def initialize_local(root: Path) -> None:
    private_directory(root)
    path = root / "postgres-password"
    if not path.exists():
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(secrets.token_urlsafe(32))
            stream.flush()
            os.fsync(stream.fileno())
    settings = root / "connection.json"
    if not settings.exists():
        fd = os.open(settings, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump({"host": "127.0.0.1", "port": 55432, "database": "netatlas"}, stream)
            stream.flush()
            os.fsync(stream.fileno())

    sync_directory(root)
    validate_settings_files(root)


def validate_settings_files(root: Path) -> None:
    for path in (root / "connection.json", root / "postgres-password"):
        if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
            raise ValueError("private regular settings required")


def local_engine(root: Path) -> Engine:
    validate_settings_files(root)
    settings = json.loads((root / "connection.json").read_text())
    if settings["host"] not in ("127.0.0.1", "::1"):
        raise ValueError("local storage only")
    url = URL.create(
        "postgresql+psycopg",
        username="postgres",
        password=(root / "postgres-password").read_text(),
        host=settings["host"],
        port=settings["port"],
        database=settings["database"],
    )
    return create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 5})


@contextmanager
def transaction(engine: Engine) -> Iterator[Connection]:
    with engine.begin() as connection:
        connection.execute(text("SET LOCAL synchronous_commit = on"))
        connection.execute(text("SET LOCAL lock_timeout = '10s'"))
        connection.execute(text("SET LOCAL statement_timeout = '60s'"))
        connection.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": LOCK_ID})
        yield connection


def migrate(engine: Engine, revision: str = "head") -> None:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    with transaction(engine) as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, revision)
