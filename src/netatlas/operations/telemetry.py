"""Fixed-cardinality process telemetry. Never retain request/exception values."""

import json
import logging
import threading
import time
from typing import Literal

from starlette.types import ASGIApp, Message, Receive, Scope, Send

ROUTES = (
    "health",
    "readiness",
    "metrics",
    "operations",
    "search",
    "facets",
    "places",
    "detail",
    "history",
    "inspection",
    "control",
    "other",
)
BUCKETS = (0.01, 0.1, 1.0, 5.0, 15.0)


def route_name(path: str) -> str:
    fixed = {
        "/healthz": "health",
        "/readyz": "readiness",
        "/metrics": "metrics",
        "/api/v1/operations": "operations",
        "/control/v1/exchange": "control",
    }
    if path in fixed:
        return fixed[path]
    if path in ("/api/v1/search", "/api/v1/facets", "/api/v1/places"):
        return path.rsplit("/", 1)[1]
    parts = path.split("/")
    if (
        len(parts) == 8
        and parts[1:4] == ["api", "v1", "endpoints"]
        and parts[-1] in ("detail", "history", "inspection")
    ):
        return parts[-1]
    return "other"


class Telemetry:
    def __init__(self, service: Literal["read", "control"]):
        self.service = service
        self.started = time.monotonic()
        self.last_log = self.started
        self.lock = threading.Lock()
        self.counts = {(route, status): 0 for route in ROUTES for status in range(2, 6)}
        self.buckets = {route: [0] * (len(BUCKETS) + 1) for route in ROUTES}
        self.seconds = dict.fromkeys(ROUTES, 0.0)
        self.active = 0

    def record(self, route: str, status: int, elapsed: float) -> None:
        # Also constrain direct callers; no arbitrary labels may enter the registry.
        route = route if route in ROUTES else "other"
        group = status // 100 if 200 <= status < 600 else 5
        elapsed = max(0.0, min(elapsed, 86400.0))
        with self.lock:
            self.counts[route, group] += 1
            self.seconds[route] += elapsed
            for index, bound in enumerate((*BUCKETS, float("inf"))):
                self.buckets[route][index] += elapsed <= bound
            now = time.monotonic()
            if now - self.last_log >= 30:
                self.last_log = now
                logging.getLogger("netatlas.operations").info(
                    json.dumps(
                        {
                            "event": "http_summary",
                            "service": self.service,
                            "requests": sum(self.counts.values()),
                            "server_errors": sum(
                                n for (_, code), n in self.counts.items() if code == 5
                            ),
                            "client_errors": sum(
                                n for (_, code), n in self.counts.items() if code == 4
                            ),
                            "uptime_seconds": int(now - self.started),
                        },
                        separators=(",", ":"),
                    )
                )

    def metrics(self) -> str:
        with self.lock:
            lines = ["# TYPE netatlas_http_requests_total counter"]
            for (route, code), count in self.counts.items():
                labels = f'service="{self.service}",route="{route}",status_class="{code}xx"'
                lines.append(f"netatlas_http_requests_total{{{labels}}} {count}")
            lines.append("# TYPE netatlas_http_duration_seconds histogram")
            for route in ROUTES:
                labels = f'service="{self.service}",route="{route}"'
                for bound, count in zip((*BUCKETS, "+Inf"), self.buckets[route], strict=True):
                    lines.append(
                        f'netatlas_http_duration_seconds_bucket{{{labels},le="{bound}"}} {count}'
                    )
                lines.append(
                    f"netatlas_http_duration_seconds_count{{{labels}}} {self.buckets[route][-1]}"
                )
                lines.append(
                    f"netatlas_http_duration_seconds_sum{{{labels}}} {self.seconds[route]}"
                )
            lines += [
                "# TYPE netatlas_http_inflight gauge",
                f'netatlas_http_inflight{{service="{self.service}"}} {self.active}',
                "# TYPE netatlas_process_uptime_seconds gauge",
                f'netatlas_process_uptime_seconds{{service="{self.service}"}} '
                f"{time.monotonic() - self.started:.3f}",
            ]
            return "\n".join(lines) + "\n"


class ObserveHTTP:
    def __init__(self, app: ASGIApp, telemetry: Telemetry):
        self.app, self.telemetry = app, telemetry

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        start, status = time.monotonic(), 500
        with self.telemetry.lock:
            self.telemetry.active += 1

        async def observed(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, observed)
        finally:
            with self.telemetry.lock:
                self.telemetry.active -= 1
            self.telemetry.record(route_name(scope["path"]), status, time.monotonic() - start)
