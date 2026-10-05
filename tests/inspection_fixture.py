"""Authored certificate/HTTP fixture for the isolated browser database only."""

import base64
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from sqlalchemy import text

from netatlas.derivations.engine import canonical
from netatlas.derivations.offline import load_pack
from netatlas.enrichment.models import Dataset
from netatlas.observation import Observation
from netatlas.search.models import Query
from netatlas.search.service import search
from netatlas.storage.enrichment import store_enrichment
from netatlas.storage.pipeline import Pipeline


def seed_inspection(pipeline: Pipeline, dataset_sha256: str) -> None:
    hit = search(pipeline.engine, Query(network="192.0.2.3/32"))["hits"][0]
    source = pipeline.load(hit["id"])
    now = datetime.now(UTC)
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "fixture.example\u202e")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(123)
        .not_valid_before(now - timedelta(days=2))
        .not_valid_after(now - timedelta(days=1))
        .sign(key, hashes.SHA256())
        .public_bytes(serialization.Encoding.DER)
    )
    raw = (
        b"HTTP/1.1 200 OK\r\nServer: nginx\r\nContent-Type: text/html\r\n"
        b"Set-Cookie: never-expose\r\nLocation: https://hostile.invalid/redirect\r\n\r\n"
        b'<script>window.pwned=1</script><img src="https://hostile.invalid/pixel">'
        b'\xe2\x80\xae <iframe src="https://hostile.invalid/frame"></iframe>'
    )
    row = Observation.model_validate(
        source.model_dump()
        | {
            "observation_id": uuid4(),
            "started_at": now - timedelta(seconds=2),
            "finished_at": now - timedelta(seconds=1),
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
                        "response": {"body_base64": base64.b64encode(raw).decode()},
                        "tls": {
                            "version": "TLSv1.3",
                            "cipher": "synthetic",
                            "secret_bits": 128,
                            "certificates": [{"body_base64": base64.b64encode(cert).decode()}],
                        },
                    }
                ],
            },
        }
    )
    pipeline.ingest(canonical(row), synthetic=True)
    pipeline.derive(row.observation_id, load_pack())
    with pipeline.engine.connect() as conn:
        dataset = Dataset.model_validate(
            conn.execute(
                text("SELECT document FROM enrichment_datasets WHERE sha256=:sha"),
                {"sha": dataset_sha256},
            ).scalar_one()
        )
    store_enrichment(pipeline, row.observation_id, dataset, now)
