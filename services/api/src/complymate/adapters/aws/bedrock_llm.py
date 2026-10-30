"""Amazon Bedrock (Claude Sonnet / Haiku) via the Converse API, with Bedrock Guardrails."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any, cast

from complymate.adapters.aws._session import client
from complymate.ports.llm import ChatMessage, LLMResult


class BedrockLLM:
    name = "bedrock"

    def __init__(
        self,
        region: str,
        model_id: str,
        fast_model_id: str,
        guardrail_id: str | None = None,
        guardrail_version: str | None = None,
    ) -> None:
        self.region = region
        self.model_id = model_id
        self.fast_model_id = fast_model_id
        self.guardrail_id = guardrail_id
        self.guardrail_version = guardrail_version or "DRAFT"
        self._client = client("bedrock-runtime", region)

    def _request(
        self, system: str, messages: list[ChatMessage], max_tokens: int, temperature: float, fast: bool
    ) -> dict[str, Any]:
        req: dict[str, Any] = {
            "modelId": self.fast_model_id if fast else self.model_id,
            "system": [{"text": system}],
            "messages": [{"role": m.role, "content": [{"text": m.content}]} for m in messages],
            "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
        }
        if self.guardrail_id:
            req["guardrailConfig"] = {
                "guardrailIdentifier": self.guardrail_id,
                "guardrailVersion": self.guardrail_version,
            }
        return req

    async def complete(
        self,
        system: str,
        messages: list[ChatMessage],
        *,
        max_tokens: int = 1500,
        temperature: float = 0.2,
        fast: bool = False,
    ) -> LLMResult:
        req = self._request(system, messages, max_tokens, temperature, fast)
        resp = await asyncio.to_thread(self._client.converse, **req)
        text = "".join(block.get("text", "") for block in resp["output"]["message"]["content"])
        usage = resp.get("usage", {})
        return LLMResult(
            text=text,
            model=req["modelId"],
            input_tokens=usage.get("inputTokens", 0),
            output_tokens=usage.get("outputTokens", 0),
            raw={"stopReason": resp.get("stopReason")},
        )

    async def stream(
        self,
        system: str,
        messages: list[ChatMessage],
        *,
        max_tokens: int = 1500,
        temperature: float = 0.2,
        fast: bool = False,
    ) -> AsyncIterator[str]:
        req = self._request(system, messages, max_tokens, temperature, fast)
        resp = await asyncio.to_thread(self._client.converse_stream, **req)
        stream = resp["stream"]
        loop = asyncio.get_running_loop()
        iterator = iter(stream)
        sentinel = object()
        while True:
            event = await loop.run_in_executor(None, next, iterator, sentinel)
            if event is sentinel:
                break
            delta = cast(dict[str, Any], event).get("contentBlockDelta", {}).get("delta", {})
            if text := delta.get("text"):
                yield text

    def strands_model(self, *, fast: bool = False) -> Any | None:
        from strands.models import BedrockModel

        kwargs: dict[str, Any] = {
            "model_id": self.fast_model_id if fast else self.model_id,
            "region_name": self.region,
            "temperature": 0.2,
            "max_tokens": 2000,
        }
        if self.guardrail_id:
            kwargs["guardrail_id"] = self.guardrail_id
            kwargs["guardrail_version"] = self.guardrail_version
            kwargs["guardrail_trace"] = "enabled"
        return BedrockModel(**kwargs)
