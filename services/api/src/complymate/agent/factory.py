"""Agent factory. Builds the "Ask the Rules" agent on Strands Agents (model-agnostic: Bedrock, Azure AI Foundry,
OpenAI-compatible) and falls back to a direct RAG call when the provider has no Strands model (local fake LLM).

Flow: guardrails(input) → retrieve sources → Strands agent with tools (search, client risk, risk explainer,
sanctions check) → guardrails(output) → caller writes audit + usage.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from complymate.agent import guardrails
from complymate.agent.rag.retriever import Retriever, citations, format_sources
from complymate.observability.tracing import agent_span
from complymate.ports.embeddings import EmbeddingProvider
from complymate.ports.llm import ChatMessage, LLMProvider

log = structlog.get_logger(__name__)
PROMPTS = Path(__file__).parent / "prompts"


@lru_cache(maxsize=16)
def load_prompt(name: str) -> str:
    return (PROMPTS / f"{name}.md").read_text(encoding="utf-8")


@dataclass
class AgentEvent:
    type: str  # token | citations | done | blocked
    data: Any


@dataclass
class AgentAnswer:
    text: str
    citations: list[dict[str, Any]]
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    blocked: bool = False


class RulesChatAgent:
    def __init__(
        self,
        llm: LLMProvider,
        embeddings: EmbeddingProvider,
        session: AsyncSession,
        principal: Any,
        jurisdiction: str,
    ) -> None:
        self.llm = llm
        self.session = session
        self.principal = principal
        self.jurisdiction = jurisdiction
        self.retriever = Retriever(session, embeddings)

    def _system(self) -> str:
        return load_prompt("system_rules_chat").format(jurisdiction=self.jurisdiction, today=date.today().isoformat())

    def _tools(self, sink: list[dict[str, Any]]) -> list[Any]:
        from complymate.agent.tools import check_sanctions, get_client_risk, score_risk, search_rules

        tools = [
            search_rules.make_tool(self.retriever, self.jurisdiction, sink),
            score_risk.make_tool(self.jurisdiction),
        ]
        perms = self.principal.permissions
        if any(p.startswith("risk:read") for p in perms):
            tools.append(get_client_risk.make_tool(self.session, self.principal, sink))
        if any(p.startswith("screening:") for p in perms):
            tools.append(check_sanctions.make_tool(self.session))
        return tools

    async def stream(
        self, question: str, history: list[ChatMessage], client_id: UUID | None = None
    ) -> AsyncIterator[AgentEvent]:
        start = time.perf_counter()
        check = guardrails.check_input(question)
        if not check.allowed:
            yield AgentEvent("blocked", {"category": check.category})
            yield AgentEvent("token", check.message)
            yield AgentEvent("done", AgentAnswer(check.message or "", [], "guardrail", flags=check.flags, blocked=True))
            return

        with agent_span("retrieve", jurisdiction=self.jurisdiction):
            chunks = await self.retriever.search(question, self.jurisdiction, k=6)
        cites = citations(chunks)
        yield AgentEvent("citations", cites)

        user_msg = f"Question: {question}\n\nSources:\n{format_sources(chunks) or '(no matching sources found)'}"
        if client_id:
            user_msg += f"\n\nThe user is asking about client {client_id}; use read_client_risk if needed."
        messages = [*history[-8:], ChatMessage("user", user_msg)]
        tool_calls: list[dict[str, Any]] = []
        text_parts: list[str] = []
        model_name = "unknown"
        input_tokens = output_tokens = 0

        strands_model = self.llm.strands_model()
        if strands_model is not None:
            from strands import Agent

            agent = Agent(
                model=strands_model,
                system_prompt=self._system(),
                tools=self._tools(tool_calls),
                messages=[{"role": m.role, "content": [{"text": m.content}]} for m in history[-8:]],
                callback_handler=None,
            )
            with agent_span("model_call", provider=self.llm.name) as span:
                async for event in agent.stream_async(user_msg):
                    if isinstance(event, dict) and (chunk := event.get("data")):
                        text_parts.append(chunk)
                        yield AgentEvent("token", chunk)
                    elif isinstance(event, dict) and "current_tool_use" in event:
                        name = (event["current_tool_use"] or {}).get("name")
                        if name and (not tool_calls or tool_calls[-1].get("tool") != name):
                            tool_calls.append({"tool": name})
                    elif isinstance(event, dict) and "result" in event:
                        result = event["result"]
                        usage = getattr(getattr(result, "metrics", None), "accumulated_usage", {}) or {}
                        input_tokens = int(usage.get("inputTokens", 0))
                        output_tokens = int(usage.get("outputTokens", 0))
                span.set_attribute("complymate.input_tokens", input_tokens)
                span.set_attribute("complymate.output_tokens", output_tokens)
            config: Any = getattr(strands_model, "config", None) or {}
            model_name = config.get("model_id", self.llm.name) if isinstance(config, dict) else self.llm.name
        else:
            with agent_span("model_call", provider=self.llm.name):
                async for chunk in self.llm.stream(self._system(), messages):
                    text_parts.append(chunk)
                    yield AgentEvent("token", chunk)
            model_name = self.llm.name
            input_tokens = sum(len(m.content.split()) for m in messages)
            output_tokens = len("".join(text_parts).split())

        out = guardrails.check_output("".join(text_parts), len(chunks))
        raw = "".join(text_parts)
        if out.text.startswith(raw):
            tail = out.text[len(raw) :]
            if tail:
                yield AgentEvent("token", tail)
        else:
            yield AgentEvent("replace", out.text)
        used = [c for c in cites if int(str(c["ref"])[1:]) in out.cited] or cites
        yield AgentEvent(
            "done",
            AgentAnswer(
                text=out.text,
                citations=used,
                model=model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=int((time.perf_counter() - start) * 1000),
                tool_calls=tool_calls,
                flags=check.flags + out.flags,
            ),
        )

    async def ask(self, question: str, history: list[ChatMessage], client_id: UUID | None = None) -> AgentAnswer:
        answer: AgentAnswer | None = None
        async for event in self.stream(question, history, client_id):
            if event.type == "done":
                answer = event.data
        assert answer is not None
        return answer


async def complete_json(llm: LLMProvider, system: str, user: str, *, fast: bool = True) -> tuple[Any, Any]:
    """One-shot JSON completion (quiz writer, SMR helper). Returns (parsed, LLMResult)."""
    import json
    import re

    result = await llm.complete(system, [ChatMessage("user", user)], max_tokens=2000, fast=fast)
    text = result.text.strip()
    match = re.search(r"(\{.*\}|\[.*\])", text, re.S)
    if not match:
        raise ValueError("model did not return JSON")
    return json.loads(match.group(1)), result
