"""Deterministic LLM for local dev and tests. Builds an answer from the sources in the prompt."""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from typing import Any

from complymate.ports.llm import ChatMessage, LLMResult

_SOURCE_RE = re.compile(r"\[S(\d+)\]\s*(?P<title>[^\n]*)\n(?P<body>.*?)(?=\n\[S\d+\]|\Z)", re.S)


class FakeLLM:
    name = "fake"

    def _answer(self, system: str, messages: list[ChatMessage]) -> str:
        last = messages[-1].content if messages else ""
        if "JSON" in system and "quiz" in system.lower():
            return (
                '[{"question": "Who must be nominated to oversee the AML/CTF program?", '
                '"options": ["The AML/CTF compliance officer", "The receptionist", "Any client", "The auditor"], '
                '"correct_index": 0, "explanation": "A compliance officer must be designated.", "source": "S1"}]'
            )
        if "JSON" in system and "smr" in system.lower():
            return (
                '{"grounds_summary": "Unusual pattern described by staff; see notes.", '
                '"suspicion_categories": ["unusual_transaction"], "missing_information": ["Transaction dates"], '
                '"austrac_fields": {"reason_for_suspicion": "See grounds summary"}}'
            )
        sources = _SOURCE_RE.findall(last)
        if not sources:
            return (
                "I could not find this in the rule library, so I can't give a sourced answer. "
                "Please check the AUSTRAC / DIA guidance or ask your compliance officer."
            )
        parts = []
        for num, _title, body in sources[:3]:
            snippet = " ".join(body.split())[:280]
            parts.append(f"{snippet} [S{num}]")
        return (
            "Based on the rule library:\n\n"
            + "\n\n".join(parts)
            + ("\n\nThis is general information, not legal advice.")
        )

    async def complete(
        self,
        system: str,
        messages: list[ChatMessage],
        *,
        max_tokens: int = 1500,
        temperature: float = 0.2,
        fast: bool = False,
    ) -> LLMResult:
        text = self._answer(system, messages)
        tokens_in = sum(len(m.content.split()) for m in messages) + len(system.split())
        return LLMResult(text=text, model="fake-llm", input_tokens=tokens_in, output_tokens=len(text.split()))

    async def stream(
        self,
        system: str,
        messages: list[ChatMessage],
        *,
        max_tokens: int = 1500,
        temperature: float = 0.2,
        fast: bool = False,
    ) -> AsyncIterator[str]:
        text = self._answer(system, messages)
        for word in re.findall(r"\S+\s*", text):
            yield word

    def strands_model(self, *, fast: bool = False) -> Any | None:
        return None
