"""Splits guidance documents into heading-aware chunks (~600 words, 80-word overlap)."""

from __future__ import annotations

import re
from dataclasses import dataclass

_HEADING = re.compile(r"^(#{1,4})\s+(.*)$|^([A-Z][A-Za-z0-9 ,'()/-]{3,80})\n[=-]{3,}$", re.M)


@dataclass
class Chunk:
    heading: str | None
    content: str
    tokens: int


def _sections(text: str) -> list[tuple[str | None, str]]:
    parts: list[tuple[str | None, str]] = []
    last_end = 0
    heading: str | None = None
    for m in _HEADING.finditer(text):
        body = text[last_end : m.start()].strip()
        if body:
            parts.append((heading, body))
        heading = (m.group(2) or m.group(3) or "").strip()
        last_end = m.end()
    tail = text[last_end:].strip()
    if tail:
        parts.append((heading, tail))
    return parts or [(None, text.strip())]


def chunk_text(text: str, max_words: int = 600, overlap: int = 80) -> list[Chunk]:
    out: list[Chunk] = []
    for heading, body in _sections(text.replace("\r\n", "\n")):
        words = body.split()
        if not words:
            continue
        start = 0
        while start < len(words):
            piece = words[start : start + max_words]
            content = " ".join(piece)
            out.append(Chunk(heading, content, int(len(piece) * 1.3)))
            if start + max_words >= len(words):
                break
            start += max_words - overlap
    return out
