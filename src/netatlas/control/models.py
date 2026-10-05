"""Versioned bounded control messages, independent of read and observation contracts."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, TypeAdapter, field_validator

from netatlas.config import Settings
from netatlas.domain import Endpoint, Model
from netatlas.observation import Observation

BODY_BYTES = 1048576
LEASE_SECONDS = 10.0
PERMIT_SECONDS = 0.25
HEARTBEAT_SECONDS = 1.0
DELIVERY_HOURS = 24
MAX_JOBS = 1024
MAX_QUEUE = 128
MAX_ATTEMPTS = 3


class Identity(Model):
    schema_version: Literal[1]
    worker_id: UUID
    session_id: UUID


class Register(Identity):
    action: Literal["register"]
    generation: int = Field(ge=1, le=2147483647, strict=True)


class Claim(Identity):
    action: Literal["claim"]


class Authority(Identity):
    job_id: UUID
    attempt_id: UUID
    fence: int = Field(ge=1, le=MAX_ATTEMPTS, strict=True)


class Heartbeat(Authority):
    action: Literal["heartbeat"]


class Permit(Authority):
    action: Literal["permit"]
    connection: int = Field(ge=1, le=2, strict=True)


class Resume(Authority):
    action: Literal["resume"]


class Abandon(Authority):
    action: Literal["abandon"]


class Deliver(Authority):
    action: Literal["deliver"]
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    observation: Observation

    @field_validator("observation", mode="before")
    @classmethod
    def explicit_source_version(cls, value: object) -> object:
        if isinstance(value, dict) and (
            type(value.get("schema_version")) is not int or value.get("schema_version") != 2
        ):
            raise ValueError("explicit worker observation version required")
        return value


Request = Annotated[
    Register | Claim | Heartbeat | Permit | Resume | Abandon | Deliver,
    Field(discriminator="action"),
]
request_reader: TypeAdapter[Request] = TypeAdapter(Request)


class Lease(Model):
    job_id: UUID
    attempt_id: UUID
    observation_id: UUID
    campaign_id: UUID
    fence: int = Field(ge=1, le=MAX_ATTEMPTS, strict=True)
    endpoint: Endpoint
    settings: Settings
    config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    remaining_seconds: float = Field(gt=0, le=3600)


class Reply(Model):
    schema_version: Literal[1] = 1
    status: Literal["ok", "idle", "wait", "granted", "inserted", "replayed"] = "ok"
    lease: Lease | None = None
    delay_seconds: float = Field(default=0, ge=0, le=3600)
    valid_seconds: float = Field(default=0, ge=0, le=PERMIT_SECONDS)


class ControlError(Exception):
    def __init__(self, status: int, code: str) -> None:
        super().__init__(code)
        self.status = status
        self.code = code
