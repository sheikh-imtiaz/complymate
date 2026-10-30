"""Amazon Titan Text Embeddings v2 on Bedrock."""

from __future__ import annotations

import asyncio
import json

from complymate.adapters.aws._session import client


class BedrockEmbeddings:
    def __init__(self, region: str, model_id: str = "amazon.titan-embed-text-v2:0", dimensions: int = 1024) -> None:
        self.model_id = model_id
        self.dimensions = dimensions
        self._client = client("bedrock-runtime", region)

    def _embed_one(self, text: str) -> list[float]:
        body = json.dumps({"inputText": text[:30000], "dimensions": self.dimensions, "normalize": True})
        resp = self._client.invoke_model(modelId=self.model_id, body=body, contentType="application/json")
        payload = json.loads(resp["body"].read())
        vector: list[float] = payload["embedding"]
        return vector

    async def embed(self, texts: list[str]) -> list[list[float]]:
        sem = asyncio.Semaphore(8)

        async def run(t: str) -> list[float]:
            async with sem:
                return await asyncio.to_thread(self._embed_one, t)

        return list(await asyncio.gather(*(run(t) for t in texts)))
