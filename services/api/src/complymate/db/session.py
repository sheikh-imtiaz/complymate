"""Database sessions. Each request runs in one transaction that first sets `app.tenant_id` (and the platform
flag) with set_config(..., is_local => true), so PostgreSQL RLS policies see the caller's tenant."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from complymate.container import get_container


async def apply_context(
    session: AsyncSession, tenant_id: UUID | None, *, platform: bool = False, user_id: UUID | None = None
) -> None:
    await session.execute(
        text(
            "SELECT set_config('app.tenant_id', :tid, true), set_config('app.is_platform', :plat, true), "
            "set_config('app.user_id', :uid, true)"
        ),
        {"tid": str(tenant_id) if tenant_id else "", "plat": "on" if platform else "off", "uid": str(user_id or "")},
    )


@asynccontextmanager
async def tenant_session(
    tenant_id: UUID | None, *, platform: bool = False, user_id: UUID | None = None
) -> AsyncIterator[AsyncSession]:
    maker = await get_container().sessionmaker()
    async with maker() as session, session.begin():
        await apply_context(session, tenant_id, platform=platform, user_id=user_id)
        yield session
