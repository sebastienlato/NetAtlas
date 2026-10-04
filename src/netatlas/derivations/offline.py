"""Bounded local-file boundary and private atomic outputs; never performs network I/O."""

import json
import os
import stat
import tempfile
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from importlib.resources import files
from pathlib import Path
from typing import BinaryIO, cast

from netatlas.derivations.engine import canonical, derive, digest
from netatlas.derivations.models import Derivation, RulePack
from netatlas.domain import ObservationV1
from netatlas.observation import Observation, observation_reader

PACK_BYTES = 131072
LINE_BYTES = 1048576
INPUT_BYTES = 16777216
OUTPUT_BYTES = 33554432
MAX_RECORDS = 1024


class OfflineError(ValueError):
    """Stable errors deliberately omit paths, raw data and validation details."""


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise OfflineError("duplicate JSON key")
        result[key] = value
    return result


def json_object(data: bytes) -> dict[str, object]:
    # Bound nesting before the general JSON parser; ignore brackets in strings.
    depth = 0
    quoted = escaped = False
    for byte in data:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
        elif byte == 34:
            quoted = True
        elif byte in (91, 123):
            depth += 1
            if depth > 32:
                raise OfflineError("JSON nesting limit")
        elif byte in (93, 125):
            depth -= 1
    value = json.loads(data, object_pairs_hook=unique_object)
    if not isinstance(value, dict) or type(value.get("schema_version")) is not int:
        raise OfflineError("explicit integer schema version required")
    return cast(dict[str, object], value)


@contextmanager
def regular_file(path: Path) -> Iterator[BinaryIO]:
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OfflineError("regular files required")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            yield stream
    finally:
        os.close(fd)


def load_pack(path: Path | None = None) -> RulePack:
    if path is None:
        data = files("netatlas.derivations").joinpath("core.json").read_bytes()
    else:
        with regular_file(path) as stream:
            data = stream.read(PACK_BYTES + 1)
    if len(data) > PACK_BYTES:
        raise OfflineError("rule pack size limit")
    return RulePack.model_validate(json_object(data))


def rows(path: Path, *, total_limit: int = INPUT_BYTES) -> Generator[bytes]:
    with regular_file(path) as stream:
        if os.fstat(stream.fileno()).st_size > total_limit:
            raise OfflineError("file size limit")
        total = count = 0
        while line := stream.readline(LINE_BYTES + 1):
            total += len(line)
            count += 1
            if len(line) > LINE_BYTES or total > total_limit or count > MAX_RECORDS:
                raise OfflineError("JSONL resource limit")
            if not line.strip():
                raise OfflineError("blank JSONL row")
            yield line
        if count == 0:
            raise OfflineError("empty JSONL input")


def read_observation(line: bytes) -> ObservationV1 | Observation:
    return observation_reader.validate_python(json_object(line))


def apply_file(source: Path, output: Path, pack: RulePack) -> dict[str, object]:
    root = Path.cwd() / "data"
    if root.is_symlink():
        raise OfflineError("data directory must not be a symlink")
    root = root.resolve()
    # Output is private and ignored; final-component symlinks also fail no-clobber publication.
    destination = output.absolute()
    if not destination.parent.resolve().is_relative_to(root):
        raise OfflineError("output must be under data")
    if destination.exists() or destination.is_symlink():
        raise OfflineError("output already exists")
    root.mkdir(mode=0o700, exist_ok=True)
    if not destination.parent.is_dir():
        raise OfflineError("output parent must exist")
    fd, temporary = tempfile.mkstemp(prefix=".fingerprints-", dir=destination.parent)
    count = total = 0
    try:
        with os.fdopen(fd, "wb") as stream:
            for line in rows(source):
                record = derive(read_observation(line), pack)
                encoded = canonical(record) + b"\n"
                total += len(encoded)
                if total > OUTPUT_BYTES:
                    raise OfflineError("derived output size limit")
                stream.write(encoded)
                count += 1
            stream.flush()
            os.fsync(stream.fileno())
        # Atomic no-overwrite publication, even if another process creates destination.
        os.link(temporary, destination)
    finally:
        os.unlink(temporary)
    return {"valid": True, "records": count, "pack_sha256": digest(canonical(pack))}


def validate_file(source: Path, derived: Path, pack: RulePack) -> dict[str, object]:
    outputs = rows(derived, total_limit=OUTPUT_BYTES)
    count = 0
    try:
        for line in rows(source):
            expected = derive(read_observation(line), pack)
            actual_line = next(outputs, None)
            if actual_line is None:
                raise OfflineError("derived row count mismatch")
            actual = Derivation.model_validate(json_object(actual_line))
            if actual != expected:
                raise OfflineError("derived record differs from replay")
            count += 1
        if next(outputs, None) is not None:
            raise OfflineError("derived row count mismatch")
    finally:
        outputs.close()
    return {"valid": True, "records": count, "pack_sha256": digest(canonical(pack))}
