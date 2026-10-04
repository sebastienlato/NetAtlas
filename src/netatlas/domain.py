"""Versioned observation contracts; these models perform no network I/O."""

import base64
import binascii
from enum import StrEnum
from ipaddress import IPv4Network, IPv6Network
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    IPvAnyAddress,
    field_validator,
    model_validator,
)

Confidence = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
Nonempty = Annotated[str, Field(min_length=1, max_length=512)]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Transport(StrEnum):
    TCP = "tcp"
    UDP = "udp"


class Protocol(StrEnum):
    UNKNOWN = "unknown"
    HTTP = "http"
    TLS = "tls"
    SSH = "ssh"
    SMTP = "smtp"
    DNS = "dns"
    FTP = "ftp"
    DATABASE = "database"
    OTHER = "other"


class Category(StrEnum):
    UNKNOWN = "unknown"
    WEB = "web_server"
    CAMERA = "camera_nvr"
    ROUTER = "router"
    NAS = "nas"
    PRINTER = "printer"
    SSH = "ssh_server"
    VPN = "vpn_appliance"
    MAIL = "mail_server"
    DATABASE = "database"
    IOT = "iot"
    INDUSTRIAL = "industrial"


class Outcome(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    TIMEOUT = "timeout"
    ERROR = "error"


class Target(Model):
    address: IPvAnyAddress
    source: Nonempty
    campaign_id: Nonempty


class Endpoint(Model):
    address: IPvAnyAddress
    port: int = Field(ge=1, le=65535, strict=True)
    transport: Transport = Transport.TCP

    @property
    def key(self) -> str:
        return f"{self.transport.value}://[{self.address.compressed}]:{self.port}"


class ScannerNode(Model):
    node_id: Nonempty
    software_version: Nonempty
    vantage: str | None = None


class CapturedResponse(Model):
    """Bounded, binary-safe bytes. Treat decoded content as untrusted data."""

    body_base64: str = Field(max_length=87384)
    media_type: Nonempty = "application/octet-stream"
    truncated: bool = False

    @field_validator("body_base64")
    @classmethod
    def bounded_base64(cls, value: str) -> str:
        try:
            decoded = base64.b64decode(value, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError("body_base64 must be valid base64") from exc
        if len(decoded) > 65536:
            raise ValueError("decoded response exceeds 65536 bytes")
        if base64.b64encode(decoded).decode("ascii") != value:
            raise ValueError("body_base64 must use canonical base64 encoding")
        return value


class Fingerprint(Model):
    rule_id: Nonempty
    rule_version: Nonempty
    product: Nonempty
    vendor: str | None = None
    version: str | None = None
    confidence: Confidence
    evidence: tuple[str, ...] = ()


class Classification(Model):
    category: Category = Category.UNKNOWN
    confidence: Confidence = 0.0
    rule_id: Nonempty
    evidence: tuple[str, ...] = ()


class Service(Model):
    protocol: Protocol = Protocol.UNKNOWN
    protocol_name: str | None = None
    tls: bool = False
    fingerprints: tuple[Fingerprint, ...] = ()
    classifications: tuple[Classification, ...] = ()


class Network(Model):
    prefix: IPv4Network | IPv6Network
    asn: int | None = Field(default=None, ge=1, le=4294967295, strict=True)
    organization: str | None = None
    source: Nonempty
    dataset_version: Nonempty


class GeoLocation(Model):
    country_code: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    region: str | None = None
    city: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90, allow_inf_nan=False)
    longitude: float | None = Field(default=None, ge=-180, le=180, allow_inf_nan=False)
    accuracy_radius_km: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    source: Nonempty
    dataset_version: Nonempty

    @model_validator(mode="after")
    def coordinate_pair(self) -> Self:
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be supplied together")
        return self


class Observation(Model):
    schema_version: Literal[1] = 1
    observation_id: UUID
    target: Target
    endpoint: Endpoint
    scanner: ScannerNode
    config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    started_at: AwareDatetime
    finished_at: AwareDatetime
    outcome: Outcome
    service: Service | None = None
    response: CapturedResponse | None = None
    network: Network | None = None
    geolocation: GeoLocation | None = None
    error_code: str | None = None

    @model_validator(mode="after")
    def consistent_observation(self) -> Self:
        if self.finished_at < self.started_at:
            raise ValueError("finished_at must not precede started_at")
        if self.target.address != self.endpoint.address:
            raise ValueError("target and endpoint addresses must match")
        if self.network and self.endpoint.address not in self.network.prefix:
            raise ValueError("endpoint must belong to the network prefix")
        if self.outcome != Outcome.OPEN and (self.response is not None or self.service is not None):
            raise ValueError("only open endpoints can carry a response or service")
        return self
