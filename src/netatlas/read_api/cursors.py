"""Process-local authenticated cursors, bound to route, query and a fixed lifetime."""

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime
from typing import Any


class ReadError(Exception):
    def __init__(self, status: int, code: str) -> None:
        self.status, self.code = status, code


class Cursors:
    def __init__(self) -> None:
        self.key = secrets.token_bytes(32)

    def encode(self, payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        mac = hmac.digest(self.key, raw, "sha256")
        return base64.urlsafe_b64encode(mac + raw).decode()

    def decode(self, token: str, scope: str, query: str, now: datetime) -> dict[str, Any]:
        try:
            raw = base64.b64decode(token, altchars=b"-_", validate=True)
            if not hmac.compare_digest(raw[:32], hmac.digest(self.key, raw[32:], "sha256")):
                raise ValueError("signature")
            payload: dict[str, Any] = json.loads(raw[32:])
            if payload["v"] != 1 or payload["scope"] != scope or payload["query"] != query:
                raise ValueError("binding")
            if now.timestamp() >= payload["expires"]:
                raise ReadError(410, "cursor_expired")
            return payload
        except ValueError, KeyError, TypeError:
            raise ReadError(400, "invalid_cursor") from None


def query_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()
