"""Tool: search the rule library (AUSTRAC / DIA guidance)."""

from __future__ import annotations

from typing import Any

from complymate.agent.rag.retriever import Retriever, citations


async def search_rules(retriever: Retriever, query: str, jurisdiction: str, k: int = 5) -> list[dict[str, Any]]:
    chunks = await retriever.search(query, jurisdiction, k)
    cites = citations(chunks)
    return [{**c, "content": ch.content[:1500]} for c, ch in zip(cites, chunks, strict=True)]


def make_tool(retriever: Retriever, jurisdiction: str, sink: list[dict[str, Any]]) -> Any:
    from strands import tool

    @tool
    async def search_rule_library(query: str) -> list[dict[str, Any]]:
        """Search AML/CTF regulatory guidance for the firm's jurisdiction. Returns passages with titles and URLs.

        Args:
            query: What to look up, in plain English.
        """
        results = await search_rules(retriever, query, jurisdiction)
        sink.extend(results)
        return results

    return search_rule_library
