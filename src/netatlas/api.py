"""Loopback synthetic read API. Requests never invoke measurement or derivation."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from ipaddress import ip_address
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException
from starlette.responses import FileResponse, Response
from starlette.staticfiles import StaticFiles

from netatlas import __version__
from netatlas.config import Settings, load_settings
from netatlas.domain import Endpoint, Model
from netatlas.examples import example_observation
from netatlas.inspection.models import InspectionRequest, InspectionResponse
from netatlas.observation import Observation
from netatlas.operations.status import OperationsRequest, Ready, Snapshot, readiness, snapshot
from netatlas.operations.telemetry import ObserveHTTP, Telemetry
from netatlas.read_api.boundary import ReadBoundary, SafeJSONResponse, error
from netatlas.read_api.cursors import Cursors, ReadError
from netatlas.read_api.inspection import inspect_source
from netatlas.read_api.models import (
    EndpointRequest,
    ErrorResponse,
    PlacesRequest,
    PlacesResponse,
    SearchMetadata,
    SearchQuery,
    SearchRequest,
    SearchResponse,
)
from netatlas.read_api.service import Reader
from netatlas.storage.blobs import BlobStore
from netatlas.storage.database import local_engine
from netatlas.storage.pipeline import Pipeline


class Health(Model):
    status: Literal["ok"] = "ok"
    version: str = __version__
    phase: Literal[13] = 13
    measurement_enabled: Literal[False] = False


ReadHeader = Annotated[Literal["1"], Header(alias="X-NetAtlas-Read")]


def create_app(
    settings: Settings | None = None,
    *,
    engine: Engine | None = None,
    blobs: BlobStore | None = None,
    storage: Path = Path("data/storage"),
    blob_root: Path = Path("data/storage/blobs"),
    web_root: Path | None = None,
) -> FastAPI:
    resolved = settings or load_settings()
    owned: Engine | None = None
    cursors = Cursors()
    telemetry = Telemetry("read")
    root = blobs.root if blobs is not None else blob_root

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        if owned is not None:
            owned.dispose()

    app = FastAPI(
        title="NetAtlas",
        version=__version__,
        lifespan=lifespan,
        default_response_class=SafeJSONResponse,
        description=(
            "Local synthetic search and bounded inspection. No measurement or public access."
        ),
        responses={
            status: {"model": ErrorResponse}
            for status in (400, 403, 404, 405, 408, 410, 413, 415, 422, 429, 500, 503)
        },
    )
    app.add_middleware(ReadBoundary, api_port=resolved.api.port)
    app.add_middleware(ObserveHTTP, telemetry=telemetry)
    app.state.telemetry = telemetry

    def reader() -> Reader:
        nonlocal owned
        if engine is not None:
            return Reader(engine, cursors)
        if owned is None:
            try:
                owned = local_engine(storage)
            except OSError, ValueError, KeyError:
                raise ReadError(503, "unavailable") from None
        return Reader(owned, cursors)

    @app.exception_handler(ReadError)
    async def read_error(request: Request, exc: ReadError) -> SafeJSONResponse:
        return error(exc.status, exc.code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> SafeJSONResponse:
        return error(422, "invalid_request")

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError) -> SafeJSONResponse:
        return error(503, "unavailable")

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> SafeJSONResponse:
        return error(
            exc.status_code, "method_not_allowed" if exc.status_code == 405 else "not_found"
        )

    @app.get("/healthz", response_model=Health, operation_id="health")
    async def health() -> Health:
        return Health()

    @app.get("/readyz", response_model=Ready, operation_id="readiness")
    def ready(response: Response) -> Ready:
        result = readiness(lambda: reader().engine, root)
        response.status_code = 200 if result.status == "ready" else 503
        return result

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        return Response(telemetry.metrics(), media_type="text/plain; version=0.0.4")

    @app.post("/api/v1/operations", response_model=Snapshot, operation_id="operations")
    def operations(body: OperationsRequest, x_read: ReadHeader) -> Snapshot:
        try:
            return snapshot(reader().engine, root)
        except OSError, ValueError:
            raise ReadError(503, "unavailable") from None

    @app.get("/api/v1/examples/observation", response_model=Observation, operation_id="example")
    async def example() -> Observation:
        return example_observation(resolved)

    def run(body: SearchRequest, scope: str) -> SearchResponse:
        try:
            return reader().search(body, scope)
        except ValidationError:
            raise ReadError(500, "internal_error") from None
        except ValueError:
            raise ReadError(422, "invalid_request") from None

    @app.post("/api/v1/search", response_model=SearchResponse, operation_id="search")
    def search(body: SearchRequest, x_read: ReadHeader) -> SearchResponse:
        return run(body, "search")

    @app.post("/api/v1/facets", response_model=SearchMetadata, operation_id="facets")
    def facets(body: SearchRequest, x_read: ReadHeader) -> SearchMetadata:
        if body.cursor is not None:
            raise ReadError(422, "invalid_request")
        result = run(body, "facets")
        return SearchMetadata.model_validate(
            result.model_dump(exclude={"hits", "next_cursor", "page_limit_reached"})
        )

    @app.post("/api/v1/places", response_model=PlacesResponse, operation_id="places")
    def places(body: PlacesRequest, x_read: ReadHeader) -> PlacesResponse:
        return reader().places(body)

    def endpoint(
        body: EndpointRequest,
        address: str,
        transport: str,
        port: int,
        mode: Literal["current", "history"],
    ) -> SearchResponse:
        try:
            if "%" in address:
                raise ValueError("literal address required")
            literal = ip_address(address)
            if mode == "current" and body.cursor:
                raise ValueError("detail has no continuation")
            query = SearchQuery.model_validate(
                body.query.model_dump()
                | {
                    "network": f"{literal}/{literal.max_prefixlen}",
                    "port": port,
                    "transport": transport,
                    "mode": mode,
                    "limit": 1 if mode == "current" else body.query.limit,
                }
            )
        except ValueError:
            raise ReadError(422, "invalid_request") from None
        result = run(
            SearchRequest(schema_version=1, query=query, cursor=body.cursor), f"endpoint:{mode}"
        )
        if mode == "current" and not result.hits:
            raise ReadError(404, "not_found")
        return result

    @app.post(
        "/api/v1/endpoints/{address}/{transport}/{port}/detail",
        response_model=SearchResponse,
        operation_id="endpointDetail",
    )
    def detail(
        address: str,
        transport: Literal["tcp", "udp"],
        port: int,
        body: EndpointRequest,
        x_read: ReadHeader,
    ) -> SearchResponse:
        return endpoint(body, address, transport, port, "current")

    @app.post(
        "/api/v1/endpoints/{address}/{transport}/{port}/history",
        response_model=SearchResponse,
        operation_id="endpointHistory",
    )
    def history(
        address: str,
        transport: Literal["tcp", "udp"],
        port: int,
        body: EndpointRequest,
        x_read: ReadHeader,
    ) -> SearchResponse:
        return endpoint(body, address, transport, port, "history")

    @app.post(
        "/api/v1/endpoints/{address}/{transport}/{port}/inspection",
        response_model=InspectionResponse,
        operation_id="endpointInspection",
    )
    def inspection(
        address: str,
        transport: Literal["tcp", "udp"],
        port: int,
        body: InspectionRequest,
        x_read: ReadHeader,
    ) -> InspectionResponse:
        try:
            if "%" in address:
                raise ValueError("literal address required")
            key = Endpoint.model_validate(
                {"address": address, "transport": transport, "port": port}
            )
        except ValueError:
            raise ReadError(422, "invalid_request") from None
        try:
            pipeline = Pipeline(reader().engine, blobs or BlobStore(root, create=False))
            return inspect_source(pipeline, key, body)
        except OSError, ValueError:
            raise ReadError(503, "unavailable") from None

    if web_root is not None:
        web_root = web_root.resolve(strict=True)
        if not (web_root / "index.html").is_file():
            raise ValueError("built web assets required")
        index = web_root / "index.html"

        @app.get("/operations", include_in_schema=False)
        def dashboard() -> FileResponse:
            return FileResponse(index)

        app.mount("/", StaticFiles(directory=web_root, html=True), name="web")

    return app
