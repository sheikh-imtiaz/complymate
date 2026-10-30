from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


@dataclass
class ChatMessage:
    role: Literal["user", "assistant"]
    content: str


@dataclass
class LLMResult:
    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


class LLMProvider(Protocol):
    """Chat model. `strands_model` returns a Strands model object so agents stay model-agnostic."""

    name: str

    async def complete(
        self,
        system: str,
        messages: list[ChatMessage],
        *,
        max_tokens: int = 1500,
        temperature: float = 0.2,
        fast: bool = False,
    ) -> LLMResult: ...

    def stream(
        self,
        system: str,
        messages: list[ChatMessage],
        *,
        max_tokens: int = 1500,
        temperature: float = 0.2,
        fast: bool = False,
    ) -> AsyncIterator[str]: ...

    def strands_model(self, *, fast: bool = False) -> Any | None: ...
