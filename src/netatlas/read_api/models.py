"""Allowlisted HTTP metadata. No source envelopes, raw fields or evidence selectors."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, Field

from netatlas.domain import Category, Model
from netatlas.enrichment.models import (
    AsnPrefix,
    CityPrefix,
    Identifier,
    Label,
    Origin,
    Position,
    Sha,
)
from netatlas.search.models import Query

Cursor = Annotated[str, Field(min_length=1, max_length=2048)]


class SearchQuery(Query):
    offset: Literal[0] = 0


class SearchRequest(Model):
    schema_version: Literal[1]
    query: SearchQuery = Field(default_factory=SearchQuery)
    cursor: Cursor | None = None


class EndpointQuery(Model):
    selection: Literal["attempt", "open", "evidence"] = "attempt"
    as_of: AwareDatetime | None = None
    pack_sha256: Sha | None = None
    dataset_sha256: Sha | None = None
    fingerprint_engine: Literal["fingerprints-1"] = "fingerprints-1"
    taxonomy: Literal["netatlas-categories-1"] = "netatlas-categories-1"
    enrichment_engine: Literal["enrichment-1"] = "enrichment-1"
    fresh_seconds: int = Field(default=86400, ge=1, le=2592000, strict=True)
    limit: int = Field(default=50, ge=1, le=200, strict=True)


class EndpointRequest(Model):
    schema_version: Literal[1]
    query: EndpointQuery = Field(default_factory=EndpointQuery)
    cursor: Cursor | None = None


class PlacesQuery(Model):
    dataset_sha256: Sha
    name: str | None = Field(default=None, min_length=1, max_length=256)
    country: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    kind: Literal["city", "region", "country"] | None = None
    limit: int = Field(default=50, ge=1, le=200, strict=True)


class PlacesRequest(Model):
    schema_version: Literal[1]
    query: PlacesQuery
    cursor: Cursor | None = None


class Error(Model):
    code: Literal[
        "invalid_request",
        "invalid_cursor",
        "cursor_expired",
        "not_found",
        "forbidden",
        "too_large",
        "unsupported_media_type",
        "request_timeout",
        "busy",
        "unavailable",
        "response_too_large",
        "internal_error",
        "method_not_allowed",
    ]


class ErrorResponse(Model):
    error: Error


class DatasetMetadata(Model):
    schema_version: Literal[1]
    id: Identifier
    version: Label
    valid_from: AwareDatetime
    expires_at: AwareDatetime
    origins: tuple[Origin, ...] = Field(max_length=16)


class PackMetadata(Model):
    schema_version: Literal[1]
    pack_id: str
    version: str
    taxonomy_version: Literal["netatlas-categories-1"]
    provenance: Label


class HitPlace(Model):
    id: Identifier
    name: Label
    country_code: str
    point: Position | None


class Hit(Model):
    id: UUID
    source_sha256: Sha
    address: str
    port: int
    transport: Literal["tcp", "udp"]
    outcome: Literal["open", "closed", "timeout", "error"]
    finished_at: AwareDatetime
    started_at: AwareDatetime
    has_evidence: bool
    fresh: bool
    derivation_id: Sha | None
    enrichment_id: Sha | None
    category_state: Literal["unknown", "single", "multiple"]
    geography_state: Literal["known", "unknown", "stale", "not_yet_valid"]
    network: AsnPrefix | None
    place: HitPlace | None
    city: CityPrefix | None
    candidate_count: int = Field(ge=0, le=128)
    products: tuple[Label, ...] = Field(max_length=128)
    categories: tuple[Category, ...] = Field(max_length=128)


class Counts(Model):
    endpoints: int = Field(ge=0)
    observations: int = Field(ge=0)
    candidates: int = Field(ge=0)


class Facet(Model):
    kind: Literal["category", "asn", "country", "prefix", "geography"]
    value: str
    endpoints: int = Field(ge=0)
    observations: int = Field(ge=0)
    rank: int = Field(ge=1, le=50)
    total_buckets: int = Field(ge=1)


class SearchMetadata(Model):
    schema_version: Literal[1] = 1
    selection: SearchQuery
    retention_checked_at: AwareDatetime
    dataset_checked_at: AwareDatetime
    dataset: DatasetMetadata | None
    pack: PackMetadata | None
    counts: Counts
    facets: tuple[Facet, ...] = Field(max_length=250)
    location_semantics: Literal["approximate_area_not_person_or_device"] = (
        "approximate_area_not_person_or_device"
    )
    count_semantics: Literal["selected_retained_observations_not_devices_or_prevalence"] = (
        "selected_retained_observations_not_devices_or_prevalence"
    )


class SearchResponse(SearchMetadata):
    hits: tuple[Hit, ...] = Field(max_length=200)
    next_cursor: Cursor | None = None
    page_limit_reached: bool = False


class PlaceSummary(Model):
    id: Identifier
    origin: Identifier
    name: Label
    country_code: str
    admin_code: Label | None
    kind: Literal["city", "country", "region"]
    point: Position | None
    boundary_kind: Literal["generalized", "synthetic"] | None
    has_boundary: bool


class PlacesResponse(Model):
    schema_version: Literal[1] = 1
    dataset_sha256: Sha
    dataset: DatasetMetadata
    dataset_state: Literal["valid", "stale", "not_yet_valid"]
    retention_checked_at: AwareDatetime
    places: tuple[PlaceSummary, ...] = Field(max_length=200)
    total: int = Field(ge=0, le=4096)
    next_cursor: Cursor | None = None
    location_semantics: Literal["approximate_area_not_person_or_device"] = (
        "approximate_area_not_person_or_device"
    )
