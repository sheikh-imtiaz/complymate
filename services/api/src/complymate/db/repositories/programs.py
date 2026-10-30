from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from complymate.db.models import Program, ProgramApproval, ProgramSection, ProgramVersion
from complymate.domain.programs.interview import SECTIONS


class ProgramRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def for_tenant(self, tenant_id: UUID) -> Program | None:
        return (await self.s.execute(select(Program).where(Program.tenant_id == tenant_id))).scalar_one_or_none()

    async def ensure(self, tenant_id: UUID, user_id: UUID) -> Program:
        program = await self.for_tenant(tenant_id)
        if program is None:
            program = Program(tenant_id=tenant_id, created_by=user_id, status="draft")
            self.s.add(program)
            await self.s.flush()
            version = await self.new_version(program, user_id, None)
            program.current_version_id = version.id
            await self.s.flush()
        return program

    async def new_version(self, program: Program, user_id: UUID, copy_from: ProgramVersion | None) -> ProgramVersion:
        versions = await self.versions(program.id)
        number = (max((v.version_number for v in versions), default=0)) + 1
        version = ProgramVersion(
            tenant_id=program.tenant_id,
            program_id=program.id,
            version_number=number,
            created_by=user_id,
            status="draft",
            change_summary=None if copy_from is None else f"Based on version {copy_from.version_number}",
        )
        self.s.add(version)
        await self.s.flush()
        previous = {s.key: s for s in await self.sections(copy_from.id)} if copy_from else {}
        for pos, sdef in enumerate(SECTIONS):
            prev = previous.get(sdef.key)
            self.s.add(
                ProgramSection(
                    tenant_id=program.tenant_id,
                    version_id=version.id,
                    key=sdef.key,
                    title=sdef.title,
                    position=pos,
                    content_html=prev.content_html if prev else "",
                    citations=prev.citations if prev else [],
                    ai_generated=prev.ai_generated if prev else False,
                    ai_accepted=prev.ai_accepted if prev else None,
                )
            )
        await self.s.flush()
        return version

    async def versions(self, program_id: UUID) -> Sequence[ProgramVersion]:
        stmt = (
            select(ProgramVersion)
            .where(ProgramVersion.program_id == program_id)
            .order_by(ProgramVersion.version_number.desc())
        )
        return (await self.s.execute(stmt)).scalars().all()

    async def version(self, version_id: UUID) -> ProgramVersion | None:
        return await self.s.get(ProgramVersion, version_id)

    async def sections(self, version_id: UUID) -> Sequence[ProgramSection]:
        stmt = select(ProgramSection).where(ProgramSection.version_id == version_id).order_by(ProgramSection.position)
        return (await self.s.execute(stmt)).scalars().all()

    async def section(self, version_id: UUID, key: str) -> ProgramSection | None:
        stmt = select(ProgramSection).where(ProgramSection.version_id == version_id, ProgramSection.key == key)
        return (await self.s.execute(stmt)).scalar_one_or_none()

    async def approvals(self, version_id: UUID) -> Sequence[ProgramApproval]:
        stmt = (
            select(ProgramApproval).where(ProgramApproval.version_id == version_id).order_by(ProgramApproval.decided_at)
        )
        return (await self.s.execute(stmt)).scalars().all()
