"""@mentions. The editor inserts `@[Display Name](user:<uuid>)`; plain `@email` also works."""

from __future__ import annotations

import re
from uuid import UUID

_TOKEN = re.compile(r"@\[(?P<name>[^\]]{1,120})\]\(user:(?P<id>[0-9a-fA-F-]{36})\)")
_EMAIL = re.compile(r"(?<![\w.])@(?P<email>[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")


def extract_user_ids(body: str) -> set[UUID]:
    return {UUID(m.group("id")) for m in _TOKEN.finditer(body)}


def extract_emails(body: str) -> set[str]:
    return {m.group("email").lower() for m in _EMAIL.finditer(body)}


def render_plain(body: str) -> str:
    return _TOKEN.sub(lambda m: f"@{m.group('name')}", body)
