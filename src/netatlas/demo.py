"""Explicit synthetic UI seed; never imported or executed by the read API."""

import argparse
import base64
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from netatlas.config import Settings
from netatlas.derivations.engine import canonical, digest
from netatlas.derivations.offline import load_pack
from netatlas.enrichment.models import CityPrefix, Dataset, Place
from netatlas.examples import example_observation
from netatlas.observation import Observation
from netatlas.storage.blobs import BlobStore
from netatlas.storage.database import local_engine
from netatlas.storage.enrichment import store_enrichment
from netatlas.storage.pipeline import Pipeline


def demo_dataset(at: datetime) -> Dataset:
    original = Dataset.model_validate_json(
        Path(__file__).with_name("demo_geography.json").read_bytes()
    )
    extra = (
        Place(
            id="demo:east",
            origin="synthetic",
            name="Example Harbor",
            country_code="FJ",
            admin_code="E",
            point=(179.5, -17.5),
        ),
        Place(
            id="demo:west",
            origin="synthetic",
            name="Example Harbor",
            country_code="FJ",
            admin_code="W",
            point=(-179.5, -17.5),
        ),
        Place.model_validate(
            {
                "id": "demo:region",
                "origin": "synthetic",
                "name": "Example Region",
                "country_code": "FJ",
                "admin_code": "DEMO",
                "kind": "region",
                "boundary_kind": "synthetic",
                "boundary": {
                    "type": "MultiPolygon",
                    "coordinates": [[[[177, -19], [180, -19], [180, -16], [177, -16], [177, -19]]]],
                },
            }
        ),
    )
    cities = (
        *original.city_prefixes,
        CityPrefix(prefix="192.0.2.9/32", origin="synthetic", place_id="demo:east"),
        CityPrefix(
            prefix="192.0.2.10/32",
            origin="synthetic",
            place_id="demo:west",
            accuracy_radius_km=250,
            radius_basis="dataset_reported",
        ),
    )
    synthetic = original.origins[-1].model_copy(
        update={
            "version": "2.0.0",
            "source_sha256": digest(
                b"\n".join(canonical(r) for r in (*extra, *original.asn_prefixes, *cities))
            ),
            "modifications": (
                "Fictional places/region and IP/ASN mappings; hash covers canonical extra "
                "places, ASN rows and city rows joined with newline. No real geography claim."
            ),
        }
    )
    return Dataset.model_validate(
        original.model_dump()
        | {
            "id": "geographic-ui-demo",
            "version": "2.0.0",
            "valid_from": at - timedelta(days=1),
            "expires_at": at + timedelta(days=7),
            "places": (*original.places, *extra),
            "city_prefixes": cities,
            "origins": (*original.origins[:-1], synthetic),
        }
    )


def seed(pipeline: Pipeline, at: datetime, *, thesis: bool = False) -> str:
    """Twelve authored endpoints, one negative follow-up; no cleanup of owner data."""
    data = demo_dataset(at)
    pack = load_pack()
    addresses = [*(f"192.0.2.{n}" for n in range(1, 11)), "2001:db8::1", "198.51.100.1"]
    for index, address in enumerate(addresses):
        row = example_observation(Settings()).model_dump(mode="json")
        row.update(
            observation_id=uuid4(),
            started_at=at - timedelta(seconds=120 + index),
            finished_at=at - timedelta(seconds=119 + index),
            network=None,
            geolocation=None,
        )
        row["target"]["address"] = row["endpoint"]["address"] = address
        content = (
            b"SSH-2.0-OpenSSH_9.0\r\n"
            if index % 3 == 1
            else b"HTTP/1.1 200 OK\r\nServer: nginx\r\n\r\n"
        )
        row["response"] = {"body_base64": base64.b64encode(content).decode()}
        if address == "198.51.100.1":
            row["response"] = None
        source = Observation.model_validate(row)
        pipeline.ingest(canonical(source), synthetic=True)
        pipeline.derive(source.observation_id, pack)
        store_enrichment(pipeline, source.observation_id, data, at)
        if index == 0:
            negative = Observation.model_validate(
                source.model_dump()
                | {
                    "observation_id": uuid4(),
                    "started_at": at - timedelta(seconds=20),
                    "finished_at": at - timedelta(seconds=19),
                    "outcome": "timeout",
                    "response": None,
                    "service": None,
                }
            )
            pipeline.ingest(canonical(negative), synthetic=True)
            pipeline.derive(negative.observation_id, pack)
            store_enrichment(pipeline, negative.observation_id, data, at)
    if thesis:
        # Additional authored evidence, never collected by this seed or a read request.
        for suffix, age, outcome, captures in (
            (14, 172800, "open", (b"HTTP/1.1 200 OK\r\nServer: nginx\r\n\r\n",)),
            (
                15,
                60,
                "open",
                (b"HTTP/1.1 200 OK\r\nServer: nginx\r\n\r\n", b"SSH-2.0-OpenSSH_9.0\r\n"),
            ),
            (16, 60, "closed", ()),
        ):
            row = example_observation(Settings()).model_dump(mode="json")
            row.update(
                observation_id=uuid4(),
                started_at=at - timedelta(seconds=age + 1),
                finished_at=at - timedelta(seconds=age),
                outcome=outcome,
                response=None,
                service=None,
                network=None,
                geolocation=None,
            )
            row["target"].update(address=f"203.0.113.{suffix}", source="authored-thesis-demo-1")
            row["endpoint"]["address"] = f"203.0.113.{suffix}"
            if captures:
                row["protocol_evidence"] = {
                    "received_bytes": sum(map(len, captures)),
                    "retained_bytes": sum(map(len, captures)),
                    "sent_bytes": 0,
                    "termination": "finished",
                    "exchanges": [
                        {
                            "connection": i + 1,
                            "probe": "greeting-http" if i == 0 else "tls",
                            "tcp_outcome": "open",
                            "status": "unknown",
                            "response": {"body_base64": base64.b64encode(raw).decode()},
                        }
                        for i, raw in enumerate(captures)
                    ],
                }
            source = Observation.model_validate(row)
            pipeline.ingest(canonical(source), synthetic=True)
            pipeline.derive(source.observation_id, pack)
            store_enrichment(pipeline, source.observation_id, data, at)
    return digest(canonical(data))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--thesis", action="store_true", help="append stale/ambiguous/closed fixtures"
    )
    args = parser.parse_args()
    engine = local_engine(Path("data/storage"))
    try:
        pipeline = Pipeline(engine, BlobStore(Path("data/storage/blobs")))
        pipeline.maintain()
        at = datetime.now(UTC)
        print(
            json.dumps(
                {
                    "synthetic": True,
                    "profile": "thesis-demo-1" if args.thesis else "geographic-ui-demo",
                    "dataset_sha256": seed(pipeline, at, thesis=args.thesis),
                    "seeded_at": at.isoformat(),
                    "dataset_valid_from": (at - timedelta(days=1)).isoformat(),
                    "dataset_expires_at": (at + timedelta(days=7)).isoformat(),
                }
            )
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
