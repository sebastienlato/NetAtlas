"""Private append-only JSONL and atomic campaign manifests in the local spool."""

import fcntl
import hashlib
import json
import os
import platform
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import IO
from uuid import UUID

from netatlas import __version__
from netatlas.config import Settings
from netatlas.discovery.policy import POLICY_SHA256, POLICY_VERSION, REGISTRY_VERSION
from netatlas.discovery.scope import Scope
from netatlas.domain import Observation


class Spool:
    def __init__(self, root: Path, campaign_id: UUID, settings: Settings, scope: Scope) -> None:
        self.root = root
        self.directory = root / str(campaign_id)
        self.digest = hashlib.sha256()
        self.counts: Counter[str] = Counter()
        self.completed = 0
        self.file: IO[bytes] | None = None
        self.lock: IO[bytes] | None = None
        self.manifest: dict[str, object] = {
            "manifest_version": 1,
            "observation_schema_version": 1,
            "campaign_id": str(campaign_id),
            "scanner": {"node_id": settings.measurement.node_id, "software_version": __version__},
            "python_version": platform.python_version(),
            "config_version": settings.config_version,
            "config_sha256": settings.sha256,
            "effective_config": settings.model_dump(mode="json"),
            "policy_version": POLICY_VERSION,
            "policy_sha256": POLICY_SHA256,
            "registry_version": REGISTRY_VERSION,
            "seed": scope.seed,
            "lab_loopback": scope.lab_loopback,
            "preview": scope.preview(settings.measurement),
            "started_at": datetime.now(UTC).isoformat(),
            "status": "running",
        }

    def __enter__(self) -> Spool:
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.lock = (self.root / ".discovery.lock").open("a+b")
        try:
            os.chmod(self.root / ".discovery.lock", 0o600)
            # Never let two local campaigns silently multiply this spool's budget.
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.directory.mkdir(mode=0o700)
            self.file = (self.directory / "observations.jsonl").open("xb")
            os.chmod(self.directory / "observations.jsonl", 0o600)
            self.write_manifest()
        except BaseException:
            if self.file is not None:
                self.file.close()
            self.lock.close()
            raise
        return self

    def append(self, observation: Observation) -> None:
        assert self.file is not None
        line = (observation.model_dump_json() + "\n").encode()
        self.file.write(line)
        self.file.flush()
        self.digest.update(line)
        self.counts[observation.outcome.value] += 1
        self.completed += 1

    def finish(self, status: str, attempted: int) -> None:
        assert self.file is not None
        self.file.flush()
        os.fsync(self.file.fileno())
        self.manifest.update(
            status=status,
            finished_at=datetime.now(UTC).isoformat(),
            attempted=attempted,
            completed=self.completed,
            incomplete=attempted - self.completed,
            outcomes=dict(sorted(self.counts.items())),
            observations_sha256=self.digest.hexdigest(),
        )
        self.write_manifest()

    def write_manifest(self) -> None:
        temporary = self.directory / "manifest.tmp"
        with temporary.open("w", encoding="utf-8") as file:
            os.chmod(temporary, 0o600)
            json.dump(self.manifest, file, sort_keys=True, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        temporary.replace(self.directory / "manifest.json")

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            if self.file is not None:
                self.file.close()
        finally:
            if self.lock is not None:
                self.lock.close()
