"""Creates (or promotes) a platform user. On AWS the identity is created in Cognito first.

uv run python scripts/create_super_admin.py founder@example.com "Founder Name" [--role super_admin]
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from complymate.container import get_container
from complymate.db.models import User
from complymate.db.session import tenant_session
from complymate.domain.audit.events import Action
from complymate.workers._common import system_audit


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("email")
    parser.add_argument("name")
    parser.add_argument("--role", default="super_admin", choices=["super_admin", "platform_support", "content_manager"])
    args = parser.parse_args()
    sub = await get_container().identity.invite_user(args.email, args.name)
    async with tenant_session(None, platform=True) as session:
        user = (await session.execute(select(User).where(User.email == args.email.lower()))).scalar_one_or_none()
        if user is None:
            user = User(external_sub=sub, email=args.email.lower(), full_name=args.name)
            session.add(user)
        user.platform_role = args.role
        await session.flush()
        await system_audit(session, None, Action.ROLE_CHANGE, "user", user.id, after={"platform_role": args.role})
    print(f"{args.email} is now {args.role}")


if __name__ == "__main__":
    asyncio.run(main())
