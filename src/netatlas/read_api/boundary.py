"""Loopback-only, bounded JSON admission. No CORS or forwarded identity trust."""

import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from netatlas.derivations.offline import json_object
from netatlas.read_api.cursors import ReadError

MAX_BODY = 16384
MAX_RESPONSE = 4 * 1024 * 1024


class SafeJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        raw = json.dumps(content, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
        raw = raw.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
        encoded = raw.encode()
        if len(encoded) > MAX_RESPONSE:
            raise ReadError(413, "response_too_large")
        return encoded


def error(status: int, code: str) -> SafeJSONResponse:
    return SafeJSONResponse({"error": {"code": code}}, status_code=status)


class ReadBoundary:
    def __init__(self, app: ASGIApp, api_port: int) -> None:
        self.app = app
        self.api_port = api_port
        self.active = False

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request = Request(scope, receive)
        path = scope["path"]
        data_route = path.startswith("/api/v1/") and not path.startswith("/api/v1/examples/")

        async def safe_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                message["headers"] = list(message["headers"]) + [
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                ]
            await send(message)

        admitted = False
        try:
            host = urlsplit("http://" + request.headers.get("host", ""))
            peer = scope.get("client")
            if (
                peer is None
                or peer[0] not in ("127.0.0.1", "::1")
                or host.hostname not in ("127.0.0.1", "::1", "localhost")
                or host.username is not None
                or host.password is not None
                or host.path
                or host.query
                or host.fragment
                or host.port not in (None, self.api_port, 5173)
            ):
                raise ReadError(403, "forbidden")
            origin = request.headers.get("origin")
            allowed = {
                f"http://{h}:{p}"
                for h in ("127.0.0.1", "[::1]", "localhost")
                for p in (self.api_port, 5173)
            }
            if origin is not None and origin not in allowed:
                raise ReadError(403, "forbidden")
            if data_route:
                if request.headers.get("x-netatlas-read") != "1":
                    raise ReadError(403, "forbidden")
                if self.active:
                    raise ReadError(429, "busy")
                self.active = admitted = True
                if request.method == "POST":
                    if request.headers.get("content-type", "").split(";")[
                        0
                    ].strip() != "application/json" or request.headers.get("content-encoding"):
                        raise ReadError(415, "unsupported_media_type")
                    size = request.headers.get("content-length")
                    if size and (not size.isdecimal() or int(size) > MAX_BODY):
                        raise ReadError(413, "too_large")
                    body = bytearray()
                    async with asyncio.timeout(5):
                        async for chunk in request.stream():
                            if len(body) + len(chunk) > MAX_BODY:
                                raise ReadError(413, "too_large")
                            body.extend(chunk)
                    json_object(
                        bytes(body)
                    )  # rejects duplicate keys, excessive depth and missing version
                    consumed = False

                    async def bounded_receive() -> Message:
                        nonlocal consumed
                        if not consumed:
                            consumed = True
                            return {"type": "http.request", "body": bytes(body), "more_body": False}
                        return await receive()

                    await self.app(scope, bounded_receive, safe_send)
                    return
            await self.app(scope, receive, safe_send)
        except ReadError as exc:
            await error(exc.status, exc.code)(scope, receive, safe_send)
        except TimeoutError:
            await error(408, "request_timeout")(scope, receive, safe_send)
        except ValueError, RecursionError:
            await error(422, "invalid_request")(scope, receive, safe_send)
        except Exception:
            await error(500, "internal_error")(scope, receive, safe_send)
        finally:
            if admitted:
                self.active = False
