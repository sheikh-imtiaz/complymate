"""Amazon SES v2."""

from __future__ import annotations

import asyncio
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from complymate.adapters.aws._session import client
from complymate.ports.email import Attachment


class SesEmail:
    def __init__(self, region: str, sender: str, configuration_set: str | None = None) -> None:
        self.sender = sender
        self.configuration_set = configuration_set
        self._client = client("sesv2", region)

    async def send(
        self,
        to: list[str],
        subject: str,
        html: str,
        text: str | None = None,
        attachments: list[Attachment] | None = None,
    ) -> str:
        args: dict[str, Any] = {"FromEmailAddress": self.sender, "Destination": {"ToAddresses": to}}
        if self.configuration_set:
            args["ConfigurationSetName"] = self.configuration_set
        if attachments:
            msg = MIMEMultipart("mixed")
            msg["Subject"] = subject
            msg["From"] = self.sender
            msg["To"] = ", ".join(to)
            alt = MIMEMultipart("alternative")
            alt.attach(MIMEText(text or "", "plain"))
            alt.attach(MIMEText(html, "html"))
            msg.attach(alt)
            for att in attachments:
                part = MIMEApplication(att.content)
                part.add_header("Content-Disposition", "attachment", filename=att.filename)
                msg.attach(part)
            args["Content"] = {"Raw": {"Data": msg.as_bytes()}}
        else:
            body: dict[str, Any] = {"Html": {"Data": html, "Charset": "UTF-8"}}
            if text:
                body["Text"] = {"Data": text, "Charset": "UTF-8"}
            args["Content"] = {"Simple": {"Subject": {"Data": subject, "Charset": "UTF-8"}, "Body": body}}
        resp = await asyncio.to_thread(self._client.send_email, **args)
        message_id: str = resp["MessageId"]
        return message_id
