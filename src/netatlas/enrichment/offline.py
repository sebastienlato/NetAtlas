"""Checksum-pinned bounded local datasets and private no-clobber enrichment output."""

import os
import tempfile
from datetime import datetime
from pathlib import Path

from netatlas.derivations.engine import canonical, digest
from netatlas.derivations.offline import (
    OUTPUT_BYTES,
    json_object,
    read_observation,
    regular_file,
    rows,
)
from netatlas.enrichment.engine import enrich
from netatlas.enrichment.models import Dataset

DATASET_BYTES = 2097152


def load_dataset(path: Path, expected_sha256: str) -> Dataset:
    with regular_file(path) as stream:
        data = stream.read(DATASET_BYTES + 1)
    if len(data) > DATASET_BYTES or digest(data) != expected_sha256:
        raise ValueError("dataset size or checksum failure")
    return Dataset.model_validate(json_object(data))


def publish(output: Path, data: bytes) -> None:
    root = Path.cwd() / "data"
    if root.is_symlink() or not output.absolute().parent.resolve().is_relative_to(root.resolve()):
        raise ValueError("output must be under ignored data")
    root.mkdir(mode=0o700, exist_ok=True)
    fd, stage = tempfile.mkstemp(prefix=".enrichment-", dir=output.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(stage, output)
    finally:
        os.unlink(stage)


def apply_file(source: Path, output: Path, dataset: Dataset, at: datetime) -> dict[str, object]:
    # The existing reader caps input at 1024 rows/16 MiB. Bound output independently.
    result = bytearray()
    count = 0
    for row in rows(source):
        result.extend(canonical(enrich(read_observation(row), dataset, at)) + b"\n")
        if len(result) > OUTPUT_BYTES:
            raise ValueError("enrichment output limit")
        count += 1
    publish(output, bytes(result))
    return {"records": count, "dataset_sha256": digest(canonical(dataset))}
