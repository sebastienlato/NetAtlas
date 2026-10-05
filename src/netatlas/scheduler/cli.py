"""Explicit private schedule files; offline planning is the default and never opens storage."""

import argparse
import json
from pathlib import Path
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from netatlas.control.coordinator import Coordinator
from netatlas.control.models import ControlError
from netatlas.derivations.engine import canonical, digest
from netatlas.derivations.offline import json_object, regular_file
from netatlas.enrichment.offline import publish
from netatlas.scheduler.models import PlanningInput
from netatlas.scheduler.planner import plan
from netatlas.scheduler.service import DOCUMENT_BYTES, enqueue, report, snapshot
from netatlas.storage.blobs import BlobStore
from netatlas.storage.database import local_engine
from netatlas.storage.pipeline import Pipeline


def read_input(path: Path) -> PlanningInput:
    with regular_file(path) as stream:
        data = stream.read(DOCUMENT_BYTES + 1)
    if len(data) > DOCUMENT_BYTES:
        raise ValueError("schedule input bound")
    return PlanningInput.model_validate(json_object(data))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Authored synthetic coverage/refresh scheduling")
    parser.add_argument("--storage", type=Path, default=Path("data/storage"))
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "snapshot", "enqueue"):
        command = commands.add_parser(name)
        command.add_argument("--input", type=Path, required=True)
        if name in ("plan", "snapshot"):
            command.add_argument("--output", type=Path, required=True)
        if name == "enqueue":
            command.add_argument("--measure", action="store_true")
            command.add_argument("--synthetic", action="store_true")
    status = commands.add_parser("report")
    status.add_argument("--campaign", type=UUID, required=True)
    args = parser.parse_args(argv)
    engine = None
    try:
        if args.command != "report":
            request = read_input(args.input)
            schedule = plan(request)
            if args.command == "plan" or (args.command == "enqueue" and not args.measure):
                if args.command == "plan":
                    publish(args.output, canonical(schedule) + b"\n")
                print(
                    json.dumps(
                        {
                            "schedule_sha256": digest(canonical(schedule)),
                            "counts": schedule.counts,
                            "execution": False,
                        }
                    )
                )
                return 0
        engine = local_engine(args.storage)
        coordinator = Coordinator(Pipeline(engine, BlobStore(args.storage / "blobs")))
        if args.command == "snapshot":
            current = snapshot(coordinator, request)
            publish(args.output, canonical(current) + b"\n")
            print(json.dumps({"history": len(current.history), "blocked": len(current.blocked)}))
        elif args.command == "enqueue":
            campaign = enqueue(coordinator, request, measure=args.measure, synthetic=args.synthetic)
            print(json.dumps({"campaign_id": str(campaign)}))
        else:
            print(json.dumps(report(coordinator, args.campaign), sort_keys=True))
        return 0
    except OSError, ValueError, SQLAlchemyError, ControlError:
        print('{"error":"schedule operation failed"}')
        return 2
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
