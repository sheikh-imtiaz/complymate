from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from complymate.db.base import Base, CreatedMixin, IdMixin, TenantMixin

EMBEDDING_DIM = 1024


class KbSource(IdMixin, CreatedMixin, Base):
    """Rule library source document (AUSTRAC / DIA guidance). Global, managed by Content Managers."""

    __tablename__ = "kb_sources"

    jurisdiction: Mapped[str] = mapped_column(String(2))
    title: Mapped[str] = mapped_column(String(300))
    url: Mapped[str | None] = mapped_column(Text)
    publisher: Mapped[str] = mapped_column(String(100))
    doc_type: Mapped[str] = mapped_column(String(40), default="guidance")
    storage_key: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="active")
    chunk_count: Mapped[int] = mapped_column(default=0)


class KbChunk(IdMixin, Base):
    __tablename__ = "kb_chunks"

    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("kb_sources.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int]
    heading: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    tokens: Mapped[int] = mapped_column(default=0)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", default=dict)


class ChatSession(IdMixin, TenantMixin, CreatedMixin, Base):
    __tablename__ = "chat_sessions"

    user_id: Mapped[uuid.UUID]
    title: Mapped[str] = mapped_column(String(200), default="New conversation")


class ChatMessage(IdMixin, TenantMixin, CreatedMixin, Base):
    __tablename__ = "chat_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    citations: Mapped[list[Any]] = mapped_column(default=list)
    model: Mapped[str | None] = mapped_column(String(120))
    prompt_version: Mapped[str | None] = mapped_column(String(40))
    tool_calls: Mapped[list[Any]] = mapped_column(default=list)
    input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 5), default=0)
    guardrail_action: Mapped[str | None] = mapped_column(String(40))


class AiFeedback(IdMixin, TenantMixin, CreatedMixin, Base):
    __tablename__ = "ai_feedback"

    message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_messages.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID]
    rating: Mapped[str] = mapped_column(String(20))
    comment: Mapped[str | None] = mapped_column(Text)
    review_status: Mapped[str] = mapped_column(String(20), default="open")
    reviewed_by: Mapped[uuid.UUID | None]
    resolution: Mapped[str | None] = mapped_column(Text)


class LlmCall(IdMixin, CreatedMixin, Base):
    __tablename__ = "llm_calls"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    purpose: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(120))
    prompt_version: Mapped[str | None] = mapped_column(String(40))
    input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 5), default=0)
    latency_ms: Mapped[int] = mapped_column(default=0)
