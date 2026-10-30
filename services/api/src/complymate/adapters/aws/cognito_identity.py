"""Amazon Cognito user pool (OIDC). Tokens are verified against the pool JWKS."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

import jwt

from complymate.adapters.aws._session import client
from complymate.ports.identity import TokenClaims


class CognitoIdentity:
    def __init__(self, region: str, user_pool_id: str, audience: str) -> None:
        self.region = region
        self.user_pool_id = user_pool_id
        # Comma-separated: the tenant web app and the platform admin app use different app clients.
        self.audiences = [a.strip() for a in audience.split(",") if a.strip()]
        self.issuer = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}"
        self._jwks = jwt.PyJWKClient(f"{self.issuer}/.well-known/jwks.json", cache_keys=True, lifespan=3600)
        self._client = client("cognito-idp", region)

    async def verify_token(self, token: str) -> TokenClaims:
        signing_key = await asyncio.to_thread(self._jwks.get_signing_key_from_jwt, token)
        unverified = jwt.decode(token, options={"verify_signature": False})
        # ID tokens carry `aud`; access tokens carry `client_id`.
        if unverified.get("token_use") == "access":
            data: dict[str, Any] = jwt.decode(
                token, signing_key.key, algorithms=["RS256"], issuer=self.issuer, options={"verify_aud": False}
            )
            if data.get("client_id") not in self.audiences:
                raise jwt.InvalidAudienceError("wrong client_id")
        else:
            data = jwt.decode(token, signing_key.key, algorithms=["RS256"], issuer=self.issuer, audience=self.audiences)
        auth_time = data.get("auth_time")
        return TokenClaims(
            sub=data["sub"],
            email=data.get("email", data.get("username", "")),
            name=data.get("name"),
            auth_time=datetime.fromtimestamp(auth_time, UTC) if auth_time else None,
            # MFA is REQUIRED on the pool, so every successful sign-in passed MFA.
            mfa_verified=True,
            groups=data.get("cognito:groups", []),
            raw=data,
        )

    async def invite_user(self, email: str, full_name: str | None = None) -> str:
        attrs = [{"Name": "email", "Value": email}, {"Name": "email_verified", "Value": "true"}]
        if full_name:
            attrs.append({"Name": "name", "Value": full_name})
        try:
            resp = await asyncio.to_thread(
                self._client.admin_create_user,
                UserPoolId=self.user_pool_id,
                Username=email,
                UserAttributes=attrs,
                DesiredDeliveryMediums=["EMAIL"],
            )
            user = resp["User"]
        except self._client.exceptions.UsernameExistsException:
            user = await asyncio.to_thread(self._client.admin_get_user, UserPoolId=self.user_pool_id, Username=email)
            user = {"Attributes": user["UserAttributes"]}
        sub = next(a["Value"] for a in user["Attributes"] if a["Name"] == "sub")
        return str(sub)

    async def _username(self, sub: str) -> str:
        resp = await asyncio.to_thread(
            self._client.list_users, UserPoolId=self.user_pool_id, Filter=f'sub = "{sub}"', Limit=1
        )
        return str(resp["Users"][0]["Username"])

    async def disable_user(self, sub: str) -> None:
        username = await self._username(sub)
        await asyncio.to_thread(self._client.admin_disable_user, UserPoolId=self.user_pool_id, Username=username)
        await asyncio.to_thread(
            self._client.admin_user_global_sign_out, UserPoolId=self.user_pool_id, Username=username
        )

    async def enable_user(self, sub: str) -> None:
        username = await self._username(sub)
        await asyncio.to_thread(self._client.admin_enable_user, UserPoolId=self.user_pool_id, Username=username)

    async def reset_mfa(self, sub: str) -> None:
        username = await self._username(sub)
        await asyncio.to_thread(
            self._client.admin_set_user_mfa_preference,
            UserPoolId=self.user_pool_id,
            Username=username,
            SoftwareTokenMfaSettings={"Enabled": False, "PreferredMfa": False},
        )
        await asyncio.to_thread(
            self._client.admin_user_global_sign_out, UserPoolId=self.user_pool_id, Username=username
        )

    async def sign_out_everywhere(self, sub: str) -> None:
        username = await self._username(sub)
        await asyncio.to_thread(
            self._client.admin_user_global_sign_out, UserPoolId=self.user_pool_id, Username=username
        )

    @staticmethod
    def now() -> datetime:
        return datetime.now(UTC)
