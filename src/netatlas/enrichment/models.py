"""Versioned bounded datasets. Coordinates describe approximate areas, never devices."""

from datetime import UTC
from ipaddress import IPv4Network, IPv6Network, ip_network
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, field_validator, model_validator

from netatlas.domain import Model

Label = Annotated[str, Field(min_length=1, max_length=512)]
Identifier = Annotated[str, Field(pattern=r"^[a-zA-Z0-9_.:-]{1,96}$")]
Sha = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Longitude = Annotated[float, Field(ge=-180, le=180, allow_inf_nan=False)]
Latitude = Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)]
Position = tuple[Longitude, Latitude]
Ring = Annotated[tuple[Position, ...], Field(min_length=4, max_length=4096)]
Polygon = Annotated[tuple[Ring, ...], Field(min_length=1, max_length=32)]


class Boundary(Model):
    type: Literal["MultiPolygon"] = "MultiPolygon"
    coordinates: tuple[Polygon, ...] = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def closed_and_split(self) -> Self:
        vertices = 0
        for polygon in self.coordinates:
            for ring in polygon:
                vertices += len(ring)
                if ring[0] != ring[-1] or len(set(ring)) < 3:
                    raise ValueError("closed nondegenerate rings required")
                if any(abs(a[0] - b[0]) > 180 for a, b in zip(ring, ring[1:], strict=False)):
                    raise ValueError("split boundaries at the antimeridian")
        if vertices > 8192:
            raise ValueError("boundary vertex limit")
        return self


class Origin(Model):
    id: Identifier
    version: Label
    source_url: Label
    source_sha256: Sha
    license: Label
    license_url: Label
    attribution: Label
    modifications: Label


class Place(Model):
    id: Identifier
    origin: Identifier
    name: Label
    country_code: str = Field(pattern=r"^[A-Z]{2}$")
    admin_code: Label | None = None
    kind: Literal["city", "country", "region"] = "city"
    point: Position | None = None
    boundary: Boundary | None = None
    boundary_kind: Literal["generalized", "synthetic"] | None = None

    @model_validator(mode="after")
    def boundary_label(self) -> Self:
        if (self.boundary is None) != (self.boundary_kind is None):
            raise ValueError("boundary requires an explicit interpretation")
        return self


class Prefix(Model):
    prefix: str = Field(max_length=49)
    origin: Identifier

    @field_validator("prefix")
    @classmethod
    def canonical_prefix(cls, value: str) -> str:
        if "/" not in value or "%" in value:
            raise ValueError("literal CIDR required")
        return str(ip_network(value, strict=True))

    @property
    def network(self) -> IPv4Network | IPv6Network:
        return ip_network(self.prefix)


class AsnPrefix(Prefix):
    asns: tuple[Annotated[int, Field(ge=1, le=4294967295, strict=True)], ...] = Field(
        min_length=1, max_length=16
    )
    organization: Label | None = None

    @field_validator("asns")
    @classmethod
    def canonical_asns(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        if len(set(value)) != len(value):
            raise ValueError("duplicate ASN")
        return tuple(sorted(value))


class CityPrefix(Prefix):
    place_id: Identifier
    accuracy_radius_km: float | None = Field(default=None, gt=0, le=20040, allow_inf_nan=False)
    radius_basis: Literal["dataset_reported", "unknown"] = "unknown"

    @model_validator(mode="after")
    def uncertainty(self) -> Self:
        if (self.accuracy_radius_km is None) != (self.radius_basis == "unknown"):
            raise ValueError("radius requires dataset provenance; missing is not zero")
        return self


class Dataset(Model):
    schema_version: Literal[1] = 1
    id: Identifier
    version: Label
    valid_from: AwareDatetime
    expires_at: AwareDatetime
    origins: tuple[Origin, ...] = Field(min_length=1, max_length=16)
    places: tuple[Place, ...] = Field(default=(), max_length=4096)
    asn_prefixes: tuple[AsnPrefix, ...] = Field(default=(), max_length=4096)
    city_prefixes: tuple[CityPrefix, ...] = Field(default=(), max_length=4096)

    @field_validator("valid_from", "expires_at")
    @classmethod
    def utc(cls, value: AwareDatetime) -> AwareDatetime:
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def references(self) -> Self:
        if self.expires_at <= self.valid_from:
            raise ValueError("empty validity window")
        origins = {item.id for item in self.origins}
        places = {item.id for item in self.places}
        if len(origins) != len(self.origins) or len(places) != len(self.places):
            raise ValueError("duplicate dataset identifier")
        for collection in (self.asn_prefixes, self.city_prefixes):
            if len({item.prefix for item in collection}) != len(collection):
                raise ValueError("duplicate prefix; encode ambiguity in one row")
        referenced: tuple[Place | AsnPrefix | CityPrefix, ...] = (
            *self.places,
            *self.asn_prefixes,
            *self.city_prefixes,
        )
        for item in referenced:
            if item.origin not in origins:
                raise ValueError("unknown origin")
        if any(item.place_id not in places for item in self.city_prefixes):
            raise ValueError("unknown place identifier")
        return self


class Enrichment(Model):
    schema_version: Literal[1] = 1
    engine_version: Literal["enrichment-1"] = "enrichment-1"
    source_observation_id: UUID
    source_schema_version: Literal[1, 2]
    source_sha256: Sha
    dataset_id: Identifier
    dataset_version: Label
    dataset_sha256: Sha
    evaluated_at: AwareDatetime
    dataset_state: Literal["valid", "stale", "not_yet_valid"]
    network: AsnPrefix | None = None
    city: CityPrefix | None = None
    place: Place | None = None
    origins: tuple[Origin, ...]
    notes: tuple[str, ...]
    location_semantics: Literal["approximate_area_not_person_or_device"] = (
        "approximate_area_not_person_or_device"
    )
