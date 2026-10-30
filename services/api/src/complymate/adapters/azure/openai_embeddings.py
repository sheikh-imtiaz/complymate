"""Azure OpenAI text-embedding-3-small, truncated to 1024 dims to match the pgvector column."""

from __future__ import annotations

from complymate.adapters.azure._credential import sync_credential


class AzureOpenAIEmbeddings:
    def __init__(self, endpoint: str, deployment: str, api_version: str, dimensions: int = 1024) -> None:
        from azure.identity import get_bearer_token_provider
        from openai import AsyncAzureOpenAI

        self.deployment = deployment
        self.dimensions = dimensions
        self._client = AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_version=api_version,
            azure_ad_token_provider=get_bearer_token_provider(
                sync_credential(), "https://cognitiveservices.azure.com/.default"
            ),
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), 64):
            resp = await self._client.embeddings.create(
                model=self.deployment, input=texts[i : i + 64], dimensions=self.dimensions
            )
            out.extend(d.embedding for d in resp.data)
        return out
