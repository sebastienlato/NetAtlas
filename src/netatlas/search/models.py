"""Local query contract. No raw capture fields are part of search results."""

from ipaddress import ip_network
from typing import Literal, Self

from pydantic import AwareDatetime, Field, field_validator, model_validator

from netatlas.domain import Category, Model
from netatlas.enrichment.models import Identifier, Latitude, Longitude, Sha


class Radius(Model):
    longitude: Longitude
    latitude: Latitude
    metres: float = Field(gt=0, le=20040000, allow_inf_nan=False)


class Box(Model):
    west: Longitude
    south: Latitude
    east: Longitude
    north: Latitude

    @model_validator(mode="after")
    def nonempty(self) -> Self:
        if self.south >= self.north or self.west == self.east:
            raise ValueError("nonempty box required")
        return self


class Query(Model):
    schema_version: Literal[1] = 1
    mode: Literal["current", "history"] = "current"
    selection: Literal["attempt", "open", "evidence"] = "attempt"
    as_of: AwareDatetime | None = None
    after: AwareDatetime | None = None
    before: AwareDatetime | None = None
    freshness: Literal["any", "fresh", "stale"] = "any"
    fresh_seconds: int = Field(default=86400, ge=1, le=2592000, strict=True)
    network: str | None = Field(default=None, max_length=49)
    port: int | None = Field(default=None, ge=1, le=65535, strict=True)
    transport: Literal["tcp", "udp"] | None = None
    outcome: Literal["open", "closed", "timeout", "error"] | None = None
    has_evidence: bool | None = None
    category: Category | None = None
    text: str | None = Field(default=None, min_length=1, max_length=256)
    pack_sha256: Sha | None = None  # null resolves to the bundled core hash
    fingerprint_engine: Literal["fingerprints-1"] = "fingerprints-1"
    taxonomy: Literal["netatlas-categories-1"] = "netatlas-categories-1"
    dataset_sha256: Sha | None = None  # null deliberately disables enrichment
    enrichment_engine: Literal["enrichment-1"] = "enrichment-1"
    asn: int | None = Field(default=None, ge=1, le=4294967295, strict=True)
    country: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    place_id: Identifier | None = None
    geography: Literal["any", "known", "unknown", "stale", "not_yet_valid"] = "any"
    radius: Radius | None = None
    box: Box | None = None
    boundary_place_id: Identifier | None = None
    limit: int = Field(default=50, ge=1, le=200, strict=True)
    offset: int = Field(default=0, ge=0, le=10000, strict=True)
    facet_limit: int = Field(default=20, ge=1, le=50, strict=True)

    @field_validator("network")
    @classmethod
    def cidr(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if "%" in value:
            raise ValueError("literal network required")
        return str(ip_network(value, strict=True))

    @field_validator("text")
    @classmethod
    def printable(cls, value: str | None) -> str | None:
        if value is not None and (not value.strip() or not value.isprintable()):
            raise ValueError("printable search text required")
        return value

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.after and self.before and self.after >= self.before:
            raise ValueError("empty observation window")
        if sum(x is not None for x in (self.radius, self.box, self.boundary_place_id)) > 1:
            raise ValueError("select one geographic area")
        needs_dataset = (
            self.asn is not None
            or self.country is not None
            or self.place_id is not None
            or self.radius is not None
            or self.box is not None
            or self.boundary_place_id is not None
            or self.geography != "any"
        )
        if needs_dataset and self.dataset_sha256 is None:
            raise ValueError("geographic/network derivations require a dataset hash")
        return self
