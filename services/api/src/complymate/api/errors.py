"""Maps domain errors to HTTP responses with a stable error envelope: {"error": {"code", "message"}}."""

from __future__ import annotations

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from complymate.domain.errors import (
    Conflict,
    DomainError,
    Forbidden,
    NotFound,
    PlanLimitReached,
    StepUpRequired,
    ValidationFailed,
)

log = structlog.get_logger(__name__)

STATUS = {
    NotFound: 404,
    StepUpRequired: 401,
    Forbidden: 403,
    Conflict: 409,
    ValidationFailed: 422,
    PlanLimitReached: 402,
}


class Unauthorized(DomainError):
    code = "unauthorized"


def _body(code: str, message: str, request: Request) -> dict[str, object]:
    return {"error": {"code": code, "message": message, "request_id": getattr(request.state, "request_id", None)}}


def install(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error(request: Request, exc: DomainError) -> JSONResponse:
        status = (
            401
            if isinstance(exc, Unauthorized)
            else next((code for cls, code in STATUS.items() if isinstance(exc, cls)), 400)
        )
        headers = (
            {"WWW-Authenticate": 'Bearer error="insufficient_user_authentication"'}
            if isinstance(exc, StepUpRequired)
            else None
        )
        return JSONResponse(_body(exc.code, str(exc), request), status_code=status, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        body = _body("validation_failed", "request is invalid", request)
        body["error"]["details"] = [  # type: ignore[index]
            {"loc": list(e.get("loc", ())), "msg": e.get("msg"), "type": e.get("type")} for e in exc.errors()
        ]
        return JSONResponse(body, status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(_body(f"http_{exc.status_code}", str(exc.detail), request), status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled_error", path=request.url.path)
        return JSONResponse(_body("internal_error", "something went wrong", request), status_code=500)
