"""Tool: read a client's current risk rating and reasons. Runs inside the caller's RLS session and checks
the caller's permission first, so the agent can never see more than the user can."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from complymate.db.repositories.clients import ClientRepo
from complymate.domain.rbac.permissions import P
from complymate.domain.rbac.policy import Principal, Scope, scope_for


async def get_client_risk(session: AsyncSession, principal: Principal, client_id: UUID) -> dict[str, Any]:
    scope = scope_for(principal, P.RISK_READ)
    if scope is None:
        return {"error": "You do not have permission to view client risk."}
    repo = ClientRepo(session)
    client = await repo.get(client_id)
    if client is None:
        return {"error": "Client not found."}
    if scope is Scope.OWN and principal.user_id not in (client.created_by, client.assigned_to):
        return {"error": "You do not have permission to view this client."}
    if scope is Scope.SHARED and not await repo.is_shared_with(client.id, principal.user_id):
        return {"error": "You do not have permission to view this client."}
    assessment = await repo.latest_assessment(client.id)
    return {
        "client_type": client.client_type,
        "status": client.status,
        "risk_level": client.risk_level,
        "next_review_date": client.next_review_date.isoformat() if client.next_review_date else None,
        "reasons": [r["description"] for r in (assessment.reasons if assessment else [])],
        "rules_version": assessment.rules_version if assessment else None,
    }


def make_tool(session: AsyncSession, principal: Principal, sink: list[dict[str, Any]]) -> Any:
    from strands import tool

    @tool
    async def read_client_risk(client_id: str) -> dict[str, Any]:
        """Read the current risk rating, status and risk reasons for one of the firm's clients.

        Args:
            client_id: The client's UUID.
        """
        result = await get_client_risk(session, principal, UUID(client_id))
        sink.append({"tool": "read_client_risk", "client_id": client_id, "ok": "error" not in result})
        return result

    return read_client_risk
