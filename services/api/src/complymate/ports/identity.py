from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass
class TokenClaims:
    sub: str
    email: str
    name: str | None = None
    auth_time: datetime | None = None
    mfa_verified: bool = False
    groups: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


class IdentityProvider(Protocol):
    """OIDC identity (Cognito / Entra External ID / dev). Verifies tokens and manages users."""

    async def verify_token(self, token: str) -> TokenClaims: ...

    async def invite_user(self, email: str, full_name: str | None = None) -> str: ...

    async def disable_user(self, sub: str) -> None: ...

    async def enable_user(self, sub: str) -> None: ...

    async def reset_mfa(self, sub: str) -> None: ...

    async def sign_out_everywhere(self, sub: str) -> None: ...
