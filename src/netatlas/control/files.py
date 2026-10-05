"""Private credentials and a single fsynced worker slot; never part of Settings hashes."""

import fcntl
import os
import secrets
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import Field

from netatlas.control.models import BODY_BYTES, Deliver, Lease
from netatlas.derivations.offline import json_object, regular_file
from netatlas.domain import Model
from netatlas.storage.database import private_directory, sync_directory


class Credential(Model):
    schema_version: int = Field(default=1, ge=1, le=1, strict=True)
    worker_id: UUID
    token: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$", repr=False)


class Credentials(Model):
    schema_version: int = Field(default=1, ge=1, le=1, strict=True)
    workers: tuple[Credential, ...] = Field(min_length=2, max_length=2)


class Boot(Model):
    schema_version: int = Field(default=1, ge=1, le=1, strict=True)
    generation: int = Field(ge=1, le=2147483647, strict=True)
    session_id: UUID
    worker_id: UUID


class Pending(Model):
    schema_version: int = Field(default=1, ge=1, le=1, strict=True)
    lease: Lease
    delivery: Deliver | None = None


def read_private(path: Path, limit: int = BODY_BYTES) -> bytes:
    with regular_file(path) as stream:
        if os.fstat(stream.fileno()).st_mode & 0o077:
            raise ValueError("private file required")
        data = stream.read(limit + 1)
        if len(data) > limit:
            raise ValueError("file bound")
        return data


def publish(path: Path, data: bytes) -> None:
    if len(data) > BODY_BYTES:
        raise ValueError("spool bound")
    temporary = path.with_suffix(".stage")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("regular file required")
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    sync_directory(path.parent)


def provision(root: Path) -> None:
    private_directory(root)
    if any(root.iterdir()):
        raise ValueError("new empty credential directory required; never replace credentials")
    credentials = Credentials(
        workers=tuple(
            Credential(worker_id=uuid4(), token=secrets.token_urlsafe(32)) for _ in range(2)
        )
    )
    publish(root / "coordinator.json", credentials.model_dump_json().encode())
    for index, credential in enumerate(credentials.workers, 1):
        publish(root / f"worker-{index}.json", credential.model_dump_json().encode())


class Spool:
    def __init__(self, root: Path):
        self.root = root
        private_directory(root)

    @contextmanager
    def lock(self) -> Iterator[None]:
        fd = os.open(self.root / ".lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Atomic staging files contain at most one previous interrupted write.
            # The committed pending slot is authoritative; never replay a partial stage.
            for name in ("pending.stage", "boot.stage"):
                (self.root / name).unlink(missing_ok=True)
            sync_directory(self.root)
            yield
        finally:
            os.close(fd)

    def boot(self, worker: UUID) -> Boot:
        path = self.root / "boot.json"
        previous = (
            Boot.model_validate(json_object(read_private(path, 4096))) if path.exists() else None
        )
        if previous and previous.worker_id != worker:
            raise ValueError("spool worker mismatch")
        boot = Boot(
            worker_id=worker,
            session_id=uuid4(),
            generation=previous.generation + 1 if previous else 1,
        )
        publish(path, boot.model_dump_json().encode())
        return boot

    def pending(self) -> Pending | None:
        path = self.root / "pending.json"
        return Pending.model_validate(json_object(read_private(path))) if path.exists() else None

    def save(self, pending: Pending) -> None:
        publish(self.root / "pending.json", pending.model_dump_json().encode())

    def clear(self) -> None:
        (self.root / "pending.json").unlink(missing_ok=True)
        sync_directory(self.root)
