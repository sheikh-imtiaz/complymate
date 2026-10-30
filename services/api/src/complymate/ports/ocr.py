from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class OcrResult:
    fields: dict[str, str] = field(
        default_factory=dict
    )  # normalised keys: full_name, date_of_birth, document_number, expiry_date, ...
    confidence: dict[str, float] = field(default_factory=dict)
    raw_text: str = ""
    provider: str = ""


class DocumentOCR(Protocol):
    async def extract_identity(self, data: bytes, content_type: str) -> OcrResult: ...
