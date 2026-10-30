from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from complymate.schemas.common import ORM


class DocumentOut(ORM):
    id: UUID
    client_id: UUID
    party_id: UUID | None
    doc_type: str
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    ocr_status: str
    ocr_fields: dict[str, Any]
    ocr_confidence: dict[str, Any]
    ocr_confirmed: bool
    confirmed_by: UUID | None
    uploaded_by: UUID | None
    created_at: datetime


class ConfirmFieldsIn(BaseModel):
    fields: dict[str, str]
    apply_to_client: bool = True
