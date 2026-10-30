"""Masks PII in structured logs: names, emails, ID numbers, dates of birth, phone numbers.

System logs are for engineers. No PII goes in them. The audit log (database) is where business records live.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

SENSITIVE_KEYS = {
    "name",
    "full_name",
    "given_names",
    "family_name",
    "display_name",
    "legal_name",
    "first_name",
    "last_name",
    "email",
    "to",
    "recipient",
    "dob",
    "date_of_birth",
    "document_number",
    "passport",
    "licence",
    "address",
    "phone",
    "password",
    "token",
    "authorization",
    "secret",
    "api_key",
    "tfn",
    "body",
    "content",
    "message",
    "prompt",
    "answer",
    "question",
    "grounds",
    "summary",
    "ocr_fields",
}

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_DATE = re.compile(r"\b(19|20)\d{2}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/(19|20)\d{2}\b")
_IDNUM = re.compile(r"\b[A-Z]{1,2}\d{6,9}\b|\b\d{9,11}\b")
_PHONE = re.compile(r"(?:\+?61|\+?64|0)[2-9]\d{7,9}\b")
_JWT = re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")


def mask_text(value: str) -> str:
    value = _JWT.sub("[jwt]", value)
    value = _EMAIL.sub("[email]", value)
    value = _DATE.sub("[date]", value)
    value = _PHONE.sub("[phone]", value)
    return _IDNUM.sub("[id]", value)


def mask_value(key: str, value: Any) -> Any:
    if key.lower() in SENSITIVE_KEYS and value not in (None, ""):
        return "[masked]"
    if isinstance(value, str):
        return mask_text(value)
    if isinstance(value, Mapping):
        return {k: mask_value(str(k), v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [mask_value(key, v) for v in value]
    return value


def pii_processor(_logger: Any, _method: str, event_dict: Any) -> Any:
    """structlog processor. Keeps the `event` name, masks everything else."""
    for key in list(event_dict.keys()):
        if key in ("event", "level", "timestamp", "logger", "request_id", "tenant_id", "user_id", "trace_id"):
            continue
        event_dict[key] = mask_value(key, event_dict[key])
    if isinstance(event_dict.get("event"), str):
        event_dict["event"] = mask_text(event_dict["event"])
    return event_dict
