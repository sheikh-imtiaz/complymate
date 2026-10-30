from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from complymate.db.repositories.audit import AuditRepo
from complymate.db.session import tenant_session
from complymate.domain.audit.events import AuditContext
from complymate.domain.audit.service import AuditService

SYSTEM = AuditContext(actor_id=None, actor_role="system", tenant_id=None)


async def active_tenant_ids() -> list[UUID]:
    async with tenant_session(None) as session:
        rows = await session.execute(text("SELECT app_active_tenant_ids()"))
        return [r[0] for r in rows.all()]


async def system_audit(
    session: AsyncSession, tenant_id: UUID | None, action: str, resource_type: str, resource_id: Any, **kwargs: Any
) -> None:
    ctx = AuditContext(actor_id=None, actor_role="system", tenant_id=tenant_id)
    await AuditService(AuditRepo(session)).record(
        ctx, action, resource_type, resource_id, tenant_id=tenant_id, **kwargs
    )


def render(template: str, **context: Any) -> str:
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    from complymate.container import get_container

    env = Environment(loader=FileSystemLoader(get_container().settings.templates_dir), autoescape=select_autoescape())
    return env.get_template(template).render(**context)
