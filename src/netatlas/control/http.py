"""Authenticated loopback-only control transport. No browser routes or target I/O."""

import asyncio
import hmac
from typing import Any

from fastapi import FastAPI, Request
from sqlalchemy.exc import SQLAlchemyError
from starlette.responses import JSONResponse

from netatlas.control.coordinator import Coordinator
from netatlas.control.files import Credentials
from netatlas.control.models import BODY_BYTES, ControlError, request_reader
from netatlas.derivations.offline import json_object


def create_control_app(
    coordinator: Coordinator, credentials: Credentials, port: int = 8001
) -> FastAPI:
    if len({item.worker_id for item in credentials.workers}) != 2:
        raise ValueError("distinct workers required")
    tokens = {str(item.worker_id): item.token for item in credentials.workers}
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    active = 0

    def response(status: int, value: Any) -> JSONResponse:
        return JSONResponse(
            value,
            status_code=status,
            headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
        )

    @app.post("/control/v1/exchange")
    async def exchange(request: Request) -> JSONResponse:
        nonlocal active
        admitted = False
        try:
            if (
                request.client is None
                or request.client.host not in ("127.0.0.1", "::1")
                or request.headers.get("host") not in (f"127.0.0.1:{port}", f"[::1]:{port}")
                or "origin" in request.headers
                or "cookie" in request.headers
                or request.headers.get("content-type") != "application/json"
                or "content-encoding" in request.headers
            ):
                raise ControlError(403, "forbidden")
            worker = request.headers.get("x-netatlas-worker", "")
            token = tokens.get(worker)
            if token is None or not hmac.compare_digest(
                request.headers.get("authorization", ""), "Bearer " + token
            ):
                raise ControlError(401, "unauthorized")
            if active >= 8:
                raise ControlError(429, "busy")
            active += 1
            admitted = True
            size = request.headers.get("content-length")
            if size and (not size.isdecimal() or len(size) > 10 or int(size) > BODY_BYTES):
                raise ControlError(413, "too_large")
            body = bytearray()
            async with asyncio.timeout(5):
                async for chunk in request.stream():
                    if len(body) + len(chunk) > BODY_BYTES:
                        raise ControlError(413, "too_large")
                    body.extend(chunk)
            document = json_object(bytes(body))
            if document.get("action") != "deliver" and len(body) > 16384:
                raise ControlError(413, "too_large")
            message = request_reader.validate_python(document)
            if str(message.worker_id) != worker:
                raise ControlError(401, "unauthorized")
            reply = await asyncio.to_thread(coordinator.exchange, message)
            return response(200, reply.model_dump(mode="json"))
        except ControlError as exc:
            return response(exc.status, {"error": {"code": exc.code}})
        except TimeoutError:
            return response(408, {"error": {"code": "request_timeout"}})
        except ValueError, RecursionError:
            return response(422, {"error": {"code": "invalid_request"}})
        except SQLAlchemyError, OSError:
            return response(503, {"error": {"code": "unavailable"}})
        except Exception:
            return response(500, {"error": {"code": "internal_error"}})
        finally:
            if admitted:
                active -= 1

    return app
