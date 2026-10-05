"""Deliberate inspection contract, separate from canonical source models."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, Field

from netatlas.derivations.models import Derivation, Digest
from netatlas.domain import Model, Protocol

DisplayText = Annotated[str, Field(max_length=16384)]


class Preview(Model):
    state: Literal["text", "redacted", "unsupported", "empty"]
    text: DisplayText = ""
    original_bytes: int = Field(ge=0, le=65536)
    shown_bytes: int = Field(default=0, ge=0, le=2048)
    truncated: bool = False


class FieldView(Model):
    name: str = Field(max_length=64)
    value: Preview


class CaptureView(Model):
    pointer: str = Field(max_length=128)
    sha256: Digest
    byte_length: int = Field(ge=0, le=65536)
    capture_truncated: bool
    parse_state: Literal["http", "ssh", "smtp", "malformed", "unsupported"]
    fields: tuple[FieldView, ...] = Field(max_length=34)
    withheld_headers: int = Field(ge=0, le=32, default=0)
    body_start: int | None = Field(default=None, ge=0, le=65536)
    preview: Preview


class CertificateView(Model):
    pointer: str = Field(max_length=128)
    sha256: Digest
    byte_length: int = Field(ge=0, le=65536)
    capture_truncated: bool
    parse_state: Literal["parsed", "parse_failed", "truncated", "unsupported"]
    verification: Literal["not_performed"] = "not_performed"
    fields: tuple[FieldView, ...] = Field(default=(), max_length=8)


class ExchangeView(Model):
    connection: int = Field(ge=1, le=2)
    probe: Literal["greeting-http", "tls"]
    tcp_outcome: Literal["open", "closed", "timeout", "error"]
    status: str = Field(max_length=32)
    http_request_sent: bool
    candidates: tuple[Protocol, ...]
    tls_fields: tuple[FieldView, ...] = Field(max_length=4)
    verification: Literal["not_performed"] | None
    chain_truncated: bool
    certificates: tuple[CertificateView, ...] = Field(max_length=8)
    capture: CaptureView | None


class InspectionQuery(Model):
    observation_id: UUID
    source_sha256: Digest
    derivation_id: Digest | None = None


class InspectionRequest(Model):
    schema_version: Literal[1]
    query: InspectionQuery


class InspectionResponse(Model):
    schema_version: Literal[1] = 1
    preview_policy: Literal["synthetic-preview-1"] = "synthetic-preview-1"
    observation_id: UUID
    source_sha256: Digest
    source_schema_version: Literal[1, 2]
    address: str
    transport: Literal["tcp", "udp"]
    port: int
    started_at: AwareDatetime
    finished_at: AwareDatetime
    expires_at: AwareDatetime
    retention_checked_at: AwareDatetime
    outcome: Literal["open", "closed", "timeout", "error"]
    legacy_capture: CaptureView | None
    exchanges: tuple[ExchangeView, ...] = Field(max_length=2)
    derivation_id: Digest | None
    derivation: Derivation | None
    trace_integrity: Literal["checked", "not_requested"]
