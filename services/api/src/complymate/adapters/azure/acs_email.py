"""Azure Communication Services Email."""

from __future__ import annotations

import base64
from typing import Any

from complymate.adapters.azure._credential import async_credential
from complymate.ports.email import Attachment


class AcsEmail:
    def __init__(self, endpoint: str, sender: str) -> None:
        from azure.communication.email.aio import EmailClient

        self.sender = sender
        self._client = EmailClient(endpoint, async_credential())

    async def send(
        self,
        to: list[str],
        subject: str,
        html: str,
        text: str | None = None,
        attachments: list[Attachment] | None = None,
    ) -> str:
        message: dict[str, Any] = {
            "senderAddress": self.sender,
            "recipients": {"to": [{"address": a} for a in to]},
            "content": {"subject": subject, "html": html, "plainText": text or ""},
        }
        if attachments:
            message["attachments"] = [
                {
                    "name": a.filename,
                    "contentType": a.content_type,
                    "contentInBase64": base64.b64encode(a.content).decode(),
                }
                for a in attachments
            ]
        poller = await self._client.begin_send(message)
        result = await poller.result()
        return str(result["id"])
