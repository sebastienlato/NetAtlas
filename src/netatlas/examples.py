"""Synthetic documentation fixture, never a measured Internet service."""

import base64

from netatlas import __version__
from netatlas.config import Settings
from netatlas.observation import Observation


def example_observation(settings: Settings) -> Observation:
    return Observation.model_validate(
        {
            "observation_id": "00000000-0000-4000-8000-000000000001",
            "target": {
                "address": "192.0.2.10",
                "source": "synthetic-documentation-fixture",
                "campaign_id": "phase-0-demo",
            },
            "endpoint": {"address": "192.0.2.10", "port": 80, "transport": "tcp"},
            "scanner": {"node_id": "synthetic", "software_version": __version__},
            "config_sha256": settings.sha256,
            "started_at": "2026-10-04T12:00:00Z",
            "finished_at": "2026-10-04T12:00:00.025Z",
            "outcome": "open",
            "service": {"protocol": "http"},
            "response": {
                "body_base64": base64.b64encode(
                    b"HTTP/1.1 200 OK\r\nContent-Length: 16\r\n\r\nNetAtlas fixture"
                ).decode("ascii"),
                "media_type": "application/octet-stream",
            },
        }
    )
