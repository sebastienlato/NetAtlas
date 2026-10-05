"""Explicit operator controls and independent local coordinator/worker processes."""

import argparse
import asyncio
import json
import signal
from pathlib import Path
from uuid import UUID

import uvicorn
from sqlalchemy.exc import SQLAlchemyError

from netatlas.config import load_settings
from netatlas.control.coordinator import Coordinator
from netatlas.control.files import Credential, Credentials, Spool, provision, read_private
from netatlas.control.http import create_control_app
from netatlas.control.models import ControlError
from netatlas.control.worker import LocalTransport, Worker
from netatlas.derivations.offline import json_object
from netatlas.discovery.policy import POLICY_SHA256
from netatlas.discovery.scope import Scope
from netatlas.storage.blobs import BlobStore
from netatlas.storage.database import local_engine
from netatlas.storage.pipeline import Pipeline


async def run_worker(worker: Worker) -> None:
    current = asyncio.current_task()
    assert current is not None
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, current.cancel)
    try:
        await worker.start()
        while await worker.step():
            pass
    finally:
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.remove_signal_handler(sig)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Private local synthetic worker control plane")
    parser.add_argument("--storage", type=Path, default=Path("data/storage"))
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser(
        "provision", help="Generate two private worker credentials in a NEW directory"
    )
    init.add_argument("--directory", type=Path, default=Path("data/control/credentials"))
    server = commands.add_parser(
        "serve", help="Authenticated loopback coordinator; no read/UI routes"
    )
    server.add_argument(
        "--credentials", type=Path, default=Path("data/control/credentials/coordinator.json")
    )
    server.add_argument("--port", type=int, default=8001)
    worker = commands.add_parser(
        "worker", help="Drain jobs using one durable spool slot; exits when idle"
    )
    worker.add_argument("--credential", type=Path, required=True)
    worker.add_argument("--spool", type=Path, required=True)
    worker.add_argument("--port", type=int, default=8001)
    enqueue = commands.add_parser(
        "enqueue", help="Preview by default; worker measurement is literal loopback only"
    )
    enqueue.add_argument("--config", type=Path)
    enqueue.add_argument("--target", action="append", required=True)
    enqueue.add_argument("--port", type=int, action="append", required=True)
    enqueue.add_argument("--lab-loopback", action="store_true")
    enqueue.add_argument("--synthetic", action="store_true")
    enqueue.add_argument("--measure", action="store_true")
    cancel = commands.add_parser("cancel")
    cancel.add_argument("--campaign", type=UUID, required=True)
    commands.add_parser("status")
    commands.add_parser("stop", help="Durably cancel all work and block new enqueue")
    commands.add_parser("allow-new-work", help="Reopen enqueue; never revive cancelled jobs")
    commands.add_parser(
        "prune", help="Remove control history older than 90 days; preserves pacing/generations"
    )
    args = parser.parse_args(argv)
    engine = None
    try:
        if args.command == "provision":
            provision(args.directory)
        elif args.command == "worker":
            credential = Credential.model_validate(json_object(read_private(args.credential, 4096)))
            spool = Spool(args.spool)
            with spool.lock():
                boot = spool.boot(credential.worker_id)
                asyncio.run(run_worker(Worker(LocalTransport(credential, args.port), spool, boot)))
        else:
            if args.command == "enqueue":
                settings = load_settings(args.config)
                scope = Scope(
                    targets=tuple(args.target),
                    ports=tuple(args.port),
                    lab_loopback=args.lab_loopback,
                )
                if not args.measure:
                    print(
                        json.dumps(
                            {
                                "preview": scope.preview(settings.measurement),
                                "config_sha256": settings.sha256,
                                "policy_sha256": POLICY_SHA256,
                                "worker_scope": "synthetic literal loopback only",
                            }
                        )
                    )
                    return 0
            engine = local_engine(args.storage)
            coordinator = Coordinator(Pipeline(engine, BlobStore(args.storage / "blobs")))
            if args.command == "serve":
                credentials = Credentials.model_validate(
                    json_object(read_private(args.credentials, 16384))
                )
                if not 1 <= args.port <= 65535:
                    raise ValueError("port bound")
                uvicorn.run(
                    create_control_app(coordinator, credentials, args.port),
                    host="127.0.0.1",
                    port=args.port,
                    access_log=False,
                    proxy_headers=False,
                    log_level="critical",
                )
            elif args.command == "enqueue":
                identity = coordinator.enqueue(
                    settings, scope, measure=True, synthetic=args.synthetic
                )
                print(json.dumps({"campaign_id": str(identity)}))
            elif args.command == "cancel":
                coordinator.cancel(args.campaign)
            elif args.command == "stop":
                coordinator.stop()
            elif args.command == "allow-new-work":
                coordinator.allow_new_work()
            elif args.command == "status":
                print(
                    json.dumps(
                        {"jobs": coordinator.status(), "global_stopped": coordinator.is_stopped()},
                        sort_keys=True,
                    )
                )
            elif args.command == "prune":
                coordinator.prune()
        return 0
    except asyncio.CancelledError, KeyboardInterrupt:
        return 130
    except OSError, ValueError, SQLAlchemyError, ControlError:
        print('{"error":"control operation failed"}')
        return 2
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
