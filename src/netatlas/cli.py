"""Small offline CLI and local API launcher."""

import argparse
import json
import logging
import tomllib
from pathlib import Path

import uvicorn
from pydantic import ValidationError

from netatlas import __version__
from netatlas.api import create_app
from netatlas.config import load_settings
from netatlas.domain import Observation
from netatlas.examples import example_observation


def main() -> None:
    parser = argparse.ArgumentParser(prog="netatlas")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--config", type=Path, help="TOML path; overrides NETATLAS_CONFIG")
    parser.add_argument("command", choices=["config-check", "example", "schema", "serve"])
    args = parser.parse_args()
    try:
        settings = load_settings(args.config)
    except OSError, ValueError, tomllib.TOMLDecodeError, ValidationError:
        parser.exit(2, "Invalid configuration; check the file path and documented TOML schema.\n")
    logging.basicConfig(level=settings.logging.level, format="%(levelname)s %(name)s %(message)s")
    match args.command:
        case "config-check":
            print(
                json.dumps({"valid": True, "measurement_enabled": False, "sha256": settings.sha256})
            )
        case "example":
            print(example_observation(settings).model_dump_json(indent=2))
        case "schema":
            print(json.dumps(Observation.model_json_schema(), indent=2))
        case "serve":
            uvicorn.run(
                create_app(settings),
                host=settings.api.host,
                port=settings.api.port,
                log_level=settings.logging.level.lower(),
                access_log=False,
            )
