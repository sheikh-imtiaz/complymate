"""Azure AI Document Intelligence prebuilt-idDocument model."""

from __future__ import annotations

from complymate.adapters.azure._credential import async_credential
from complymate.ports.ocr import OcrResult

_FIELD_MAP = {
    "FirstName": "given_names",
    "LastName": "family_name",
    "DateOfBirth": "date_of_birth",
    "DocumentNumber": "document_number",
    "DateOfExpiration": "expiry_date",
    "Address": "address",
    "Nationality": "nationality",
    "PlaceOfBirth": "place_of_birth",
}


class DocIntelOCR:
    def __init__(self, endpoint: str) -> None:
        from azure.ai.documentintelligence.aio import DocumentIntelligenceClient

        self._client = DocumentIntelligenceClient(endpoint, async_credential())

    async def extract_identity(self, data: bytes, content_type: str) -> OcrResult:
        poller = await self._client.begin_analyze_document("prebuilt-idDocument", body=data, content_type=content_type)
        result = await poller.result()
        fields: dict[str, str] = {}
        confidence: dict[str, float] = {}
        for doc in result.documents or []:
            for name, field in (doc.fields or {}).items():
                key = _FIELD_MAP.get(name)
                if key and field.content:
                    fields[key] = field.content
                    confidence[key] = field.confidence or 0.0
        if fields.get("given_names") or fields.get("family_name"):
            fields["full_name"] = " ".join(x for x in (fields.get("given_names"), fields.get("family_name")) if x)
        return OcrResult(fields=fields, confidence=confidence, raw_text=result.content or "", provider="docintel")
