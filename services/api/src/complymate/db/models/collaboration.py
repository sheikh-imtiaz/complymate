from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from complymate.db.base import Base, CreatedMixin, IdMixin, TenantMixin


class Task(IdMixin, TenantMixin, CreatedMixin, Base):
    __tablename__ = "tasks"

    type: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    resource_type: Mapped[str | None] = mapped_column(String(40))
    resource_id: Mapped[str | None] = mapped_column(String(64))
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    created_by: Mapped[uuid.UUID | None]
    status: Mapped[str] = mapped_column(String(20), default="open")
    due_date: Mapped[date | None] = mapped_column(Date)
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_by: Mapped[uuid.UUID | None]


class Comment(IdMixin, TenantMixin, CreatedMixin, Base):
    __tablename__ = "comments"

    resource_type: Mapped[str] = mapped_column(String(40))
    resource_id: Mapped[str] = mapped_column(String(64), index=True)
    author_id: Mapped[uuid.UUID]
    body: Mapped[str] = mapped_column(Text)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Mention(IdMixin, TenantMixin, CreatedMixin, Base):
    __tablename__ = "mentions"

    comment_id: Mapped[uuid.UUID] = mapped_column(index=True)
    user_id: Mapped[uuid.UUID]


class Notification(IdMixin, TenantMixin, CreatedMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(index=True)
    kind: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(300))
    body: Mapped[str | None] = mapped_column(Text)
    link: Mapped[str | None] = mapped_column(Text)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    emailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Share(IdMixin, TenantMixin, CreatedMixin, Base):
    __tablename__ = "shares"

    resource_type: Mapped[str] = mapped_column(String(40))
    resource_id: Mapped[str] = mapped_column(String(64))
    grantee_user_id: Mapped[uuid.UUID] = mapped_column(index=True)
    granted_by: Mapped[uuid.UUID]
    permission: Mapped[str] = mapped_column(String(20), default="read")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PresenceHeartbeat(Base):
    __tablename__ = "presence_heartbeats"

    tenant_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    resource_type: Mapped[str] = mapped_column(String(40), primary_key=True)
    resource_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
