"""Versioned minimization, not comprehensive sensitive-content sanitization.

Only authored synthetic input is authorized. No raw/hex/base64 escape hatch.
Redact the whole field/body on a recognized marker BEFORE display truncation.
"""

import base64
import re
import unicodedata
import warnings

from cryptography import x509
from cryptography.exceptions import UnsupportedAlgorithm

from netatlas.derivations.engine import digest
from netatlas.domain import CapturedResponse
from netatlas.inspection.models import CaptureView, CertificateView, FieldView, Preview
from netatlas.protocol_syntax import inspect

# Deliberately conservative: a marker anywhere withholds the whole value, including
# obfuscated control-separated markers. Unknown secrets cannot be detected reliably.
SENSITIVE = re.compile(
    r"cookie|authorization|authenticate|bearer|basic\s|password|passwd|secret|token|"
    r"api[ _-]?key|session|credential|private[ _-]?key|-----begin|"
    r"://[^\s/]*@",
    re.IGNORECASE,
)


def preview(data: bytes, *, limit: int = 2048, supported: bool = True) -> Preview:
    if not data:
        return Preview(state="empty", original_bytes=0)
    if not supported:
        return Preview(state="unsupported", original_bytes=len(data))
    try:
        decoded = data.decode("utf-8")
    except UnicodeDecodeError:
        return Preview(state="unsupported", original_bytes=len(data))
    normalized = unicodedata.normalize("NFKC", decoded)
    normalized = "".join(c for c in normalized if unicodedata.category(c) not in ("Cc", "Cf"))
    if SENSITIVE.search(decoded) or SENSITIVE.search(normalized):
        return Preview(state="redacted", original_bytes=len(data))
    # No partial UTF-8 sequence. Controls (including line breaks and bidi) are visible.
    prefix = data[:limit].decode("utf-8", errors="ignore")
    visible = "".join(
        f"[U+{ord(c):04X}]" if unicodedata.category(c) in ("Cc", "Cf", "Zl", "Zp") else c
        for c in prefix
    )
    shown = len(prefix.encode("utf-8"))
    return Preview(
        state="text",
        text=visible,
        original_bytes=len(data),
        shown_bytes=shown,
        truncated=shown < len(data),
    )


def field(name: str, value: str) -> FieldView:
    return FieldView(name=name, value=preview(value.encode("utf-8"), limit=256))


def capture_view(capture: CapturedResponse, pointer: str) -> CaptureView:
    raw = base64.b64decode(capture.body_base64)
    parsed = inspect(raw, eof=not capture.truncated)
    fields: list[FieldView] = []
    withheld = 0
    body_start = None
    body = Preview(state="unsupported", original_bytes=len(raw))
    state = "malformed" if parsed.status == "malformed" else "unsupported"
    if parsed.http and parsed.http.headers_complete and parsed.status != "malformed":
        state = "http"
        http = parsed.http
        fields = [field("HTTP version", http.version), field("HTTP status", str(http.status))]
        for name, value in http.headers:
            if name.lower() in ("server", "content-type", "content-length"):
                fields.append(field(name.lower(), value))
            else:
                withheld += 1
        body_start = http.body_offset
        headers = {name.lower(): value for name, value in http.headers}
        types = [v for n, v in http.headers if n.lower() == "content-type"]
        supported = (
            len(types) == 1
            and types[0].lower().replace(" ", "")
            in (
                "text/plain",
                "text/html",
                "text/plain;charset=utf-8",
                "text/html;charset=utf-8",
            )
            and not any(n in headers for n in ("content-encoding", "transfer-encoding"))
        )
        data = raw[body_start:] if body_start is not None else b""
        if http.status < 200 or http.status in (204, 304):
            data = b""
        elif "content-length" in headers:
            data = data[: int(headers["content-length"])]
        body = preview(data, supported=supported)
    elif parsed.ssh:
        state = "ssh"
        fields = [
            field("SSH version", parsed.ssh.protocol_version),
            field("SSH software", parsed.ssh.software),
        ]
        # Preambles and comments may contain personal/authentication information.
        body = Preview(state="redacted", original_bytes=len(raw))
    elif parsed.smtp:
        state = "smtp"
        fields = [field("SMTP reply", "220")]
        # Greeting text doubles as the bounded content preview; no extra raw route.
        body = preview("\n".join(parsed.smtp.greeting).encode())
    return CaptureView(
        pointer=pointer,
        sha256=digest(raw),
        byte_length=len(raw),
        capture_truncated=capture.truncated,
        parse_state=state,  # type: ignore[arg-type]
        fields=tuple(fields),
        withheld_headers=withheld,
        body_start=body_start,
        preview=body,
    )


def certificate_view(capture: CapturedResponse, pointer: str) -> CertificateView:
    raw = base64.b64decode(capture.body_base64)
    base = CertificateView(
        pointer=pointer,
        sha256=digest(raw),
        byte_length=len(raw),
        capture_truncated=capture.truncated,
        parse_state="truncated" if capture.truncated else "parse_failed",
    )
    if capture.truncated:
        return base
    try:
        # Parsing only: no verification APIs, extension URLs, DNS or network I/O.
        # Parser warnings can contain peer data; convert them to generic failures.
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            cert = x509.load_der_x509_certificate(raw)
            fields = (
                field("Subject assertion", cert.subject.rfc4514_string()),
                field("Issuer assertion", cert.issuer.rfc4514_string()),
                field("Serial", format(cert.serial_number, "x")),
                field("Not before assertion", cert.not_valid_before_utc.isoformat()),
                field("Not after assertion", cert.not_valid_after_utc.isoformat()),
                field("Signature algorithm OID", cert.signature_algorithm_oid.dotted_string),
            )
        return base.model_copy(update={"parse_state": "parsed", "fields": fields})
    except UnsupportedAlgorithm:
        return base.model_copy(update={"parse_state": "unsupported"})
    except ValueError, TypeError, OverflowError, Warning:
        return base
