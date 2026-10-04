"""Validated TOML settings: defaults < explicit file or NETATLAS_CONFIG."""

import hashlib
import json
import os
import re
import tomllib
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, IPvAnyNetwork, field_validator, model_validator

from netatlas.domain import Model, Nonempty


class ApiSettings(Model):
    host: Literal["127.0.0.1", "::1"] = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535, strict=True)


class MeasurementSettings(Model):
    enabled: bool = Field(default=False, strict=True)
    node_id: Nonempty = "local-dev"
    operator_name: str = Field(default="", max_length=120)
    operator_contact: str = Field(default="", max_length=512)
    user_agent: Nonempty = "NetAtlas/0.3 (research; measurement disabled)"
    connect_timeout_seconds: float = Field(default=3, gt=0, le=30, allow_inf_nan=False)
    interaction_timeout_seconds: float = Field(default=5, gt=0, le=60, allow_inf_nan=False)
    protocol_evidence: bool = Field(default=False, strict=True)
    greeting_timeout_seconds: float = Field(default=0.5, gt=0, le=5, allow_inf_nan=False)
    endpoint_timeout_seconds: float = Field(default=15, gt=0, le=120, allow_inf_nan=False)
    max_connections_per_endpoint: int = Field(default=2, ge=1, le=2, strict=True)
    max_sent_bytes: int = Field(default=8192, ge=1, le=16384, strict=True)
    max_concurrency: int = Field(default=32, ge=1, le=128, strict=True)
    global_connections_per_second: float = Field(default=10, gt=0, le=100, allow_inf_nan=False)
    per_prefix_connections_per_second: float = Field(default=1, gt=0, le=20, allow_inf_nan=False)
    max_response_bytes: int = Field(default=65536, ge=1, le=65536, strict=True)
    queue_size: int = Field(default=128, ge=1, le=256, strict=True)
    max_addresses: int = Field(default=4096, ge=1, le=4096, strict=True)
    max_endpoints: int = Field(default=16384, ge=1, le=16384, strict=True)
    campaign_timeout_seconds: float = Field(default=300, gt=0, le=3600, allow_inf_nan=False)
    exclusion_cidrs: tuple[IPvAnyNetwork, ...] = Field(default=(), max_length=1024)
    opt_out_cidrs: tuple[IPvAnyNetwork, ...] = Field(default=(), max_length=1024)
    allow_cidrs: tuple[IPvAnyNetwork, ...] = Field(default=(), max_length=1024)

    @field_validator("user_agent", "operator_contact", "operator_name", "node_id")
    @classmethod
    def single_line(cls, value: str) -> str:
        if any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("identification fields must not contain control characters")
        return value

    @field_validator("user_agent")
    @classmethod
    def ascii_agent(cls, value: str) -> str:
        if not value.isascii():
            raise ValueError("user_agent must be ASCII for HTTP")
        return value

    @model_validator(mode="after")
    def enabled_identity(self) -> Self:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", self.node_id):
            raise ValueError("node_id must be a bounded identifier")
        if self.enabled:
            contact = self.operator_contact
            url = urlsplit(contact)
            email = re.fullmatch(r"[^\s@:/]+@[^\s@:/]+\.[^\s@:/]+", contact)
            https = (
                url.scheme == "https"
                and url.hostname
                and "." in url.hostname
                and not url.username
                and not url.password
                and not url.query
                and not url.fragment
                and not any(char.isspace() for char in contact)
            )
            if not self.operator_name.strip() or not (email or https):
                raise ValueError(
                    "enabled measurement requires operator name and email/HTTPS contact"
                )
            if (
                "measurement disabled" in self.user_agent.lower()
                or "research" not in self.user_agent.lower()
            ):
                raise ValueError("enabled measurement requires an explicit research user-agent")
        return self


class LoggingSettings(Model):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"


class Settings(Model):
    config_version: Literal[3] = 3
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
