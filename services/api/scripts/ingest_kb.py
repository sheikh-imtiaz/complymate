"""(Re)ingests the rule library from seed/kb_sources.yaml, or a single text/markdown file.

uv run python scripts/ingest_kb.py
uv run python scripts/ingest_kb.py --file guidance.md --title "AUSTRAC CDD guidance" --jurisdiction AU --url https://...
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
from pathlib import Path

from complymate.agent.rag.ingest import ingest_source
from complymate.container import get_container
from complymate.db.models import KbSource
from complymate.db.session import tenant_session
from complymate.workers.seed_reference import seed_kb


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file")
    parser.add_argument("--title")
    parser.add_argument("--jurisdiction", default="AU")
    parser.add_argument("--publisher", default="AUSTRAC")
    parser.add_argument("--url")
    args = parser.parse_args()
    if not args.file:
        print(f"ingested {await seed_kb()} chunks from seed/kb_sources.yaml")
        return
    text = Path(args.file).read_text(encoding="utf-8")  # noqa: ASYNC240 - CLI script
    async with tenant_session(None, platform=True) as session:
        source = KbSource(
            jurisdiction=args.jurisdiction,
            title=args.title or Path(args.file).stem,
            url=args.url,
            publisher=args.publisher,
            last_checked_at=datetime.now(UTC),
        )
        session.add(source)
        await session.flush()
        n = await ingest_source(session, get_container().embeddings, source, text)
    print(f"ingested {n} chunks")


if __name__ == "__main__":
    asyncio.run(main())
