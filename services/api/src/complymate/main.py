"""FastAPI application. One container image runs it on AWS Lambda (Mangum), Azure Container Apps or locally."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from complymate import __version__
from complymate.api import errors
from complymate.api.middleware.audit import AuditContextMiddleware
from complymate.api.middleware.rate_limit import RateLimitMiddleware
from complymate.api.middleware.request_id import RequestIdMiddleware
from complymate.api.middleware.tenant_context import TenantContextMiddleware
from complymate.api.routers import (
    api_keys,
    audit,
    auth,
    billing,
    chat,
    clients,
    comments,
    documents,
    health,
    invitations,
    notifications,
    platform_admin,
    programs,
    reports,
    risk,
    roles,
    screening,
    shares,
    smr,
    tasks,
    tenants,
    training,
    users,
    webhooks_stripe,
)
from complymate.api.ws import chat as ws_chat
from complymate.config import get_settings
from complymate.container import get_container
from complymate.observability.logging import configure_logging
from complymate.observability.tracing import configure_tracing


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    container = get_container()
    if container.settings.is_local:
        # Local mode: run queued tasks in-process so OCR/screening/emails work without SQS.
        from complymate.adapters.local.memory_queue import InProcessWorkflows, MemoryQueue
        from complymate.workers.entry import dispatch

        if isinstance(container.queue, MemoryQueue):
            container.queue.dispatcher = dispatch
        if isinstance(container.workflows, InProcessWorkflows):
            container.workflows.dispatcher = dispatch
    yield
    await container.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, json_logs=not settings.is_local)
    app = FastAPI(
        title="ComplyMate API",
        version=__version__,
        description="AML/CTF compliance agent for small firms. General information, not legal advice.",
        lifespan=lifespan,
        docs_url="/docs" if settings.environment != "prod" else None,
        redoc_url=None,
    )
    errors.install(app)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(AuditContextMiddleware)
    app.add_middleware(TenantContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Tenant-Id",
            "X-Request-Id",
            "X-Impersonation-Id",
            "X-Break-Glass-Reason",
            "X-API-Key",
        ],
        expose_headers=["X-Request-Id", "Content-Disposition"],
    )
    app.add_middleware(RequestIdMiddleware)

    for module in (
        health,
        auth,
        tenants,
        users,
        invitations,
        roles,
        api_keys,
        programs,
        clients,
        documents,
        risk,
        screening,
        smr,
        chat,
        training,
        tasks,
        comments,
        shares,
        notifications,
        reports,
        audit,
        billing,
        webhooks_stripe,
        platform_admin,
    ):
        app.include_router(module.router)
    app.include_router(ws_chat.router)
    configure_tracing(settings, app)
    return app


app = create_app()
