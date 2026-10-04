"""Offline previews, explicitly enabled bounded discovery, and local API launcher."""

import argparse
import asyncio
import json
import logging
import signal
import tomllib
from pathlib import Path

import uvicorn
from pydantic import ValidationError

from netatlas import __version__
from netatlas.api import create_app
from netatlas.config import Settings, load_settings
from netatlas.derivations.engine import canonical, digest
from netatlas.derivations.offline import apply_file, load_pack, validate_file
from netatlas.discovery.engine import run_campaign
from netatlas.discovery.policy import POLICY_SHA256, POLICY_VERSION, REGISTRY_VERSION
from netatlas.discovery.scope import Scope
from netatlas.examples import example_observation
from netatlas.observation import Observation


async def measure(settings: Settings, scope: Scope) -> dict[str, object]:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    for sig in previous:
        loop.add_signal_handler(sig, stop.set)
    try:
        return await run_campaign(settings, scope, stop=stop)
    finally:
        for sig, handler in previous.items():
            loop.remove_signal_handler(sig)
            signal.signal(sig, handler)


def main() -> None:
    parser = argparse.ArgumentParser(prog="netatlas")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--config", type=Path, help="TOML path; overrides NETATLAS_CONFIG")
    parser.add_argument(
        "command", choices=["config-check", "example", "schema", "serve", "discover", "fingerprint"]
    )
    parser.add_argument(
        "--target", action="append", default=[], help="literal IP or small strict CIDR"
    )
    parser.add_argument("--port", action="append", type=int, default=[], help="explicit TCP port")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--lab-loopback", action="store_true", help="only literal 127.0.0.1 / ::1")
    parser.add_argument("--measure", action="store_true", help="explicitly enable connections")
    parser.add_argument("--pack", type=Path, help="bounded JSON rule pack; default bundled core")
    parser.add_argument("--input", type=Path, help="offline observation JSONL")
    parser.add_argument("--output", type=Path, help="new derived JSONL under ignored data/")
    parser.add_argument("--validate", type=Path, help="replay and validate existing derived JSONL")
    parser.add_argument("--inspect", action="store_true", help="inspect rule pack as escaped JSON")
    args = parser.parse_args()
    if args.command == "fingerprint":
        try:
            pack = load_pack(args.pack)
            if args.inspect:
                if args.input or args.output or args.validate:
                    raise ValueError("incompatible options")
                print(
                    json.dumps(
                        {"pack": pack.model_dump(mode="json"), "sha256": digest(canonical(pack))},
                        ensure_ascii=True,
                        indent=2,
                    )
                )
            else:
                if args.input is None or bool(args.output) == bool(args.validate):
                    raise ValueError("supply input and exactly one output or validation path")
                result = (
                    validate_file(args.input, args.validate, pack)
                    if args.validate
                    else apply_file(args.input, args.output, pack)
                )
                print(json.dumps(result))
        except ValueError, OSError, RecursionError:
            parser.exit(
                2, "Fingerprint operation failed; check files, versions, bounds and options.\n"
            )
        return
    try:
        settings = load_settings(args.config)
    except OSError, ValueError, tomllib.TOMLDecodeError, ValidationError:
        parser.exit(2, "Invalid configuration; check the file path and documented TOML schema.\n")
    logging.basicConfig(level=settings.logging.level, format="%(message)s")
    match args.command:
        case "config-check":
            print(
                json.dumps(
                    {
                        "valid": True,
                        "measurement_enabled": settings.measurement.enabled,
                        "sha256": settings.sha256,
                    }
                )
            )
        case "example":
            print(example_observation(settings).model_dump_json(indent=2))
        case "schema":
            print(json.dumps(Observation.model_json_schema(), indent=2))
        case "discover":
            try:
                scope = Scope(
                    targets=tuple(args.target),
                    ports=tuple(args.port),
                    seed=args.seed,
                    lab_loopback=args.lab_loopback,
                )
                preview = scope.preview(settings.measurement)
                print(
                    json.dumps(
                        {
                            "dry_run": not args.measure,
                            "config_sha256": settings.sha256,
                            "config_version": settings.config_version,
                            "policy_version": POLICY_VERSION,
                            "policy_sha256": POLICY_SHA256,
                            "registry_version": REGISTRY_VERSION,
                            "budgets": settings.measurement.model_dump(
                                mode="json",
                                exclude={
                                    "operator_name",
                                    "operator_contact",
                                    "user_agent",
                                },
                            ),
                            **preview,
                        },
                        indent=2,
                    ),
                    flush=True,
                )
                if args.measure:
                    manifest = asyncio.run(measure(settings, scope))
                    print(
                        json.dumps(
                            {
                                "campaign_id": manifest["campaign_id"],
                                "status": manifest["status"],
                                "completed": manifest["completed"],
                            }
                        )
                    )
                    if manifest["status"] != "completed":
                        parser.exit(130 if manifest["status"] == "cancelled" else 1)
            except ValueError, OSError, ExceptionGroup:
                parser.exit(
                    2, "Discovery failed; check scope, enabled identity, budgets, and spool.\n"
                )
        case "serve":
            uvicorn.run(
                create_app(settings),
                host=settings.api.host,
                port=settings.api.port,
                log_level=settings.logging.level.lower(),
                access_log=False,
                proxy_headers=False,
            )
