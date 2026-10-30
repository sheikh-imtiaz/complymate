"""Azure AI Foundry / Azure OpenAI chat models through the OpenAI-compatible API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from complymate.adapters.azure._credential import sync_credential
from complymate.ports.llm import ChatMessage, LLMResult


class FoundryLLM:
    name = "azure-foundry"

    def __init__(self, endpoint: str, model: str, fast_model: str, api_version: str) -> None:
        from azure.identity import get_bearer_token_provider
        from openai import AsyncAzureOpenAI

        self.endpoint = endpoint
        self.model = model
        self.fast_model = fast_model
        self.api_version = api_version
        self._token_provider = get_bearer_token_provider(
            sync_credential(), "https://cognitiveservices.azure.com/.default"
        )
        self._client = AsyncAzureOpenAI(
            azure_endpoint=endpoint, api_version=api_version, azure_ad_token_provider=self._token_provider
        )

    def _messages(self, system: str, messages: list[ChatMessage]) -> list[dict[str, str]]:
        return [{"role": "system", "content": system}] + [{"role": m.role, "content": m.content} for m in messages]

    async def complete(
        self,
        system: str,
        messages: list[ChatMessage],
        *,
        max_tokens: int = 1500,
        temperature: float = 0.2,
        fast: bool = False,
    ) -> LLMResult:
        model = self.fast_model if fast else self.model
        resp = await self._client.chat.completions.create(
            model=model,
            messages=self._messages(system, messages),  # type: ignore[arg-type]
            max_tokens=max_tokens,
            temperature=temperature,
        )
        usage = resp.usage
        return LLMResult(
            text=resp.choices[0].message.content or "",
            model=model,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
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
        stream = await self._client.chat.completions.create(
            model=self.fast_model if fast else self.model,
            messages=self._messages(system, messages),  # type: ignore[arg-type]
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and (delta := chunk.choices[0].delta.content):
                yield delta

    def strands_model(self, *, fast: bool = False) -> Any | None:
        from openai import AsyncAzureOpenAI
        from strands.models.openai import OpenAIModel

        model = OpenAIModel(
            client_args={},
            model_id=self.fast_model if fast else self.model,
            params={"temperature": 0.2, "max_tokens": 2000},
        )
        # Strands' OpenAI model accepts a pre-built client; use Entra auth instead of API keys.
        model.client = AsyncAzureOpenAI(  # type: ignore[attr-defined]
            azure_endpoint=self.endpoint,
            api_version=self.api_version,
            azure_ad_token_provider=self._token_provider,
        )
        return model
