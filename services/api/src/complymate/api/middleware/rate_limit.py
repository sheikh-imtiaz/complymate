"""Token-bucket rate limit per API key / bearer token / IP. In-process: on Lambda it limits per instance;
API Gateway throttling and AWS WAF rate rules are the shared limit."""

from __future__ import annotations

import hashlib
import time

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

LIMITS = {"/chat": (20, 60.0), "/auth": (30, 60.0)}
DEFAULT = (240, 60.0)


class RateLimitMiddleware:
    def __init__(self, app: ASGIApp, max_keys: int = 50_000) -> None:
        self.app = app
        self.buckets: dict[str, tuple[float, float]] = {}
        self.max_keys = max_keys

    def _key(self, scope: Scope) -> tuple[str, tuple[int, float]]:
        headers = dict(scope.get("headers") or [])
        ident = headers.get(b"x-api-key") or headers.get(b"authorization") or headers.get(b"x-forwarded-for") or b""
        if not ident and scope.get("client"):
            ident = scope["client"][0].encode()
        path = scope.get("path", "")
        limit = next((v for p, v in LIMITS.items() if path.startswith(p)), DEFAULT)
        prefix = next((p for p in LIMITS if path.startswith(p)), "*")
        return prefix + ":" + hashlib.sha256(ident).hexdigest()[:24], limit

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") in ("/health", "/events"):
            await self.app(scope, receive, send)
            return
        key, (capacity, window) = self._key(scope)
        now = time.monotonic()
        tokens, last = self.buckets.get(key, (float(capacity), now))
        tokens = min(float(capacity), tokens + (now - last) * capacity / window)
        if tokens < 1:
            response = JSONResponse(
                {"error": {"code": "rate_limited", "message": "too many requests"}},
                status_code=429,
                headers={"Retry-After": str(int(window / capacity) + 1)},
            )
            await response(scope, receive, send)
            return
        if len(self.buckets) > self.max_keys:
            self.buckets.clear()
        self.buckets[key] = (tokens - 1, now)
        await self.app(scope, receive, send)
