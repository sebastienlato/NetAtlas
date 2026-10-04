"""Validated TOML settings: defaults < explicit file or NETATLAS_CONFIG."""

import hashlib
import json
import os
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import Field, IPvAnyNetwork, field_validator

from netatlas.domain import Model, Nonempty


class ApiSettings(Model):
    host: Literal["127.0.0.1", "::1"] = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535, strict=True)


class MeasurementSettings(Model):
    # Phase 1 must deliberately evolve this contract when the worker exists.
    enabled: Literal[False] = False
    node_id: Nonempty = "local-dev"
    operator_contact: str = ""
    user_agent: Nonempty = "NetAtlas/0.1 (research; measurement disabled)"
    connect_timeout_seconds: float = Field(default=3, gt=0, le=30, allow_inf_nan=False)
    interaction_timeout_seconds: float = Field(default=5, gt=0, le=60, allow_inf_nan=False)
    max_concurrency: int = Field(default=32, ge=1, le=1024, strict=True)
    global_connections_per_second: float = Field(default=10, gt=0, le=1000, allow_inf_nan=False)
    per_prefix_connections_per_second: float = Field(default=1, gt=0, le=100, allow_inf_nan=False)
    max_response_bytes: int = Field(default=65536, ge=1, le=65536, strict=True)
    exclusion_cidrs: tuple[IPvAnyNetwork, ...] = ()

    @field_validator("user_agent", "operator_contact")
    @classmethod
    def single_line(cls, value: str) -> str:
        if any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("identification fields must not contain control characters")
        return value


class LoggingSettings(Model):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"


class Settings(Model):
    api: ApiSettings = Field(default_factory=ApiSettings)
    measurement: MeasurementSettings = Field(default_factory=MeasurementSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    @property
    def sha256(self) -> str:
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


def load_settings(path: Path | None = None) -> Settings:
    configured = path or (
        Path(os.environ["NETATLAS_CONFIG"]) if "NETATLAS_CONFIG" in os.environ else None
    )
    if configured is None:
        return Settings()
    with configured.open("rb") as file:
        return Settings.model_validate(tomllib.load(file))
