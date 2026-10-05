"""Pure source projections and exact trace checks; never execute fingerprint rules."""

import base64

from netatlas.derivations.engine import digest
from netatlas.derivations.models import Derivation
from netatlas.domain import ObservationV1
from netatlas.inspection.models import ExchangeView
from netatlas.inspection.preview import capture_view, certificate_view, field
from netatlas.observation import Observation

AnyObservation = ObservationV1 | Observation


def exchanges(source: AnyObservation) -> tuple[ExchangeView, ...]:
    if not isinstance(source, Observation) or source.protocol_evidence is None:
        return ()
    result = []
    for i, exchange in enumerate(source.protocol_evidence.exchanges):
        pointer = f"/protocol_evidence/exchanges/{i}"
        tls = exchange.tls
        result.append(
            ExchangeView(
                connection=exchange.connection,
                probe=exchange.probe,
                tcp_outcome=exchange.tcp_outcome.value,
                status=exchange.status,
                http_request_sent=exchange.http_request_sent,
                candidates=exchange.candidates,
                tls_fields=(
                    field("TLS version", tls.version),
                    field("Cipher", tls.cipher),
                    field("Secret bits", str(tls.secret_bits)),
                    field("ALPN", tls.alpn or "none"),
                )
                if tls
                else (),
                verification="not_performed" if tls else None,
                chain_truncated=tls.chain_truncated if tls else False,
                certificates=tuple(
                    certificate_view(c, f"{pointer}/tls/certificates/{j}/body_base64")
                    for j, c in enumerate(tls.certificates)
                )
                if tls
                else (),
                capture=capture_view(exchange.response, f"{pointer}/response/body_base64")
                if exchange.response
                else None,
            )
        )
    return tuple(result)


def check_trace(source: AnyObservation, result: Derivation) -> None:
    captures = {}
    if source.response:
        captures["/response/body_base64"] = base64.b64decode(source.response.body_base64)
    if isinstance(source, Observation) and source.protocol_evidence:
        for i, exchange in enumerate(source.protocol_evidence.exchanges):
            if exchange.response:
                captures[f"/protocol_evidence/exchanges/{i}/response/body_base64"] = (
                    base64.b64decode(exchange.response.body_base64)
                )
    if result.source_schema_version != source.schema_version:
        raise ValueError("trace source mismatch")
    for candidate in result.candidates:
        for ref in candidate.evidence:
            raw = captures.get(ref.pointer)
            if raw is None or ref.end > len(raw) or digest(raw[ref.start : ref.end]) != ref.sha256:
                raise ValueError("trace integrity failure")
