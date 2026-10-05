"""Synthetic hostile-content and real-storage inspection acceptance."""

import base64
import socket
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from sqlalchemy import text
from test_read_api import client_for, post
from test_storage import observation

from netatlas.derivations.engine import canonical, derive, digest
from netatlas.derivations.offline import load_pack
from netatlas.domain import CapturedResponse, ObservationV1
from netatlas.inspection.preview import capture_view, certificate_view, preview
from netatlas.inspection.project import check_trace
from netatlas.observation import Observation
from netatlas.storage.blobs import BlobStore
from netatlas.storage.database import transaction
from netatlas.storage.pipeline import Pipeline

pytest_plugins = ["test_storage"]
PATH = "endpoints/192.0.2.10/tcp/80/inspection"


def capture(raw: bytes, truncated: bool = False) -> CapturedResponse:
    return CapturedResponse(body_base64=base64.b64encode(raw).decode(), truncated=truncated)


def request(source: Observation | ObservationV1, identity: str | None = None) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "query": {
            "observation_id": str(source.observation_id),
            "source_sha256": digest(canonical(source)),
            "derivation_id": identity,
        },
    }


def http(body: bytes, headers: bytes = b"Content-Type: text/html\r\n") -> bytes:
    return b"HTTP/1.1 200 OK\r\nServer: nginx\r\n" + headers + b"\r\n" + body


@pytest.mark.parametrize(
    "marker",
    [
        b"Password=hunter-fixture",
        b"Authorization: Basic abc",
        b"Set-Cookie: key=fixture",
        b"api_key=fixture",
        b"Bearer fixture",
        b"session=fixture",
        b"https://user:fixture@example.org/",
        b"-----BEGIN PRIVATE KEY-----",
        "pass\u202eword=fixture".encode(),
        "ＴＯＫＥＮ=fixture".encode(),
    ],
)
def test_sensitive_marker_anywhere_redacts_before_truncation(marker: bytes) -> None:
    value = preview(b"x" * 4096 + marker)
    assert value.state == "redacted" and value.text == "" and value.shown_bytes == 0


def test_hostile_text_is_bounded_inert_and_controls_visible() -> None:
    raw = '<script>location="https://hostile.invalid"</script>\u202e\x00'.encode()
    value = preview(raw)
    assert "<script>" in value.text and "[U+202E][U+0000]" in value.text
    large = preview(b"x" * 65536)
    assert large.shown_bytes == 2048 and large.truncated and len(large.text) == 2048
    assert preview(b"\xff\xfe").state == "unsupported"


@pytest.mark.parametrize(
    "headers",
    [
        b"Content-Type: application/json\r\n",
        b"Content-Type: image/svg+xml\r\n",
        b"Content-Type: text/html\r\nContent-Encoding: gzip\r\n",
        b"Content-Type: text/html\r\nTransfer-Encoding: chunked\r\n",
        b"Content-Type: text/html\r\nContent-Type: text/plain\r\n",
        b"",
    ],
)
def test_unreviewed_encoded_and_ambiguous_types_have_no_raw_fallback(headers: bytes) -> None:
    result = capture_view(
        capture(http(b"<img src='https://hostile.invalid'>", headers)), "/response/body_base64"
    )
    assert result.preview.state == "unsupported" and not result.preview.text


def test_headers_comments_malformed_binary_and_body_bounds() -> None:
    result = capture_view(
        capture(
            http(
                b"safeSECRET",
                b"Content-Type: text/plain\r\nContent-Length: 4\r\n"
                b"Set-Cookie: never-expose\r\nLocation: https://hostile.invalid\r\n"
                b"X-Private: never-expose\r\n",
            )
        ),
        "/response/body_base64",
    )
    assert result.preview.text == "safe" and result.withheld_headers == 3
    assert "never-expose" not in result.model_dump_json()
    assert "hostile.invalid" not in result.model_dump_json()
    for raw in [b"HTTP/1.1 200 OK\r\nBad\r\n\r\nSECRET", b"\x00SECRET", b"HTTP/1.1 200 OK\r\n"]:
        assert not capture_view(capture(raw), "/response/body_base64").preview.text
    ssh = capture_view(capture(b"SSH-2.0-OpenSSH_9.0 private-comment\r\n"), "/response/body_base64")
    assert "private-comment" not in ssh.model_dump_json() and ssh.parse_state == "ssh"
    smtp = capture_view(capture(b"220 fixture.example ESMTP Postfix\r\n"), "/response/body_base64")
    assert smtp.parse_state == "smtp" and "Postfix" in smtp.preview.text


def cert_bytes() -> bytes:
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, '<img src="https://hostile.invalid">\u202e')]
    )
    now = datetime.now(UTC)
    return (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(42)
        .not_valid_before(now - timedelta(days=3))
        .not_valid_after(now - timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.UniformResourceIdentifier("https://hostile.invalid/aia")]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
        .public_bytes(serialization.Encoding.DER)
    )


def test_certificates_are_parsed_assertions_never_validated_or_fetched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("network forbidden")

    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    raw = cert_bytes()
    result = certificate_view(capture(raw), "/certificate")
    assert result.parse_state == "parsed" and result.verification == "not_performed"
    assert "[U+202E]" in result.model_dump_json() and "/aia" not in result.model_dump_json()
    assert certificate_view(capture(raw, True), "/certificate").parse_state == "truncated"
    for invalid in (b"", b"x" * 65536, raw[:20], raw + b"trailing"):
        assert certificate_view(capture(invalid), "/certificate").parse_state == "parse_failed"


def test_exact_trace_rejects_wrong_pointer_range_and_hash() -> None:
    source = observation()
    result = derive(source, load_pack())
    check_trace(source, result)
    c = result.candidates[0]
    for patch in (
        {"end": 65536},
        {"sha256": "0" * 64},
        {"pointer": "/protocol_evidence/exchanges/0/response/body_base64"},
    ):
        bad = result.model_copy(
            update={
                "candidates": (
                    c.model_copy(update={"evidence": (c.evidence[0].model_copy(update=patch),)}),
                )
            }
        )
        with pytest.raises(ValueError, match="trace integrity"):
            check_trace(source, bad)


def test_inspection_source_binding_redaction_and_immutable_replay(pipeline: Pipeline) -> None:
    raw = http(
        b'<img src="https://hostile.invalid">\xe2\x80\xae',
        b"Content-Type: text/html\r\nSet-Cookie: never-expose\r\nAuthorization: never-expose\r\n",
    )
    source = observation(body=raw)
    pipeline.ingest(canonical(source), synthetic=True)
    identity = pipeline.derive(source.observation_id, load_pack())
    before = canonical(pipeline.load(source.observation_id))
    with client_for(pipeline) as client:
        response = client.post("/api/v1/" + PATH, json=request(source, identity))
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["trace_integrity"] == "checked"
        assert data["derivation"]["source_sha256"] == digest(before)
        assert "never-expose" not in response.text and "body_base64" not in data
        assert "\\u003cimg" in response.text and "[U+202E]" in response.text
        assert response.headers["cache-control"] == "no-store"
        for path in [PATH.replace("192.0.2.10", "192.0.2.99"), PATH.replace("/80/", "/81/")]:
            assert client.post("/api/v1/" + path, json=request(source)).status_code == 404
        for patch in (
            {"source_sha256": "0" * 64},
            {"observation_id": str(uuid4())},
            {"derivation_id": "0" * 64},
        ):
            body = request(source)
            body["query"].update(patch)
            assert client.post("/api/v1/" + PATH, json=body).status_code == 404
        body = request(source)
        body["query"]["pointer"] = "../../private"
        assert client.post("/api/v1/" + PATH, json=body).status_code == 422
    assert canonical(pipeline.load(source.observation_id)) == before
    assert pipeline.verify()["observations"] == 1


@pytest.mark.parametrize("mode", ["expiry", "suppression", "removal"])
def test_every_endpoint_read_rechecks_retention(
    pipeline: Pipeline, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    source = observation(age=29 * 86400)
    pipeline.ingest(canonical(source), synthetic=True)
    identity = pipeline.derive(source.observation_id, load_pack())
    with client_for(pipeline) as client:
        assert client.post("/api/v1/" + PATH, json=request(source, identity)).status_code == 200
        if mode == "suppression":
            # Persistence before physical maintenance must already deny all reads.
            with transaction(pipeline.engine) as conn:
                conn.execute(text("INSERT INTO suppressions(network) VALUES ('192.0.2.0/24')"))
        elif mode == "removal":
            pipeline.maintain(suppress="192.0.2.0/24")
        else:

            class Later(datetime):
                @classmethod
                def now(cls, tz: Any = None) -> datetime:  # type: ignore[override]
                    return datetime.now(UTC) + timedelta(days=2)

            monkeypatch.setattr("netatlas.storage.inspection.datetime", Later)
            monkeypatch.setattr("netatlas.read_api.service.datetime", Later)
        assert client.post("/api/v1/" + PATH, json=request(source, identity)).status_code == 404
        base = PATH.removesuffix("inspection")
        assert post(client, base + "detail").status_code == 404
        assert post(client, base + "history").json()["hits"] == []


def test_v1_ipv6_negative_and_tls_inspection(pipeline: Pipeline) -> None:
    old = observation(address="2001:db8::1")
    legacy = ObservationV1.model_validate(
        old.model_dump(exclude={"protocol_evidence"}) | {"schema_version": 1}
    )
    pipeline.ingest(canonical(legacy), synthetic=True)
    negative = observation(address="2001:db8::1", outcome="timeout", body=None)
    pipeline.ingest(canonical(negative), synthetic=True)
    cert = cert_bytes()
    raw = http(b"auth_token=never-expose")
    source = Observation.model_validate(
        observation().model_dump()
        | {
            "response": None,
            "protocol_evidence": {
                "received_bytes": len(cert) + len(raw),
                "sent_bytes": 0,
                "retained_bytes": len(cert) + len(raw),
                "termination": "finished",
                "exchanges": [
                    {
                        "connection": 1,
                        "probe": "tls",
                        "tcp_outcome": "open",
                        "status": "complete",
                        "response": capture(raw),
                        "tls": {
                            "version": "TLSv1.3",
                            "cipher": "fixture",
                            "secret_bits": 128,
                            "certificates": [capture(cert)],
                            "chain_truncated": True,
                        },
                    }
                ],
            },
        }
    )
    pipeline.ingest(canonical(source), synthetic=True)
    with client_for(pipeline) as client:
        path = "/api/v1/" + PATH.replace("192.0.2.10", "2001:db8::1")
        assert client.post(path, json=request(legacy)).json()["source_schema_version"] == 1
        assert client.post(path, json=request(negative)).json()["legacy_capture"] is None
        result = client.post("/api/v1/" + PATH, json=request(source))
        assert result.status_code == 200, result.text
        e = result.json()["exchanges"][0]
        assert e["verification"] == "not_performed" and e["chain_truncated"]
        assert e["certificates"][0]["parse_state"] == "parsed"
        assert e["capture"]["preview"]["state"] == "redacted"
        assert "never-expose" not in result.text
        history = post(client, "endpoints/2001:db8::1/tcp/80/history").json()
        assert len(history["hits"]) == 2
        detail = post(
            client, "endpoints/2001:db8::1/tcp/80/detail", {"selection": "evidence"}
        ).json()
        assert detail["hits"][0]["id"] == str(legacy.observation_id)


def test_expiry_during_projection_and_blob_failure_fail_closed(
    pipeline: Pipeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = observation()
    pipeline.ingest(canonical(source), synthetic=True)
    import netatlas.read_api.inspection as reader
    from netatlas.storage.inspection import eligible

    original = eligible
    monkeypatch.setattr(reader, "eligible", lambda *a, **kw: None)
    with client_for(pipeline) as client:
        assert client.post("/api/v1/" + PATH, json=request(source)).status_code == 404
        monkeypatch.setattr(reader, "eligible", original)

        def bad_read(sha: str) -> bytes:
            raise OSError("secret filesystem path")

        monkeypatch.setattr(pipeline.blobs, "read", bad_read)
        result = client.post("/api/v1/" + PATH, json=request(source))
        assert result.status_code == 503 and "secret" not in result.text


def test_ambiguous_selected_derivation_no_cross_source_or_execution(
    pipeline: Pipeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    from test_search import ambiguous_pack

    first, other = observation(), observation()
    for source in (first, other):
        pipeline.ingest(canonical(source), synthetic=True)
    selected = pipeline.derive(first.observation_id, ambiguous_pack())
    core = pipeline.derive(first.observation_id, load_pack())
    foreign = pipeline.derive(other.observation_id, ambiguous_pack())

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("inspection must not run rules or resolve names")

    monkeypatch.setattr("netatlas.storage.pipeline.derive", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    with client_for(pipeline) as client:
        result = client.post("/api/v1/" + PATH, json=request(first, selected))
        assert result.status_code == 200, result.text
        record = result.json()["derivation"]
        assert record["category_state"] == "multiple" and len(record["candidates"]) == 2
        assert {c["category"] for c in record["candidates"]} == {"web_server", "router"}
        assert record["pack_sha256"] == digest(canonical(ambiguous_pack()))
        assert client.post("/api/v1/" + PATH, json=request(first, foreign)).status_code == 404
        # Multiple exact versions coexist; no arbitrary newest-pack choice.
        assert (
            len(
                client.post("/api/v1/" + PATH, json=request(first, core)).json()["derivation"][
                    "candidates"
                ]
            )
            == 1
        )


def test_inspection_blob_open_does_not_create_or_accept_public_directories(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    with pytest.raises(FileNotFoundError):
        BlobStore(missing, create=False)
    assert not missing.exists()
    public = tmp_path / "public"
    public.mkdir(mode=0o755)
    with pytest.raises(ValueError):
        BlobStore(public, create=False)
    private = BlobStore(tmp_path / "private")
    sha = private.put(b"fixture")
    assert BlobStore(private.root, create=False).read(sha) == b"fixture"
    link = tmp_path / "link"
    link.symlink_to(private.root)
    with pytest.raises(ValueError):
        BlobStore(link, create=False)
