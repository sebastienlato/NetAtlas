"""Private local SHA-256 blobs, fsynced before any referring database commit."""

import hashlib
import os
import re
import stat
import tempfile
from pathlib import Path

from netatlas.storage.database import private_directory, require_capacity, sync_directory

DIGEST = re.compile(r"[0-9a-f]{64}")


class BlobStore:
    def __init__(self, root: Path, *, create: bool = True):
        self.root = root
        if create:
            private_directory(root)
        else:
            info = root.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o077:
                raise ValueError("existing private blob directory required")

    def read(self, sha256: str) -> bytes:
        if not DIGEST.fullmatch(sha256):
            raise ValueError("invalid blob identity")
        fd = os.open(self.root / sha256, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_size > 65536:
                raise ValueError("invalid private blob")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                data = stream.read(65537)
        finally:
            os.close(fd)
        if hashlib.sha256(data).hexdigest() != sha256 or len(data) > 65536:
            raise ValueError("blob integrity failure")
        return data

    def put(self, data: bytes) -> str:
        if len(data) > 65536:
            raise ValueError("blob size limit")
        sha256 = hashlib.sha256(data).hexdigest()
        destination = self.root / sha256
        if destination.exists() or destination.is_symlink():
            if self.read(sha256) != data:
                raise ValueError("blob conflict")
            # A prior writer may have crashed after link but before directory fsync.
            sync_directory(self.root)
            return sha256
        require_capacity(self.root, len(data))
        fd, temporary = tempfile.mkstemp(prefix=".stage-", dir=self.root)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.link(temporary, destination)
            sync_directory(self.root)
        finally:
            os.unlink(temporary)
        return sha256

    def collect(self, referenced: set[str]) -> int:
        """Caller must hold the pipeline DB lock, including during directory fsync."""
        count = 0
        for path in self.root.iterdir():
            if path.name.startswith(".stage-") or (
                DIGEST.fullmatch(path.name) and path.name not in referenced
            ):
                path.unlink()
                count += 1
        sync_directory(self.root)
        return count
