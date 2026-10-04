"""Labeled offline behavior, adversarial bounds, traceability and reprocessing."""

import base64
import json
import os
import socket
import subprocess
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from netatlas.config import Settings
from netatlas.derivations.engine import canonical, derive, digest
from netatlas.derivations.models import RulePack
from netatlas.derivations.offline import (
    INPUT_BYTES,
    LINE_BYTES,
    MAX_RECORDS,
    PACK_BYTES,
    OfflineError,
    apply_file,
    json_object,
    load_pack,
    read_observation,
    rows,
    validate_file,
)
from netatlas.examples import example_observation
from netatlas.observation import Observation, observation_reader

FIXTURES = Path(__file__).parent / "fixtures" / "fingerprints"
CORPUS = json.loads((FIXTURES / "corpus.json").read_text())["cases"]


def observation(raw: str | None, *, schema: int = 2, truncated: bool = False) -> Any:
    data = example_observation(Settings()).model_dump(mode="json")
    data["schema_version"] = schema
    data["service"] = None  # no service metadata needed; no port inference
    data["endpoint"]["port"] = 49152
    capture = (
        None
        if raw is None
        else {
            "body_base64": base64.b64encode(raw.encode("ascii")).decode(),
            "truncated": truncated,
        }
    )
    data["response"] = None
    if schema == 1:
        del data["protocol_evidence"]
        data["response"] = capture
    elif capture:
        data["protocol_evidence"] = {
            "exchanges": [
                {
                    "connection": 1,
                    "probe": "greeting-http",
                    "tcp_outcome": "open",
                    "status": "unknown",
                    "response": capture,
                }
            ],
            "received_bytes": len(raw or ""),
            "sent_bytes": 0,
            "retained_bytes": len(raw or ""),
            "termination": "finished",
        }
    return observation_reader.validate_python(data)


def pack_named(name: str) -> RulePack:
    return load_pack(FIXTURES / "synthetic-pack.json" if name == "synthetic" else None)


@pytest.mark.parametrize("case", CORPUS, ids=lambda case: case["name"])
def test_labeled_corpus(case: dict[str, Any]) -> None:
    obs = observation(case["raw"], schema=case["schema_version"], truncated=case["truncated"])
    before = canonical(obs)
    pack = pack_named(case["pack"])
    result = derive(obs, pack)
    assert sorted(c.rule_id for c in result.candidates) == sorted(case["expected_rules"])
    assert sorted({c.category for c in result.candidates if c.category is not None}) == sorted(
        case["expected_categories"]
    )
    assert set(case["expected_notes"]) <= set(result.notes)
    assert result.source_observation_id == obs.observation_id
    assert result.source_sha256 == digest(before)
    assert result == derive(obs, pack)
    assert canonical(obs) == before
    for candidate in result.candidates:
        rule = next(r for r in pack.rules if r.rule_id == candidate.rule_id)
        assert candidate.confidence == rule.confidence
        for ref in candidate.evidence:
            value = obs.model_dump(mode="json")
            for part in ref.pointer.split("/")[1:]:
                value = value[int(part)] if isinstance(value, list) else value[part]
            selected = base64.b64decode(value)[ref.start : ref.end]
            assert digest(selected) == ref.sha256
            assert selected.decode() == rule.conditions[ref.condition_index].value


def test_reprocessing_pack_identity_and_source_immutability() -> None:
    obs = observation("SSH-2.0-OpenSSH_0.0\r\n")
    pack = load_pack()
    original = derive(obs, pack)
    changed = pack.model_dump(mode="json")
    changed["version"] = "1.0.1"
    changed["rules"][2]["version"] = "1.0.1"
    changed["rules"][2]["conditions"][0]["value"] = "Other_"
    new = derive(obs, RulePack.model_validate(changed))
    assert new.product_state == "unknown"
    assert new.pack_sha256 != original.pack_sha256
    assert new.source_sha256 == original.source_sha256
    changed["version"] = "1.0.0"  # hash still exposes edits with an incorrectly reused version
    assert derive(obs, RulePack.model_validate(changed)).pack_sha256 != original.pack_sha256
    assert derive(obs, pack) == original


def test_metadata_port_tls_and_existing_derivations_are_not_fingerprint_inputs() -> None:
    obs = observation("HTTP/1.1 200 OK\r\nServer: Other\r\n\r\n")
    data = obs.model_dump(mode="json")
    data["endpoint"]["port"] = 22
    data["service"] = {
        "protocol": "ssh",
        "fingerprints": [
            {
                "rule_id": "forged",
                "rule_version": "1",
                "product": "OpenSSH",
                "confidence": 1.0,
            }
        ],
    }
    data["protocol_evidence"]["exchanges"][0]["http"] = {
        "version": "1.1",
        "status": 200,
        "headers": [["Server", "nginx"]],
        "headers_complete": True,
    }
    assert not derive(Observation.model_validate(data), load_pack()).candidates
    data = observation(None).model_dump(mode="json")
    data["protocol_evidence"] = {
        "exchanges": [
            {
                "connection": 1,
                "probe": "tls",
                "tcp_outcome": "open",
                "status": "complete",
                "tls": {
                    "version": "TLSv1.3",
                    "cipher": "fixture",
                    "secret_bits": 128,
                    "certificates": [],
                },
            }
        ],
        "received_bytes": 10,
        "retained_bytes": 0,
        "sent_bytes": 0,
        "termination": "finished",
    }
    assert derive(Observation.model_validate(data), load_pack()).category_state == "unknown"


def test_duplicate_headers_and_separate_exchanges_preserve_candidates() -> None:
    pack = pack_named("synthetic")
    first = observation(
        "HTTP/1.1 200 OK\r\nServer: Other\r\nServer: NetAtlasFixture/1\r\n\r\n[category=nas]"
    )
    assert derive(first, pack).candidates[0].category == "nas"
    data = first.model_dump(mode="json")
    second = observation(
        "HTTP/1.1 200 OK\r\nServer: NetAtlasFixture/1\r\n\r\n[category=camera_nvr]"
    )
    second_exchange = second.model_dump(mode="json")["protocol_evidence"]["exchanges"][0]
    second_exchange.update(connection=2, probe="tls")
    data["protocol_evidence"]["exchanges"].append(second_exchange)
    for key in ("received_bytes", "retained_bytes"):
        data["protocol_evidence"][key] += second.protocol_evidence.retained_bytes
    result = derive(Observation.model_validate(data), pack)
    assert result.category_state == "multiple"
    assert len({c.evidence[0].pointer for c in result.candidates}) == 2
    # The AND must never mix a Server field from one connection and body from another.
    data["protocol_evidence"]["exchanges"][0]["response"]["body_base64"] = base64.b64encode(
        b"HTTP/1.1 200 OK\r\nServer: NetAtlasFixture/1\r\n\r\n"
    ).decode()
    data["protocol_evidence"]["exchanges"][1]["response"]["body_base64"] = base64.b64encode(
        b"HTTP/1.1 200 OK\r\nServer: Other\r\n\r\n[category=nas]"
    ).decode()
    size = sum(
        len(base64.b64decode(e["response"]["body_base64"]))
        for e in data["protocol_evidence"]["exchanges"]
    )
    data["protocol_evidence"].update(received_bytes=size, retained_bytes=size)
    assert not derive(Observation.model_validate(data), pack).candidates


def test_product_and_category_independent_outputs_and_body_bounds() -> None:
    data = pack_named("synthetic").model_dump(mode="json")
    data["rules"] = data["rules"][:1]
    raw = "HTTP/1.1 200 OK\r\nServer: NetAtlasFixture/1\r\n\r\n[category=web_server]"
    data["rules"][0]["category"] = None
    result = derive(observation(raw), RulePack.model_validate(data))
    assert (result.product_state, result.category_state) == ("single", "unknown")
    data["rules"][0].update(product=None, category="web_server")
    result = derive(observation(raw), RulePack.model_validate(data))
    assert (result.product_state, result.category_state) == ("unknown", "single")
    raw = raw.replace("[category=", "x" * 8192 + "[category=")
    result = derive(observation(raw), pack_named("synthetic"))
    assert not result.candidates and "body_window_limited" in result.notes
    # Bytes after declared body length and body-forbidden status are not evidence.
    for prefix in ("HTTP/1.1 204 OK\r\n", "HTTP/1.1 200 OK\r\nContent-Length: 0\r\n"):
        raw = prefix + "Server: NetAtlasFixture/1\r\n\r\n[category=nas]"
        assert not derive(observation(raw), pack_named("synthetic")).candidates


@pytest.mark.parametrize(
    "patch",
    [
        {"operator": "regex"},
        {"selector": "endpoint.port"},
        {"value": ""},
        {"value": "x" * 513},
        {"value": "\x1b[31m"},
        {"code": "__import__('os')"},
    ],
)
def test_untrusted_conditions_rejected(patch: dict[str, str]) -> None:
    data = load_pack().model_dump(mode="json")
    data["rules"][0]["conditions"][0].update(patch)
    with pytest.raises(ValidationError):
        RulePack.model_validate(data)


def test_rule_pack_bounds_and_confidence_contract() -> None:
    base = load_pack().model_dump(mode="json")
    for mutation in ("duplicate", "count", "confidence", "category", "schema"):
        data = json.loads(json.dumps(base))
        if mutation == "duplicate":
            data["rules"].append(data["rules"][0])
        elif mutation == "count":
            data["rules"] *= 17
        elif mutation == "confidence":
            data["rules"][0]["confidence"] = "corroborated"
        elif mutation == "category":
            data["rules"][0]["category"] = "unknown"
        else:
            data["schema_version"] = 2
        with pytest.raises(ValidationError):
            RulePack.model_validate(data)


def test_offline_atomic_private_replay_and_no_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("offline path attempted networking")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    source = tmp_path / "source.jsonl"
    source.write_bytes(canonical(observation("SSH-2.0-OpenSSH_0.0\r\n")) + b"\n")
    before = source.read_bytes()
    output = Path("data/derived.jsonl")
    pack = load_pack()
    assert apply_file(source, output, pack)["records"] == 1
    assert output.stat().st_mode & 0o777 == 0o600
    assert output.parent.stat().st_mode & 0o777 == 0o700
    assert validate_file(source, output, pack)["records"] == 1
    second = Path("data/second.jsonl")
    apply_file(source, second, pack)
    assert output.read_bytes() == second.read_bytes()
    assert source.read_bytes() == before
    with pytest.raises(OfflineError):
        apply_file(source, output, pack)
    for key, value in (
        ("source_sha256", "0" * 64),
        ("pack_version", "9.0.0"),
        ("category_state", "unknown"),
    ):
        tampered = json.loads(second.read_bytes())
        tampered[key] = value
        second.write_text(json.dumps(tampered) + "\n")
        with pytest.raises(OfflineError):
            validate_file(source, second, pack)
        second.write_bytes(output.read_bytes())
    record = json.loads(output.read_bytes())
    record["candidates"][0]["evidence"][0]["start"] += 1
    second.write_text(json.dumps(record) + "\n")
    with pytest.raises(OfflineError):
        validate_file(source, second, pack)
    second.write_bytes(output.read_bytes() * 2)
    with pytest.raises(OfflineError):
        validate_file(source, second, pack)
    source.write_bytes(before + b'{"schema_version":2,"secret":"do-not-log"}\n')
    with pytest.raises(ValidationError):
        apply_file(source, Path("data/failed.jsonl"), pack)
    assert not Path("data/failed.jsonl").exists()
    assert not list(Path("data").glob(".fingerprints-*"))
    with pytest.raises(OfflineError):
        apply_file(source, tmp_path / "outside.jsonl", pack)
    Path("data/link.jsonl").symlink_to(source)
    with pytest.raises(OfflineError):
        apply_file(source, Path("data/link.jsonl"), pack)


def test_file_json_and_record_limits(tmp_path: Path) -> None:
    file = tmp_path / "input"
    for raw in (b"", b"\n", b"x" * (LINE_BYTES + 1), b"{}\n" * (MAX_RECORDS + 1)):
        file.write_bytes(raw)
        with pytest.raises(OfflineError):
            list(rows(file))
    with file.open("wb") as stream:
        stream.truncate(INPUT_BYTES + 1)
    with pytest.raises(OfflineError):
        list(rows(file))
    file.write_bytes(b"x" * (PACK_BYTES + 1))
    with pytest.raises(OfflineError):
        load_pack(file)
    for raw in (
        b'{"schema_version":1,"schema_version":2}',
        b"[" * 33 + b"]" * 33,
        b'{"schema_version":true}',
        b"{}",
    ):
        with pytest.raises(OfflineError):
            json_object(raw)
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    with pytest.raises(OfflineError):
        list(rows(fifo))
    link = tmp_path / "link"
    link.symlink_to(file)
    with pytest.raises(OSError):
        list(rows(link))
    for schema in (0, 3):
        data = observation(None).model_dump(mode="json") | {"schema_version": schema}
        with pytest.raises(ValidationError):
            read_observation(json.dumps(data).encode())


def test_cli_inspection_errors_and_replay(tmp_path: Path) -> None:
    result = subprocess.run(
        ["netatlas", "fingerprint", "--inspect"], capture_output=True, text=True, check=True
    )
    assert json.loads(result.stdout)["pack"]["pack_id"] == "netatlas-core"
    source = tmp_path / "observations.jsonl"
    source.write_bytes(canonical(observation("SSH-2.0-OpenSSH_0.0\r\n")) + b"\n")
    args = ["netatlas", "fingerprint", "--input", str(source)]
    result = subprocess.run(
        [*args, "--output", "data/cli.jsonl"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout)["records"] == 1
    subprocess.run(
        [*args, "--validate", "data/cli.jsonl"], cwd=tmp_path, capture_output=True, check=True
    )
    source.write_text('{"schema_version":2,"secret":"DO_NOT_LOG_RAW"}\n')
    result = subprocess.run(
        [*args, "--output", "data/failure.jsonl"], cwd=tmp_path, capture_output=True, text=True
    )
    assert result.returncode == 2 and "DO_NOT_LOG_RAW" not in result.stderr + result.stdout
    assert not (tmp_path / "data/failure.jsonl").exists()


def test_incomplete_body_cannot_prove_equality_or_word_end() -> None:
    data = pack_named("synthetic").model_dump(mode="json")
    data["rules"] = data["rules"][:1]
    data["rules"][0]["conditions"][1].update(value="marker", operator="equals")
    raw = "HTTP/1.1 200 OK\r\nServer: NetAtlasFixture/1\r\n\r\nmarker"
    for operator in ("equals", "word"):
        data["rules"][0]["conditions"][1]["operator"] = operator
        pack = RulePack.model_validate(data)
        assert derive(observation(raw), pack).candidates
        assert not derive(observation(raw, truncated=True), pack).candidates
        declared = raw.replace("Server:", "Content-Length: 100\r\nServer:")
        assert not derive(observation(declared), pack).candidates
    data["rules"][0]["conditions"][1]["operator"] = "contains"
    assert derive(observation(raw, truncated=True), RulePack.model_validate(data)).candidates


def test_v2_legacy_shaped_response_and_invalid_base64() -> None:
    data = observation("SSH-2.0-OpenSSH_0.0\r\n", schema=1).model_dump(mode="json")
    data["schema_version"] = 2
    assert derive(Observation.model_validate(data), load_pack()).product_state == "single"
    data["response"]["body_base64"] = "malformed!"
    with pytest.raises(ValidationError):
        read_observation(json.dumps(data).encode())
