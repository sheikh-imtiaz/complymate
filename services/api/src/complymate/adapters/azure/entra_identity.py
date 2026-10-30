"""Microsoft Entra External ID (OIDC). Users are managed through Microsoft Graph."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

import httpx
import jwt

from complymate.adapters.azure._credential import async_credential
from complymate.ports.identity import TokenClaims

GRAPH = "https://graph.microsoft.com/v1.0"


class EntraIdentity:
    def __init__(self, issuer: str, audience: str, jwks_url: str | None = None) -> None:
        self.issuer = issuer
        self.audience = audience
        self._jwks = jwt.PyJWKClient(jwks_url or f"{issuer.rstrip('/')}/discovery/v2.0/keys", cache_keys=True)

    async def verify_token(self, token: str) -> TokenClaims:
        key = await asyncio.to_thread(self._jwks.get_signing_key_from_jwt, token)
        data: dict[str, Any] = jwt.decode(
            token, key.key, algorithms=["RS256"], audience=self.audience, issuer=self.issuer
        )
        amr = data.get("amr", [])
        return TokenClaims(
            sub=data["oid"] if "oid" in data else data["sub"],
            email=data.get("email") or data.get("preferred_username", ""),
            name=data.get("name"),
            auth_time=datetime.fromtimestamp(data["auth_time"], UTC) if "auth_time" in data else None,
            mfa_verified="mfa" in amr,
            raw=data,
        )

    async def _graph(self, method: str, path: str, json_body: dict[str, Any] | None = None) -> dict[str, Any]:
        token = await async_credential().get_token("https://graph.microsoft.com/.default")
        async with httpx.AsyncClient(timeout=15) as http:
            resp = await http.request(
                method, f"{GRAPH}{path}", json=json_body, headers={"Authorization": f"Bearer {token.token}"}
            )
            resp.raise_for_status()
            return resp.json() if resp.content else {}

    async def invite_user(self, email: str, full_name: str | None = None) -> str:
        result = await self._graph(
            "POST",
            "/invitations",
            {
                "invitedUserEmailAddress": email,
                "invitedUserDisplayName": full_name or email,
                "sendInvitationMessage": True,
                "inviteRedirectUrl": "https://app.complymate.example/callback",
            },
        )
        return str(result["invitedUser"]["id"])

    async def disable_user(self, sub: str) -> None:
        await self._graph("PATCH", f"/users/{sub}", {"accountEnabled": False})
        await self.sign_out_everywhere(sub)

    async def enable_user(self, sub: str) -> None:
        await self._graph("PATCH", f"/users/{sub}", {"accountEnabled": True})

    async def reset_mfa(self, sub: str) -> None:
        methods = await self._graph("GET", f"/users/{sub}/authentication/softwareOathMethods")
        for m in methods.get("value", []):
            await self._graph("DELETE", f"/users/{sub}/authentication/softwareOathMethods/{m['id']}")

    async def sign_out_everywhere(self, sub: str) -> None:
        await self._graph("POST", f"/users/{sub}/revokeSignInSessions")
