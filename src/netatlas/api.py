"""Local foundation API. No persistence, querying, or scan controls yet."""

from typing import Literal

from fastapi import FastAPI

from netatlas import __version__
from netatlas.config import Settings, load_settings
from netatlas.domain import Model, Observation
from netatlas.examples import example_observation


class Health(Model):
    status: Literal["ok"] = "ok"
    version: str = __version__
    phase: Literal[1] = 1
    measurement_enabled: Literal[False] = False


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or load_settings()
    app = FastAPI(title="NetAtlas", version=__version__)

    @app.get("/healthz", response_model=Health)
    async def health() -> Health:
        return Health()

    @app.get("/api/v1/examples/observation", response_model=Observation)
    async def example() -> Observation:
        return example_observation(resolved)

    return app
