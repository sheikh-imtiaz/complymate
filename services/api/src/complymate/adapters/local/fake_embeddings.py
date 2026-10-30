"""Hash-based bag-of-words embeddings. Deterministic, good enough for local retrieval tests."""

from __future__ import annotations

import hashlib
import math
import re

_WORD = re.compile(r"[a-z0-9]+")


class FakeEmbeddings:
    def __init__(self, dimensions: int = 1024) -> None:
        self.dimensions = dimensions

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self.dimensions
        for word in _WORD.findall(text.lower()):
            if len(word) < 3:
                continue
            h = int.from_bytes(hashlib.blake2b(word.encode(), digest_size=8).digest(), "big")
            vec[h % self.dimensions] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]
