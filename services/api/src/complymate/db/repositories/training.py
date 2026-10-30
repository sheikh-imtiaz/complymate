from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from complymate.db.models import QuizAttempt, QuizQuestion, TrainingAssignment, TrainingModule


class TrainingRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def modules(self, jurisdiction: str, published_only: bool = True) -> Sequence[TrainingModule]:
        stmt = select(TrainingModule).where(TrainingModule.jurisdiction == jurisdiction)
        if published_only:
            stmt = stmt.where(TrainingModule.status == "published")
        return (await self.s.execute(stmt.order_by(TrainingModule.title))).scalars().all()

    async def approved_questions(self, module_id: UUID) -> Sequence[QuizQuestion]:
        stmt = select(QuizQuestion).where(QuizQuestion.module_id == module_id, QuizQuestion.review_status == "approved")
        return (await self.s.execute(stmt.order_by(QuizQuestion.created_at))).scalars().all()

    async def questions(
        self, module_id: UUID | None = None, review_status: str | None = None
    ) -> Sequence[QuizQuestion]:
        stmt = select(QuizQuestion)
        if module_id:
            stmt = stmt.where(QuizQuestion.module_id == module_id)
        if review_status:
            stmt = stmt.where(QuizQuestion.review_status == review_status)
        return (await self.s.execute(stmt.order_by(QuizQuestion.created_at.desc()))).scalars().all()

    async def assignments(self, user_id: UUID | None = None) -> Sequence[TrainingAssignment]:
        stmt = select(TrainingAssignment)
        if user_id:
            stmt = stmt.where(TrainingAssignment.user_id == user_id)
        return (await self.s.execute(stmt)).scalars().all()

    async def attempts(self, user_id: UUID | None = None, module_id: UUID | None = None) -> Sequence[QuizAttempt]:
        stmt = select(QuizAttempt)
        if user_id:
            stmt = stmt.where(QuizAttempt.user_id == user_id)
        if module_id:
            stmt = stmt.where(QuizAttempt.module_id == module_id)
        return (await self.s.execute(stmt.order_by(QuizAttempt.completed_at.desc()))).scalars().all()

    async def assignment(self, module_id: UUID, user_id: UUID) -> TrainingAssignment | None:
        stmt = select(TrainingAssignment).where(
            TrainingAssignment.module_id == module_id, TrainingAssignment.user_id == user_id
        )
        return (await self.s.execute(stmt)).scalar_one_or_none()

    async def visible_module(self, module_id: UUID) -> TrainingModule | None:
        stmt = select(TrainingModule).where(
            TrainingModule.id == module_id,
            or_(TrainingModule.status == "published", TrainingModule.tenant_id.is_not(None)),
        )
        return (await self.s.execute(stmt)).scalar_one_or_none()
