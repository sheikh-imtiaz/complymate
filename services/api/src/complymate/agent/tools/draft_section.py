"""Tool: draft one AML/CTF program section with citations (used by the draft_program worker)."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from complymate.agent.factory import load_prompt
from complymate.agent.guardrails import sanitize_html
from complymate.agent.rag.retriever import Retriever, citations, format_sources
from complymate.domain.programs.interview import QUESTIONS, section
from complymate.ports.llm import ChatMessage, LLMProvider


@dataclass
class DraftResult:
    html: str
    citations: list[dict[str, Any]]
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    flags: list[str] = field(default_factory=list)


async def draft_section(
    llm: LLMProvider,
    retriever: Retriever,
    *,
    section_key: str,
    answers: dict[str, Any],
    jurisdiction: str,
    firm_name: str,
) -> DraftResult:
    sdef = section(section_key)
    chunks = await retriever.search(sdef.rag_query, jurisdiction, k=5)
    relevant = {q.id: answers.get(q.id) for q in QUESTIONS if q.id in sdef.questions}
    system = load_prompt("program_drafter").format(
        jurisdiction=jurisdiction, section_title=sdef.title, section_guidance=sdef.guidance
    )
    user = (
        f"Firm: {firm_name}\nDate: {date.today().isoformat()}\n\nInterview answers (JSON):\n"
        f"{json.dumps(relevant, indent=2, default=str)}\n\nSources:\n{format_sources(chunks)}"
    )
    start = time.perf_counter()
    result = await llm.complete(system, [ChatMessage("user", user)], max_tokens=1800)
    html = sanitize_html(result.text)
    if not html.lstrip().startswith("<"):
        html = "".join(f"<p>{p.strip()}</p>" for p in html.split("\n\n") if p.strip())
    return DraftResult(
        html=html,
        citations=citations(chunks),
        model=result.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        latency_ms=int((time.perf_counter() - start) * 1000),
    )
