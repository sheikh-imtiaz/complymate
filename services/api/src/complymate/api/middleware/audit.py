"""Captures client IP and user agent for audit events, and logs one access line per request (no PII)."""

from __future__ import annotations

import time
from contextvars import ContextVar

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

client_ip_var: ContextVar[str | None] = ContextVar("client_ip", default=None)
user_agent_var: ContextVar[str | None] = ContextVar("user_agent", default=None)
log = structlog.get_logger("access")


def _client_ip(scope: Scope) -> str | None:
    headers = dict(scope.get("headers") or [])
    forwarded = headers.get(b"x-forwarded-for", b"").decode()
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = scope.get("client")
    return client[0] if client else None


class AuditContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        ip_token = client_ip_var.set(_client_ip(scope))
        ua_token = user_agent_var.set(dict(scope.get("headers") or []).get(b"user-agent", b"").decode()[:400] or None)
        start = time.perf_counter()
        status = {"code": 500}

        async def capture(message: Message) -> None:
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, capture)
        finally:
            if scope.get("path") != "/health":
                log.info(
                    "request",
                    method=scope.get("method"),
                    path=scope.get("path"),
                    status=status["code"],
                    duration_ms=round((time.perf_counter() - start) * 1000, 1),
                )
            client_ip_var.reset(ip_token)
            user_agent_var.reset(ua_token)
