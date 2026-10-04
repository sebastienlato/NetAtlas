"""A single TLS handshake, preserving unverified certificate and negotiation evidence."""

import base64

from netatlas.collectors.io import Counters, SocketChannel, TlsChannel
from netatlas.config import MeasurementSettings
from netatlas.domain import CapturedResponse
from netatlas.evidence import TlsMetadata


class TlsCollector:
    def __init__(self, raw: SocketChannel) -> None:
        self.channel = TlsChannel(raw)

    async def collect(self, config: MeasurementSettings, count: Counters) -> TlsMetadata:
        await self.channel.handshake()
        certs = self.channel.ssl.get_unverified_chain()
        captured: list[CapturedResponse] = []
        for cert in certs[:8]:
            if len(cert) > config.max_response_bytes - count.retained:
                break
            captured.append(
                CapturedResponse(
                    body_base64=base64.b64encode(cert).decode("ascii"),
                    media_type="application/pkix-cert",
                )
            )
            count.retained += len(cert)
        cipher = self.channel.ssl.cipher()
        assert cipher is not None
        return TlsMetadata(
            version=self.channel.ssl.version() or "unknown",
            cipher=cipher[0],
            secret_bits=cipher[2],
            alpn=self.channel.ssl.selected_alpn_protocol(),
            certificates=tuple(captured),
            chain_truncated=len(captured) != len(certs),
        )
