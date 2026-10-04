"""Operator-only synthetic storage commands. No measurement or HTTP upload path."""

import argparse
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

from netatlas.derivations.offline import load_pack, read_observation, rows
from netatlas.enrichment.offline import load_dataset
from netatlas.storage.backup import backup, restore
from netatlas.storage.blobs import BlobStore
from netatlas.storage.database import initialize_local, local_engine, migrate
from netatlas.storage.enrichment import store_enrichment
from netatlas.storage.pipeline import Pipeline


def main() -> None:
    parser = argparse.ArgumentParser(prog="netatlas-store")
    parser.add_argument("--root", type=Path, default=Path("data/storage"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-local")
    sub.add_parser("migrate")
    ingest = sub.add_parser("ingest")
    ingest.add_argument("--input", type=Path, required=True)
    ingest.add_argument("--synthetic", action="store_true", required=True)
    derive = sub.add_parser("derive")
    derive.add_argument("--id", type=UUID, required=True)
    derive.add_argument("--pack", type=Path)
    enrichment = sub.add_parser("enrich")
    enrichment.add_argument("--id", type=UUID, required=True)
    enrichment.add_argument("--dataset", type=Path, required=True)
    enrichment.add_argument("--sha256", required=True)
    enrichment.add_argument("--at", type=datetime.fromisoformat, required=True)
    consume = sub.add_parser("consume")
    consume.add_argument("--consumer", default="local-mirror")
    consume.add_argument("--limit", type=int, default=100)
    consume.add_argument("--replay", action="store_true")
    consume.add_argument("--after", type=int, default=0)
    sub.add_parser("verify")
    sub.add_parser("collect")
    sub.add_parser("expire")
    suppress = sub.add_parser("suppress")
    suppress.add_argument("--network", required=True)
    save = sub.add_parser("backup")
    save.add_argument("--output", type=Path, required=True)
    recover = sub.add_parser("restore")
    recover.add_argument("--input", type=Path, required=True)
    recover.add_argument("--database", required=True)
    args = parser.parse_args()
    try:
        if (Path.cwd() / "data").is_symlink():
            raise ValueError("private data root required")
        if not args.root.absolute().resolve().is_relative_to((Path.cwd() / "data").resolve()):
            raise ValueError("storage root must be under ignored data")
        if args.command == "init-local":
            initialize_local(args.root)
            print(json.dumps({"initialized": True}))
            return
        engine = local_engine(args.root)
        try:
            if args.command == "restore":
                if not re.fullmatch(r"netatlas_restore_[a-z0-9_]{1,40}", args.database):
                    raise ValueError("separate restore database required")
                restored_engine = create_engine(
                    engine.url.set(database=args.database), hide_parameters=True
                )
                try:
                    restored = restore(
                        restored_engine, BlobStore(args.root / args.database / "blobs"), args.input
                    )
                    print(json.dumps(restored))
                finally:
                    restored_engine.dispose()
                return
            if args.command == "migrate":
                migrate(engine)
                print(json.dumps({"migrated": True}))
                return
            pipeline = Pipeline(engine, BlobStore(args.root / "blobs"))
            result: object
            match args.command:
                case "backup":
                    if (
                        not args.output.absolute()
                        .resolve()
                        .is_relative_to((Path.cwd() / "data").resolve())
                    ):
                        raise ValueError("private backup under data required")
                    backup(engine, pipeline.blobs, args.output)
                    result = {"backed_up": True}
                case "ingest":
                    inserted = replayed = 0
                    for raw in rows(args.input):
                        outcome = pipeline.ingest(raw, synthetic=args.synthetic)
                        inserted += outcome == "inserted"
                        replayed += outcome == "replayed"
                        # Each acknowledgement follows that row's durable commit; flush immediately.
                        print(
                            json.dumps(
                                {
                                    "ack": str(read_observation(raw).observation_id),
                                    "status": outcome,
                                }
                            ),
                            flush=True,
                        )
                    result = {"inserted": inserted, "replayed": replayed}
                case "derive":
                    result = {"derivation": pipeline.derive(args.id, load_pack(args.pack))}
                case "enrich":
                    result = {
                        "enrichment": store_enrichment(
                            pipeline, args.id, load_dataset(args.dataset, args.sha256), args.at
                        )
                    }
                case "consume":
                    result = pipeline.consume(
                        args.consumer, limit=args.limit, replay=args.replay, after=args.after
                    )
                case "verify":
                    result = pipeline.verify()
                case "collect":
                    result = {"blobs_collected": pipeline.collect()}
                case "expire":
                    result = pipeline.maintain()
                case "suppress":
                    result = pipeline.maintain(suppress=args.network)
                case _:
                    raise ValueError("unknown command")
            print(json.dumps(result))
        finally:
            engine.dispose()
    except (
        ValueError,
        OSError,
        SQLAlchemyError,
        RecursionError,
        KeyError,
        TypeError,
        subprocess.SubprocessError,
    ):
        parser.exit(
            2, "Storage operation failed; inspect local setup, input, policy and integrity.\n"
        )
