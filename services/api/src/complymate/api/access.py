"""Record-level access helpers (ABAC: own / shared) used by routers after `require(...)`."""

from __future__ import annotations

from uuid import UUID

from complymate.api.deps import Ctx
from complymate.db.models import Client
from complymate.db.repositories.clients import ClientRepo
from complymate.domain.errors import NotFound
from complymate.domain.rbac.policy import Scope, check_record_access


async def load_client(ctx: Ctx, client_id: UUID) -> Client:
    repo = ClientRepo(ctx.session)
    client = await repo.get(client_id)
    if client is None:  # RLS hides other tenants' rows, so this also covers cross-tenant ids
        raise NotFound("client not found")
    shared = {ctx.user_id} if ctx.scope is Scope.SHARED and await repo.is_shared_with(client_id, ctx.user_id) else set()
    check_record_access(ctx.scope, ctx.principal, owner_ids={client.created_by, client.assigned_to}, shared_with=shared)
    return client
