import base64
import json
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from netatlas.api import create_app
from netatlas.config import Settings, load_settings
from netatlas.domain import CapturedResponse
from netatlas.examples import example_observation
from netatlas.observation import Observation


def test_api_contract_and_synthetic_provenance() -> None:
    with TestClient(
        create_app(Settings()), base_url="http://127.0.0.1", client=("127.0.0.1", 50000)
    ) as client:
        assert client.get("/healthz").json() == {
            "status": "ok",
            "version": "0.11.0",
            "phase": 10,
            "measurement_enabled": False,
        }
        response = client.get("/api/v1/examples/observation")
        assert response.status_code == 200
        observation = Observation.model_validate(response.json())
        assert observation.target.source == "synthetic-documentation-fixture"
        assert str(observation.endpoint.address) == "192.0.2.10"
        assert observation.response is not None
        assert base64.b64decode(observation.response.body_base64).endswith(b"NetAtlas fixture")
        assert client.get("/openapi.json").json()["info"]["title"] == "NetAtlas"
        assert (
            client.post(
                "/api/v1/scan", headers={"X-NetAtlas-Read": "1"}, json={"schema_version": 1}
            ).status_code
            == 404
        )


def test_config_precedence_and_digest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NETATLAS_CONFIG", raising=False)
    assert load_settings(Path("config/default.toml")) == Settings()
    custom = tmp_path / "custom.toml"
    custom.write_text("[api]\nport = 8100\n", encoding="utf-8")
    monkeypatch.setenv("NETATLAS_CONFIG", str(custom))
    assert load_settings().api.port == 8100
    assert load_settings().sha256 != Settings().sha256
    assert load_settings(Path("config/default.toml")).api.port == 8000
    custom.write_text("[measurement]\nmax_concurency = 4\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_settings()


@pytest.mark.parametrize(
    "fragment",
    [
        {"enabled": True},
        {"max_concurrency": 0},
        {"connect_timeout_seconds": 0},
        {"max_response_bytes": 65537},
        {"exclusion_cidrs": ["not-a-network"]},
        {"user_agent": "Agent\r\nInjected: value"},
    ],
)
def test_invalid_measurement_settings_fail_closed(fragment: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({"measurement": fragment})


def test_observation_roundtrip_and_invariants() -> None:
    observation = example_observation(Settings())
    assert Observation.model_validate_json(observation.model_dump_json()) == observation
    patches: list[dict[str, object]] = [
        {"finished_at": "2026-10-03T12:00:00Z"},
        {"started_at": "2026-10-04T12:00:00"},
        {"endpoint": {"address": "192.0.2.11", "port": 80}},
        {"endpoint": {"address": "192.0.2.10", "port": 0}},
        {"outcome": "closed"},
        {"schema_version": 3},
    ]
    for patch in patches:
        with pytest.raises(ValidationError):
            Observation.model_validate(observation.model_dump(mode="json") | patch)


@pytest.mark.parametrize("encoded", ["bad-base64", base64.b64encode(b"x" * 65537).decode()])
def test_response_bytes_are_valid_and_bounded(encoded: str) -> None:
    with pytest.raises(ValidationError):
        CapturedResponse(body_base64=encoded)


def test_cli_installed_entrypoint() -> None:
    result = subprocess.run(
        ["netatlas", "config-check"], capture_output=True, text=True, check=True
    )
    assert json.loads(result.stdout)["measurement_enabled"] is False
