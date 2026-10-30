"""API Gateway WebSocket connection pusher (chat streaming on AWS)."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from complymate.adapters.aws._session import client


class ApiGatewayRealtime:
    def __init__(self, region: str, endpoint_url: str) -> None:
        self._client = client("apigatewaymanagementapi", region, endpoint_url)

    async def push(self, connection_id: str, message: dict[str, Any]) -> bool:
        try:
            await asyncio.to_thread(
                self._client.post_to_connection,
                ConnectionId=connection_id,
                Data=json.dumps(message, default=str).encode(),
            )
            return True
        except self._client.exceptions.GoneException:
            return False
