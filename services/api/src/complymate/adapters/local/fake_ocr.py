"""Fake OCR: pulls `key: value` lines out of text files, otherwise returns empty fields for manual entry."""

from __future__ import annotations

import re

from complymate.ports.ocr import OcrResult

_KEYS = {
    "name": "full_name",
    "full name": "full_name",
    "date of birth": "date_of_birth",
    "dob": "date_of_birth",
    "document number": "document_number",
    "passport no": "document_number",
    "licence number": "document_number",
    "expiry": "expiry_date",
    "expiry date": "expiry_date",
    "nationality": "nationality",
    "address": "address",
}


class FakeOCR:
    async def extract_identity(self, data: bytes, content_type: str) -> OcrResult:
        if not content_type.startswith("text/"):
            return OcrResult(provider="fake")
        text = data.decode("utf-8", errors="ignore")
        fields: dict[str, str] = {}
        for line in text.splitlines():
            m = re.match(r"\s*([A-Za-z ]+)\s*:\s*(.+)", line)
            if m and (key := _KEYS.get(m.group(1).strip().lower())):
                fields[key] = m.group(2).strip()
        return OcrResult(fields=fields, confidence={k: 0.99 for k in fields}, raw_text=text, provider="fake")
