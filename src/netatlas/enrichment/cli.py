"""Offline operator tool; no downloads, credentials or measurement."""

import argparse
import json
from datetime import datetime
from pathlib import Path

from netatlas.derivations.engine import canonical, digest
from netatlas.enrichment.engine import places_named
from netatlas.enrichment.offline import apply_file, load_dataset


def main() -> None:
    parser = argparse.ArgumentParser(prog="netatlas-enrich")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--sha256", required=True, help="SHA-256 of the exact input file")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("inspect")
    places = sub.add_parser("places")
    places.add_argument("--name", required=True)
    places.add_argument("--country")
    apply = sub.add_parser("apply")
    apply.add_argument("--input", type=Path, required=True)
    apply.add_argument("--output", type=Path, required=True)
    apply.add_argument("--at", type=datetime.fromisoformat, required=True)
    args = parser.parse_args()
    try:
        dataset = load_dataset(args.dataset, args.sha256)
        result: object
        if args.command == "apply":
            result = apply_file(args.input, args.output, dataset, args.at)
        elif args.command == "places":
            result = [
                p.model_dump(mode="json") for p in places_named(dataset, args.name, args.country)
            ]
        else:
            result = {
                "id": dataset.id,
                "version": dataset.version,
                "dataset_sha256": digest(canonical(dataset)),
                "valid_from": dataset.valid_from.isoformat(),
                "expires_at": dataset.expires_at.isoformat(),
                "origins": [o.model_dump(mode="json") for o in dataset.origins],
            }
        print(json.dumps(result, ensure_ascii=True))
    except ValueError, OSError, RecursionError, TypeError, KeyError:
        parser.exit(2, "Enrichment failed; check local input, checksum, clock and output.\n")
