"""Amazon Textract AnalyzeID (identity documents) with AnalyzeDocument fallback for other files."""

from __future__ import annotations

import asyncio

from complymate.adapters.aws._session import client
from complymate.ports.ocr import OcrResult

_FIELD_MAP = {
    "FIRST_NAME": "given_names",
    "MIDDLE_NAME": "middle_name",
    "LAST_NAME": "family_name",
    "DATE_OF_BIRTH": "date_of_birth",
    "DOCUMENT_NUMBER": "document_number",
    "EXPIRATION_DATE": "expiry_date",
    "ADDRESS": "address",
    "PLACE_OF_BIRTH": "place_of_birth",
    "ID_TYPE": "id_type",
    "STATE_IN_ADDRESS": "state",
}


class TextractOCR:
    def __init__(self, region: str) -> None:
        self._client = client("textract", region)

    async def extract_identity(self, data: bytes, content_type: str) -> OcrResult:
        if content_type in ("image/jpeg", "image/png", "application/pdf"):
            resp = await asyncio.to_thread(self._client.analyze_id, DocumentPages=[{"Bytes": data}])
            fields: dict[str, str] = {}
            confidence: dict[str, float] = {}
            for doc in resp.get("IdentityDocuments", []):
                for f in doc.get("IdentityDocumentFields", []):
                    key = _FIELD_MAP.get(f["Type"]["Text"])
                    value = f.get("ValueDetection", {})
                    if key and value.get("Text"):
                        fields[key] = value.get("NormalizedValue", {}).get("Value") or value["Text"]
                        confidence[key] = float(value.get("Confidence", 0)) / 100
            names = [fields.get("given_names"), fields.get("middle_name"), fields.get("family_name")]
            if any(names):
                fields["full_name"] = " ".join(n for n in names if n)
            return OcrResult(fields=fields, confidence=confidence, provider="textract")
        resp = await asyncio.to_thread(self._client.detect_document_text, Document={"Bytes": data})
        text = "\n".join(b["Text"] for b in resp.get("Blocks", []) if b["BlockType"] == "LINE")
        return OcrResult(raw_text=text, provider="textract")
