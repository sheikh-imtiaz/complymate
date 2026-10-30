"""SMTP sender for Mailpit (local)."""

from __future__ import annotations

import asyncio
import smtplib
import uuid
from email.message import EmailMessage

from complymate.ports.email import Attachment


class MailpitEmail:
    def __init__(self, host: str, port: int, sender: str) -> None:
        self.host = host
        self.port = port
        self.sender = sender
        self.outbox: list[EmailMessage] = []

    def _send_sync(self, msg: EmailMessage) -> None:
        with smtplib.SMTP(self.host, self.port, timeout=5) as smtp:
            smtp.send_message(msg)

    async def send(
        self,
        to: list[str],
        subject: str,
        html: str,
        text: str | None = None,
        attachments: list[Attachment] | None = None,
    ) -> str:
        msg = EmailMessage()
        msg["From"] = self.sender
        msg["To"] = ", ".join(to)
        msg["Subject"] = subject
        msg_id = f"<{uuid.uuid4()}@complymate.local>"
        msg["Message-ID"] = msg_id
        msg.set_content(text or "This email requires an HTML-capable client.")
        msg.add_alternative(html, subtype="html")
        for att in attachments or []:
            maintype, _, subtype = att.content_type.partition("/")
            msg.add_attachment(att.content, maintype=maintype, subtype=subtype or "octet-stream", filename=att.filename)
        self.outbox.append(msg)
        try:
            await asyncio.to_thread(self._send_sync, msg)
        except OSError:
            pass  # Mailpit not running: keep the message in the outbox
        return msg_id
