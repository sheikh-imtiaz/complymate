"""Puts the requested tenant id into the logging context early. Authorisation happens in api/deps.py."""

from __future__ import annotations

import uuid

from starlette.types import ASGIApp, Receive, Scope, Send

from complymate.observability.logging import tenant_id_var


class TenantContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        raw = dict(scope.get("headers") or []).get(b"x-tenant-id", b"").decode()
        try:
            value = str(uuid.UUID(raw)) if raw else None
        except ValueError:
            value = None
        token = tenant_id_var.set(value)
        try:
            await self.app(scope, receive, send)
        finally:
            tenant_id_var.reset(token)
