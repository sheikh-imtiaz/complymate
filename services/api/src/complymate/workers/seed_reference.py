"""Loads reference data on a fresh environment: sample/real watchlists, rule-library sources, training modules."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select

from complymate.agent.rag.ingest import ingest_source
from complymate.container import get_container
from complymate.db.models import KbSource, QuizQuestion, TrainingModule
from complymate.db.session import tenant_session
from complymate.workers import refresh_watchlists

SEED = Path(__file__).resolve().parents[3] / "seed"


async def seed_kb() -> int:
    container = get_container()
    spec = yaml.safe_load((SEED / "kb_sources.yaml").read_text(encoding="utf-8"))
    count = 0
    async with tenant_session(None, platform=True) as session:
        for item in spec["sources"]:
            existing = (
                await session.execute(
                    select(KbSource).where(
                        KbSource.title == item["title"], KbSource.jurisdiction == item["jurisdiction"]
                    )
                )
            ).scalar_one_or_none()
            source = existing or KbSource(
                jurisdiction=item["jurisdiction"],
                title=item["title"],
                url=item.get("url"),
                publisher=item["publisher"],
                doc_type=item.get("doc_type", "guidance"),
                last_checked_at=datetime.fromisoformat(item["last_checked"]).replace(tzinfo=UTC),
            )
            if existing is None:
                session.add(source)
                await session.flush()
            count += await ingest_source(session, container.embeddings, source, item["content"])
    return count


async def seed_training() -> int:
    spec = yaml.safe_load((SEED / "kb_sources.yaml").read_text(encoding="utf-8"))
    created = 0
    async with tenant_session(None, platform=True) as session:
        for m in spec.get("training_modules", []):
            exists = (
                await session.execute(
                    select(TrainingModule).where(TrainingModule.title == m["title"], TrainingModule.tenant_id.is_(None))
                )
            ).scalar_one_or_none()
            if exists:
                continue
            module = TrainingModule(
                tenant_id=None,
                title=m["title"],
                description=m["description"],
                content_md=m["content_md"],
                roles=m.get("roles", []),
                jurisdiction=m.get("jurisdiction", "AU"),
                duration_minutes=m.get("duration_minutes", 15),
                pass_mark=m.get("pass_mark", 80),
                status="published",
            )
            session.add(module)
            await session.flush()
            for q in m.get("questions", []):
                session.add(
                    QuizQuestion(
                        module_id=module.id,
                        question=q["question"],
                        options=q["options"],
                        correct_index=q["correct_index"],
                        explanation=q.get("explanation"),
                        review_status="approved",
                    )
                )
            created += 1
    return created


async def run(payload: dict[str, Any]) -> dict[str, Any]:
    watchlists = await refresh_watchlists.run({"skip_rescreen": True})
    return {"watchlists": watchlists, "kb_chunks": await seed_kb(), "training_modules": await seed_training()}
