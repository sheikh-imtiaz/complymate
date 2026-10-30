from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from complymate import __version__
from complymate.container import get_container

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    s = get_container().settings
    return {"status": "ok", "version": __version__, "cloud": s.cloud_provider, "environment": s.environment}


@router.get("/health/ready")
async def ready() -> dict[str, str]:
    maker = await get_container().sessionmaker()
    async with maker() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ready"}
