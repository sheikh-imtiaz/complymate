"""Machine-to-machine prefix. On AWS the HTTP API JWT authorizer protects every route except `/m2m/*`, which is
reserved for API-key clients. This middleware strips the prefix and refuses requests without an API key."""

from __future__ import annotations

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

PREFIX = "/m2m"


class M2MPrefixMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope.get("path", "").startswith(PREFIX + "/"):
            headers = dict(scope.get("headers") or [])
            if b"x-api-key" not in headers or b"authorization" in headers:
                await JSONResponse({"error": {"code": "unauthorized", "message": "API key required"}}, 401)(
                    scope, receive, send
                )
                return
            scope = dict(scope)
            scope["path"] = scope["path"][len(PREFIX) :]
            scope["raw_path"] = scope["path"].encode()
        await self.app(scope, receive, send)
