"""Chat streaming.

* `run_chat_turn` — one agent turn inside the caller's RLS session: permission checks, usage metering, agent
  stream, persistence, audit (model, prompt version, sources, tool calls) and LLM cost.
* `/ws/chat` — native WebSocket (local, Azure Container Apps).
* `handle_apigw_event` — API Gateway WebSocket events on AWS ($connect / chat / $disconnect), pushing tokens back
  with the management API.

Protocol (both transports): client sends {"action": "chat", "message", "session_id"?, "client_id"?, "token"?,
"tenant_id"?}; server sends {"type": "citations"|"token"|"replace"|"blocked"|"done"|"error", "data": ...}.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.datastructures import Headers

from complymate.agent.factory import RulesChatAgent
from complymate.agent.guardrails import DISCLAIMER
from complymate.application import llm_usage
from complymate.application.usage import meter
from complymate.db.models import ChatMessage, ChatSession, Tenant
from complymate.domain.audit.events import Action
from complymate.domain.errors import DomainError, Forbidden, NotFound
from complymate.domain.rbac.permissions import P
from complymate.domain.rbac.policy import authorize
from complymate.ports.llm import ChatMessage as LlmMessage

log = structlog.get_logger(__name__)
router = APIRouter()


async def run_chat_turn(
    ctx: Any, message: str, session_id: UUID | None, client_id: UUID | None
) -> AsyncIterator[dict[str, Any]]:
    from sqlalchemy import select

    from complymate.db.repositories.tenants import TenantRepo
    from complymate.domain.platform.feature_flags import resolve

    g, t = await TenantRepo(ctx.session).flags(ctx.tenant_id)
    if not resolve(g, t).get("ask_rules_chat", True):
        raise Forbidden("Ask the Rules is turned off for this firm")
    limit = await meter(ctx.session, ctx.tenant_id, "agent_turns")

    if session_id:
        chat_session = await ctx.session.get(ChatSession, session_id)
        if chat_session is None or chat_session.user_id != ctx.user_id:
            raise NotFound("conversation not found")
    else:
        chat_session = ChatSession(tenant_id=ctx.tenant_id, user_id=ctx.user_id, title=message[:80])
        ctx.session.add(chat_session)
        await ctx.session.flush()

    history_rows = (
        (
            await ctx.session.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == chat_session.id)
                .order_by(ChatMessage.created_at.desc())
                .limit(8)
            )
        )
        .scalars()
        .all()
    )
    history = [LlmMessage(m.role, m.content) for m in reversed(history_rows)]  # type: ignore[arg-type]
    ctx.session.add(ChatMessage(tenant_id=ctx.tenant_id, session_id=chat_session.id, role="user", content=message))

    tenant = await ctx.session.get(Tenant, ctx.tenant_id)
    agent = RulesChatAgent(
        ctx.container.llm, ctx.container.embeddings, ctx.session, ctx.principal, tenant.jurisdiction if tenant else "AU"
    )
    if limit.warning and limit.message:
        yield {"type": "notice", "data": limit.message}
    answer = None
    async for event in agent.stream(message, history, client_id):
        if event.type == "done":
            answer = event.data
        else:
            yield {"type": event.type, "data": event.data}
    assert answer is not None

    cost = llm_usage.cost_usd(ctx.container.settings, answer.input_tokens, answer.output_tokens)
    reply = ChatMessage(
        tenant_id=ctx.tenant_id,
        session_id=chat_session.id,
        role="assistant",
        content=answer.text,
        citations=answer.citations,
        model=answer.model,
        prompt_version=ctx.container.settings.prompt_version,
        tool_calls=answer.tool_calls,
        input_tokens=answer.input_tokens,
        output_tokens=answer.output_tokens,
        cost_usd=cost,
        guardrail_action=",".join(answer.flags) or None,
    )
    ctx.session.add(reply)
    await ctx.session.flush()
    await llm_usage.record(
        ctx.session,
        ctx.container.settings,
        tenant_id=ctx.tenant_id,
        purpose="rules_chat",
        model=answer.model,
        input_tokens=answer.input_tokens,
        output_tokens=answer.output_tokens,
        latency_ms=answer.latency_ms,
    )
    await ctx.record(
        Action.AI_SUGGESTION,
        "chat_message",
        reply.id,
        ai={
            "model": answer.model,
            "prompt_version": ctx.container.settings.prompt_version,
            "sources": [c["title"] for c in answer.citations],
            "tool_calls": answer.tool_calls,
            "flags": answer.flags,
            "blocked": answer.blocked,
        },
    )
    yield {
        "type": "done",
        "data": {
            "session_id": str(chat_session.id),
            "message_id": str(reply.id),
            "answer": answer.text,
            "citations": answer.citations,
            "model": answer.model,
            "disclaimer": DISCLAIMER,
        },
    }


class _FakeRequest:
    """Adapts WebSocket / API Gateway event data to the attributes `authenticate` reads."""

    def __init__(self, token: str | None, tenant_id: str | None, path: str = "/ws/chat") -> None:
        headers = {}
        if token:
            headers["authorization"] = f"Bearer {token}"
        if tenant_id:
            headers["x-tenant-id"] = tenant_id
        self.headers = Headers(headers)
        self.query_params: dict[str, str] = {}

        class _Url:
            pass

        self.url = _Url()
        self.url.path = path  # type: ignore[attr-defined]


async def _turn_with_auth(
    token: str | None, tenant_id: str | None, payload: dict[str, Any], ip: str | None
) -> AsyncIterator[dict[str, Any]]:
    from complymate.api.deps import Ctx, _tenant_guards, authenticate
    from complymate.container import get_container
    from complymate.db.session import apply_context

    container = get_container()
    maker = await container.sessionmaker()
    async with maker() as session, session.begin():
        principal, user = await authenticate(_FakeRequest(token, tenant_id), session, container)  # type: ignore[arg-type]
        await apply_context(session, principal.tenant_id, user_id=principal.user_id)
        ctx = Ctx(
            principal=principal,
            session=session,
            container=container,
            request_id=None,
            ip=ip,
            user_agent="websocket",
            user=user,
        )
        if principal.tenant_id is None:
            raise Forbidden("select a firm first")
        await _tenant_guards(ctx)
        authorize(principal, P.CHAT_USE)
        async for event in run_chat_turn(
            ctx,
            str(payload.get("message", ""))[:4000],
            UUID(payload["session_id"]) if payload.get("session_id") else None,
            UUID(payload["client_id"]) if payload.get("client_id") else None,
        ):
            yield event


@router.websocket("/ws/chat")
async def chat_socket(ws: WebSocket) -> None:
    await ws.accept()
    token = ws.query_params.get("token")
    tenant_id = ws.query_params.get("tenant")
    try:
        while True:
            payload = json.loads(await ws.receive_text())
            if payload.get("action") == "ping":
                await ws.send_json({"type": "pong"})
                continue
            try:
                async for event in _turn_with_auth(
                    payload.get("token") or token,
                    payload.get("tenant_id") or tenant_id,
                    payload,
                    ws.client.host if ws.client else None,
                ):
                    await ws.send_text(json.dumps(event, default=str))
            except DomainError as exc:
                await ws.send_json({"type": "error", "data": {"code": exc.code, "message": str(exc)}})
            except Exception as exc:
                log.exception("ws.chat_failed")
                await ws.send_json({"type": "error", "data": {"code": "internal_error", "message": type(exc).__name__}})
    except WebSocketDisconnect:
        return


async def handle_apigw_event(event: dict[str, Any]) -> dict[str, Any]:
    """AWS API Gateway WebSocket: auth on $connect (querystring token), stream on the `chat` route."""
    from complymate.container import get_container

    rc = event.get("requestContext", {})
    route = rc.get("routeKey")
    connection_id = rc.get("connectionId")
    if route == "$connect":
        qs = event.get("queryStringParameters") or {}
        try:
            await get_container().identity.verify_token(qs.get("token", ""))
        except Exception:
            return {"statusCode": 401}
        return {"statusCode": 200}
    if route == "$disconnect":
        return {"statusCode": 200}

    pusher = get_container().realtime
    try:
        payload = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return {"statusCode": 400}
    if payload.get("action") == "ping":
        await pusher.push(connection_id, {"type": "pong"})
        return {"statusCode": 200}
    try:
        async for item in _turn_with_auth(
            payload.get("token"), payload.get("tenant_id"), payload, rc.get("identity", {}).get("sourceIp")
        ):
            if not await pusher.push(connection_id, item):
                break
    except DomainError as exc:
        await pusher.push(connection_id, {"type": "error", "data": {"code": exc.code, "message": str(exc)}})
    except Exception:
        log.exception("apigw_ws.chat_failed")
        await pusher.push(
            connection_id, {"type": "error", "data": {"code": "internal_error", "message": "chat failed"}}
        )
    return {"statusCode": 200}
