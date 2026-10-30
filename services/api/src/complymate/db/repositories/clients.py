from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from uuid import UUID

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from complymate.db.models import (
    Client,
    ClientDocument,
    ClientParty,
    EddTask,
    RiskAssessment,
    ScreeningMatch,
    ScreeningRun,
    Share,
)
from complymate.domain.rbac.policy import Scope


class ClientRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    def _scoped(self, stmt, scope: Scope, user_id: UUID):  # type: ignore[no-untyped-def]
        if scope is Scope.OWN:
            return stmt.where(or_(Client.created_by == user_id, Client.assigned_to == user_id))
        if scope is Scope.SHARED:
            shared = select(Share.resource_id).where(
                Share.grantee_user_id == user_id,
                Share.resource_type == "client",
                Share.revoked_at.is_(None),
                Share.expires_at > func.now(),
            )
            return stmt.where(cast(Client.id, String).in_(shared))
        return stmt

    async def search(
        self,
        scope: Scope,
        user_id: UUID,
        *,
        q: str | None = None,
        status: str | None = None,
        risk: str | None = None,
        review_overdue: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[Client], int]:
        stmt = self._scoped(select(Client), scope, user_id)
        if q:
            stmt = stmt.where(Client.display_name.ilike(f"%{q}%"))
        if status:
            stmt = stmt.where(Client.status == status)
        if risk:
            stmt = (
                stmt.where(Client.risk_level == risk)
                if risk != "unassessed"
                else stmt.where(Client.risk_level.is_(None))
            )
        if review_overdue:
            stmt = stmt.where(Client.next_review_date < date.today(), Client.status == "approved")
        total = (await self.s.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        rows = (
            (await self.s.execute(stmt.order_by(Client.updated_at.desc()).limit(limit).offset(offset))).scalars().all()
        )
        return rows, total

    async def get(self, client_id: UUID) -> Client | None:
        return await self.s.get(Client, client_id)

    async def is_shared_with(self, client_id: UUID, user_id: UUID) -> bool:
        stmt = select(func.count()).where(
            Share.resource_type == "client",
            Share.resource_id == str(client_id),
            Share.grantee_user_id == user_id,
            Share.revoked_at.is_(None),
            Share.expires_at > func.now(),
        )
        return (await self.s.execute(stmt)).scalar_one() > 0

    async def parties(self, client_id: UUID) -> Sequence[ClientParty]:
        stmt = select(ClientParty).where(ClientParty.client_id == client_id).order_by(ClientParty.created_at)
        return (await self.s.execute(stmt)).scalars().all()

    async def documents(self, client_id: UUID) -> Sequence[ClientDocument]:
        stmt = (
            select(ClientDocument)
            .where(ClientDocument.client_id == client_id)
            .order_by(ClientDocument.created_at.desc())
        )
        return (await self.s.execute(stmt)).scalars().all()

    async def latest_assessment(self, client_id: UUID) -> RiskAssessment | None:
        stmt = (
            select(RiskAssessment)
            .where(RiskAssessment.client_id == client_id, RiskAssessment.status != "superseded")
            .order_by(RiskAssessment.created_at.desc())
            .limit(1)
        )
        return (await self.s.execute(stmt)).scalar_one_or_none()

    async def assessments(self, client_id: UUID) -> Sequence[RiskAssessment]:
        stmt = (
            select(RiskAssessment)
            .where(RiskAssessment.client_id == client_id)
            .order_by(RiskAssessment.created_at.desc())
        )
        return (await self.s.execute(stmt)).scalars().all()

    async def edd_tasks(self, client_id: UUID) -> Sequence[EddTask]:
        stmt = select(EddTask).where(EddTask.client_id == client_id).order_by(EddTask.created_at)
        return (await self.s.execute(stmt)).scalars().all()

    async def screening_state(self, client_id: UUID) -> tuple[bool, int, bool]:
        """(screened, open_matches, true_match)"""
        runs = (await self.s.execute(select(func.count()).where(ScreeningRun.client_id == client_id))).scalar_one()
        open_m = (
            await self.s.execute(
                select(func.count()).where(
                    ScreeningMatch.client_id == client_id, ScreeningMatch.status.in_(("open", "needs_info"))
                )
            )
        ).scalar_one()
        true_m = (
            await self.s.execute(
                select(func.count()).where(ScreeningMatch.client_id == client_id, ScreeningMatch.status == "true_match")
            )
        ).scalar_one()
        return runs > 0, open_m, true_m > 0

    async def active_ids(self) -> list[UUID]:
        stmt = select(Client.id).where(Client.status.in_(("approved", "pending")))
        return [r for (r,) in (await self.s.execute(stmt)).all()]

    async def reviews_due(self, before: date) -> Sequence[Client]:
        stmt = select(Client).where(Client.status == "approved", Client.next_review_date <= before)
        return (await self.s.execute(stmt)).scalars().all()
