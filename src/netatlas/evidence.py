"""Typed protocol evidence contracts. No I/O and no product/device derivations."""

import base64
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from netatlas.domain import CapturedResponse, Model, Outcome, Protocol


class HttpMetadata(Model):
    version: Literal["1.0", "1.1"]
    status: int = Field(ge=100, le=599)
    # Ordered duplicates preserved, no cookie jar or URL interpretation.
    headers: tuple[
        tuple[
            Annotated[str, Field(min_length=1, max_length=256)],
            Annotated[str, Field(max_length=2048)],
        ],
        ...,
    ] = Field(max_length=32)
    headers_complete: bool
    body_offset: int | None = Field(default=None, ge=0, le=65536)
    host_source: Literal["target-ip"] | None = None


class TlsMetadata(Model):
    version: str = Field(max_length=32)
    cipher: str = Field(max_length=128)
    secret_bits: int = Field(ge=0, le=512)
    alpn: str | None = Field(default=None, max_length=32)
    certificates: tuple[CapturedResponse, ...] = Field(max_length=8)
    chain_truncated: bool = False
    verification: Literal["not_performed"] = "not_performed"
    sni: None = None


class SshMetadata(Model):
    protocol_version: Literal["2.0", "1.99"]
    software: str = Field(min_length=1, max_length=245)
    comments: str | None = Field(default=None, max_length=245)


class SmtpMetadata(Model):
    reply_code: Literal[220] = 220
    greeting: tuple[Annotated[str, Field(max_length=512)], ...] = Field(min_length=1, max_length=32)
    identification: Literal["explicit-smtp-greeting"] = "explicit-smtp-greeting"


class Exchange(Model):
    connection: int = Field(ge=1, le=2)
    probe: Literal["greeting-http", "tls"]
    tcp_outcome: Outcome
    status: Literal[
        "complete",
        "unknown",
        "ambiguous",
        "malformed",
        "eof",
        "interaction_timeout",
        "endpoint_timeout",
        "byte_limit",
        "transport_error",
        "tls_error",
        "connect_failed",
    ]
    error_code: str | None = None
    response: CapturedResponse | None = None
    http_request_sent: bool = False
    http: HttpMetadata | None = None
    tls: TlsMetadata | None = None
    ssh: SshMetadata | None = None
    smtp: SmtpMetadata | None = None
    candidates: tuple[Protocol, ...] = Field(default=(), max_length=2)

    @model_validator(mode="after")
    def evidence_requires_connection(self) -> Self:
        if self.tcp_outcome != Outcome.OPEN and any(
            (self.response, self.http, self.tls, self.ssh, self.smtp, self.candidates)
        ):
            raise ValueError("protocol evidence requires an established connection")
        if sum(value is not None for value in (self.http, self.ssh, self.smtp)) > 1:
            raise ValueError("one application protocol per exchange")
        if any((self.http, self.ssh, self.smtp)) and self.response is None:
            raise ValueError("application metadata requires raw evidence")
        if (
            self.http
            and self.http.body_offset is not None
            and self.response
            and self.http.body_offset > len(base64.b64decode(self.response.body_base64))
        ):
            raise ValueError("HTTP body offset exceeds capture")
        if self.tls and self.probe != "tls":
            raise ValueError("TLS metadata requires the TLS probe")
        return self


class ProtocolEvidence(Model):
    strategy: Literal["greeting-http-tls-v1"] = "greeting-http-tls-v1"
    exchanges: tuple[Exchange, ...] = Field(min_length=1, max_length=2)
    # Socket payload bytes, including TLS records. Sent counts are conservative
    # reservations if a send is interrupted; excludes TCP/IP overhead/retransmits.
    received_bytes: int = Field(ge=0, le=65536)
    sent_bytes: int = Field(ge=0, le=16384)
    retained_bytes: int = Field(ge=0, le=65536)
    termination: Literal[
        "finished", "endpoint_timeout", "byte_limit", "connection_limit", "admission_stopped"
    ]

    @model_validator(mode="after")
    def consistent_capture(self) -> Self:
        sizes = sum(
            len(base64.b64decode(capture.body_base64))
            for exchange in self.exchanges
            for capture in (
                *((exchange.response,) if exchange.response else ()),
                *(exchange.tls.certificates if exchange.tls else ()),
            )
        )
        if self.retained_bytes > self.received_bytes:
            raise ValueError("retained bytes cannot exceed received payload")
        if sizes != self.retained_bytes:
            raise ValueError("retained byte count differs from evidence")
        if [e.connection for e in self.exchanges] != list(range(1, len(self.exchanges) + 1)):
            raise ValueError("exchanges must be ordered unique connection attempts")
        return self
