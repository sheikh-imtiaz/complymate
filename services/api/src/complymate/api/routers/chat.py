"""'Ask the Rules' chat. POST /chat streams Server-Sent Events (local / Azure) or returns JSON (stream=false).
On AWS the web app streams over the API Gateway WebSocket (api/ws/chat.py) because HTTP API buffers responses."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from complymate.api.deps import Ctx, require
from complymate.api.ws.chat import run_chat_turn
from complymate.db.models import AiFeedback, ChatMessage, ChatSession
from complymate.domain.audit.events import Action
from complymate.domain.errors import NotFound
from complymate.domain.rbac.permissions import P
from complymate.schemas.chat import ChatAnswer, ChatIn, FeedbackIn, MessageOut, SessionOut
from complymate.schemas.common import Ok

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatAnswer)
async def chat(body: ChatIn, ctx: Ctx = Depends(require(P.CHAT_USE))) -> object:
    if not body.stream:
        final: dict[str, object] = {}
        async for event in run_chat_turn(ctx, body.message, body.session_id, body.client_id):
            if event["type"] == "done":
                final = event["data"]  # type: ignore[assignment]
        return final

    # Collect inside the request transaction, then stream (DB work must finish before the dependency exits).
    events = [e async for e in run_chat_turn(ctx, body.message, body.session_id, body.client_id)]

    async def sse() -> AsyncIterator[bytes]:
        for e in events:
            yield f"event: {e['type']}\ndata: {json.dumps(e['data'], default=str)}\n\n".encode()

    return StreamingResponse(sse(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.get("/sessions", response_model=list[SessionOut])
async def sessions(ctx: Ctx = Depends(require(P.CHAT_USE))) -> list[object]:
    stmt = (
        select(ChatSession).where(ChatSession.user_id == ctx.user_id).order_by(ChatSession.created_at.desc()).limit(50)
    )
    return list((await ctx.session.execute(stmt)).scalars().all())


@router.get("/sessions/{session_id}/messages", response_model=list[MessageOut])
async def messages(session_id: UUID, ctx: Ctx = Depends(require(P.CHAT_USE))) -> list[object]:
    chat_session = await ctx.session.get(ChatSession, session_id)
    if chat_session is None or chat_session.user_id != ctx.user_id:
        raise NotFound("conversation not found")
    stmt = select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at)
    return list((await ctx.session.execute(stmt)).scalars().all())


@router.post("/messages/{message_id}/feedback", response_model=Ok)
async def feedback(message_id: UUID, body: FeedbackIn, ctx: Ctx = Depends(require(P.CHAT_USE))) -> Ok:
    msg = await ctx.session.get(ChatMessage, message_id)
    if msg is None or msg.role != "assistant":
        raise NotFound("message not found")
    fb = AiFeedback(
        tenant_id=ctx.tenant_id,
        message_id=msg.id,
        user_id=ctx.user_id,
        rating=body.rating,
        comment=body.comment,
        review_status="open" if body.rating == "wrong" else "resolved",
    )
    ctx.session.add(fb)
    await ctx.session.flush()
    await ctx.record(
        Action.AI_REJECTED if body.rating == "wrong" else Action.AI_ACCEPTED,
        "chat_message",
        msg.id,
        ai={"feedback": body.rating, "model": msg.model, "prompt_version": msg.prompt_version},
    )
    return Ok()
