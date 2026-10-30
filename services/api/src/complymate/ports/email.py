from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class Attachment:
    filename: str
    content: bytes
    content_type: str


class EmailSender(Protocol):
    async def send(
        self,
        to: list[str],
        subject: str,
        html: str,
        text: str | None = None,
        attachments: list[Attachment] | None = None,
    ) -> str: ...
