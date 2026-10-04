"""Synthetic offline enrichment truth, provenance, uncertainty and file-boundary tests."""

import json
import socket
import subprocess
from datetime import UTC, datetime, timedelta
from ipaddress import ip_address
from pathlib import Path
from typing import Any

import pytest

from netatlas.config import Settings
from netatlas.derivations.engine import canonical, digest
from netatlas.enrichment.engine import enrich, longest_prefix, places_named
from netatlas.enrichment.geometry import bounding_boundary
from netatlas.enrichment.models import Dataset, Enrichment
from netatlas.enrichment.offline import DATASET_BYTES, apply_file, load_dataset
from netatlas.examples import example_observation
from netatlas.observation import Observation, observation_reader

FIXTURE = Path("tests/fixtures/enrichment/synthetic.json")
AT = datetime(2026, 10, 4, tzinfo=UTC)


def dataset() -> Dataset:
    return load_dataset(FIXTURE, digest(FIXTURE.read_bytes()))


def source(address: str = "192.0.2.10") -> Observation:
    row = example_observation(Settings()).model_dump(mode="json")
    row["target"]["address"] = row["endpoint"]["address"] = address
    return Observation.model_validate(row)


@pytest.mark.parametrize(
    "address,asns,place",
    [
        ("192.0.2.0", (64497, 64498), "fixture:east"),
        ("192.0.2.127", (64497, 64498), "fixture:east"),
        ("192.0.2.128", (64496,), "fixture:west"),
        ("192.0.2.255", (64496,), "fixture:west"),
        ("2001:db8:1::", (64499,), "fixture:east"),
        ("2001:db8:1:ffff:ffff:ffff:ffff:ffff", (64499,), "fixture:east"),
        ("2001:db8:2::1", (64496,), "fixture:west"),
        ("198.51.100.1", None, None),
        ("::ffff:192.0.2.10", None, None),
    ],
)
def test_longest_prefix_independent_dimensions(address: str, asns: Any, place: str | None) -> None:
    result = enrich(source(address), dataset(), AT)
    assert (result.network.asns if result.network else None) == asns
    assert (result.place.id if result.place else None) == place
    assert result.source_sha256 == digest(canonical(source(address)))


def test_clock_staleness_boundaries_and_reproducible_replay() -> None:
    data = dataset()
    for at, state in (
        (data.valid_from - timedelta(microseconds=1), "not_yet_valid"),
        (data.valid_from, "valid"),
        (data.expires_at, "stale"),
    ):
        record = enrich(source(), data, at)
        assert record.dataset_state == state
        if state != "valid":
            assert record.network is None and record.city is None and record.place is None
        assert Enrichment.model_validate_json(canonical(record)) == enrich(source(), data, at)
    with pytest.raises(ValueError, match="aware"):
        enrich(source(), data, AT.replace(tzinfo=None))


def test_unknown_radius_missing_coordinates_and_ambiguity() -> None:
    first = enrich(source(), dataset(), AT)
    assert first.city and first.city.accuracy_radius_km is None
    assert "accuracy_radius_unknown" in first.notes
    assert "multiple_origin_asns" in first.notes
    second = enrich(source("192.0.2.128"), dataset(), AT)
    assert second.city and second.city.accuracy_radius_km == 250
    missing = enrich(source("203.0.113.1"), dataset(), AT)
    assert missing.place and missing.place.point is None
    assert set(missing.notes) == {"asn_unknown", "coordinates_unknown", "accuracy_radius_unknown"}
    assert len(places_named(dataset(), "example harbor")) == 2
    assert [p.id for p in places_named(dataset(), "Example Harbor", "FJ")] == ["fixture:east"]
    assert places_named(dataset(), "absent") == ()


def test_versions_checksums_legacy_and_source_immutability(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_network(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("offline engine opened a socket")

    monkeypatch.setattr(socket, "socket", no_network)
    original = source()
    before = canonical(original)
    record = enrich(original, dataset(), AT)
    changed = Dataset.model_validate(dataset().model_dump() | {"version": "1.0.1"})
    assert enrich(original, changed, AT).dataset_sha256 != record.dataset_sha256
    content = dataset().model_dump()
    content["asn_prefixes"][0]["asns"] = (64500,)
    assert (
        enrich(original, Dataset.model_validate(content), AT).dataset_sha256
        != record.dataset_sha256
    )
    legacy = original.model_dump(mode="json")
    legacy.pop("protocol_evidence")
    legacy["schema_version"] = 1
    assert (
        enrich(observation_reader.validate_python(legacy), dataset(), AT).source_schema_version == 1
    )
    assert canonical(original) == before
    assert record.origins == dataset().origins
    assert enrich(original, dataset(), AT) == record


@pytest.mark.parametrize(
    "variant",
    [
        "duplicate",
        "host_bits",
        "bad_asn",
        "missing_origin",
        "missing_place",
        "duplicate_place",
        "nan",
        "radius",
        "unclosed",
        "unsplit",
        "dates",
        "schema",
    ],
)
def test_invalid_dataset_rejected(variant: str) -> None:
    data = dataset().model_dump(mode="json")
    match variant:
        case "duplicate":
            data["asn_prefixes"].append(data["asn_prefixes"][0])
        case "host_bits":
            data["asn_prefixes"][0]["prefix"] = "192.0.2.1/24"
        case "bad_asn":
            data["asn_prefixes"][0]["asns"] = [0]
        case "missing_origin":
            data["places"][0]["origin"] = "missing"
        case "missing_place":
            data["city_prefixes"][0]["place_id"] = "missing"
        case "duplicate_place":
            data["places"].append(data["places"][0])
        case "nan":
            data["places"][0]["point"][0] = float("nan")
        case "radius":
            data["city_prefixes"][0]["accuracy_radius_km"] = 0
        case "unclosed":
            data["places"][0]["boundary"]["coordinates"][0][0][-1] = [171, -20]
        case "unsplit":
            data["places"][0]["boundary"]["coordinates"] = [
                [[[170, -20], [-170, -20], [-170, -10], [170, -20]]]
            ]
        case "dates":
            data["expires_at"] = data["valid_from"]
        case "schema":
            data["schema_version"] = 2
    with pytest.raises(ValueError):
        Dataset.model_validate(data)


def test_input_bounds_checksums_duplicates_and_symlinks(tmp_path: Path) -> None:
    path = tmp_path / "dataset.json"
    for raw in (b"x" * (DATASET_BYTES + 1), b'{"schema_version":1,"schema_version":1}'):
        path.write_bytes(raw)
        with pytest.raises(ValueError):
            load_dataset(path, digest(raw))
    with pytest.raises(ValueError):
        load_dataset(FIXTURE, "0" * 64)
    path.unlink()
    path.symlink_to(FIXTURE.resolve())
    with pytest.raises(OSError):
        load_dataset(path, digest(FIXTURE.read_bytes()))


def test_private_offline_cli_and_replay(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = FIXTURE.resolve()
    monkeypatch.chdir(tmp_path)
    inputs = tmp_path / "input.jsonl"
    inputs.write_bytes(canonical(source()) + b"\n")
    output = Path("data/result.jsonl")
    command = [
        "netatlas-enrich",
        "--dataset",
        str(fixture),
        "--sha256",
        digest(fixture.read_bytes()),
        "apply",
        "--input",
        str(inputs),
        "--output",
        str(output),
        "--at",
        AT.isoformat(),
    ]
    run = subprocess.run(command, capture_output=True, text=True, check=True)
    assert json.loads(run.stdout)["records"] == 1
    assert output.stat().st_mode & 0o777 == 0o600
    expected = enrich(source(), load_dataset(fixture, digest(fixture.read_bytes())), AT)
    assert Enrichment.model_validate_json(output.read_bytes()) == expected
    assert subprocess.run(command, capture_output=True).returncode == 2
    with pytest.raises(ValueError):
        apply_file(
            inputs, Path("outside.jsonl"), load_dataset(fixture, digest(fixture.read_bytes())), AT
        )


def test_bbox_split_and_family_separation() -> None:
    boundary = bounding_boundary(170, -20, -170, -10)
    assert len(boundary.coordinates) == 2
    assert len(bounding_boundary(-180, -90, 180, 90).coordinates) == 2
    with pytest.raises(ValueError):
        bounding_boundary(170, 20, -170, -10)
    assert longest_prefix(ip_address("::1"), dataset().asn_prefixes) is None


def test_demo_import_preserves_source_ids_and_attribution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from netatlas.enrichment import demo

    point = {"type": "Point", "coordinates": [179.5, -17.5]}
    inputs = {
        "places": {
            "features": [
                {
                    "properties": {
                        "ne_id": 1159150917,
                        "name": "Fictional city fixture",
                        "iso_a2": "FJ",
                    },
                    "geometry": point,
                }
            ]
        },
        "countries": {
            "features": [
                {
                    "properties": {"NE_ID": 1159320625},
                    "geometry": bounding_boundary(170, -20, -170, -10).model_dump(mode="json"),
                }
            ]
        },
    }
    pins = {}
    for key, value in inputs.items():
        raw = json.dumps(value).encode()
        (tmp_path / key).write_bytes(raw)
        pins[key] = (key + ".geojson", digest(raw))
    monkeypatch.setattr(demo, "FILES", pins)
    data = demo.build_demo(tmp_path / "places", tmp_path / "countries")
    assert data.places[0].id == "ne:1159150917"
    assert data.places[0].point == (179.5, -17.5)
    assert data.origins[0].source_sha256 == pins["places"][1]
    assert data.origins[0].license == "Public domain"
    assert data.city_prefixes[0].origin == "synthetic"
    assert data.city_prefixes[0].accuracy_radius_km is None
    (tmp_path / "places").write_text("bad")
    with pytest.raises(ValueError, match="checksum"):
        demo.build_demo(tmp_path / "places", tmp_path / "countries")


def test_invalid_later_row_leaves_no_partial_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = dataset()
    monkeypatch.chdir(tmp_path)
    inputs = tmp_path / "bad.jsonl"
    inputs.write_bytes(canonical(source()) + b'\n{"secret":"never-print-me"}\n')
    with pytest.raises(ValueError):
        apply_file(inputs, Path("data/partial.jsonl"), data, AT)
    assert not Path("data/partial.jsonl").exists()
