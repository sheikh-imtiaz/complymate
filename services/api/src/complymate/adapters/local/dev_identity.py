"""Dev identity provider: HS256 JWTs signed with DEV_JWT_SECRET. Never enabled outside CLOUD_PROVIDER=local."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime

import jwt

from complymate.ports.identity import TokenClaims

ISSUER = "complymate-dev"


class DevIdentity:
    def __init__(self, secret: str) -> None:
        self.secret = secret
        self.disabled: set[str] = set()

    def issue_token(self, sub: str, email: str, name: str | None = None, ttl: int = 8 * 3600) -> str:
        now = int(time.time())
        payload = {
            "iss": ISSUER,
            "sub": sub,
            "email": email,
            "name": name or email,
            "iat": now,
            "auth_time": now,
            "exp": now + ttl,
            "amr": ["pwd", "mfa"],
        }
        return jwt.encode(payload, self.secret, algorithm="HS256")

    async def verify_token(self, token: str) -> TokenClaims:
        data = jwt.decode(token, self.secret, algorithms=["HS256"], issuer=ISSUER)
        if data["sub"] in self.disabled:
            raise jwt.InvalidTokenError("user disabled")
        return TokenClaims(
            sub=data["sub"],
            email=data["email"],
            name=data.get("name"),
            auth_time=datetime.fromtimestamp(data.get("auth_time", data["iat"]), UTC),
            mfa_verified="mfa" in data.get("amr", []),
            raw=data,
        )

    async def invite_user(self, email: str, full_name: str | None = None) -> str:
        return f"dev-{uuid.uuid5(uuid.NAMESPACE_URL, email.lower())}"

    async def disable_user(self, sub: str) -> None:
        self.disabled.add(sub)

    async def enable_user(self, sub: str) -> None:
        self.disabled.discard(sub)

    async def reset_mfa(self, sub: str) -> None:
        return None

    async def sign_out_everywhere(self, sub: str) -> None:
        return None
