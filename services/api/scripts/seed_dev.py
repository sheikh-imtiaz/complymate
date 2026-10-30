"""Seeds a local demo firm with one user per role, plus reference data. Local development only.

uv run python scripts/seed_dev.py
"""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select

from complymate.adapters.local.dev_identity import DevIdentity
from complymate.container import get_container
from complymate.db.models import Client, Membership, Tenant, User
from complymate.db.repositories.programs import ProgramRepo
from complymate.db.repositories.tenants import TenantRepo
from complymate.db.repositories.users import UserRepo
from complymate.db.session import tenant_session
from complymate.workers import seed_reference

DEMO_TENANT = uuid.UUID("11111111-1111-4111-8111-111111111111")
USERS = [
    ("owner@demo.test", "Olivia Owner", "owner"),
    ("amlco@demo.test", "Aiden Compliance", "amlco"),
    ("manager@demo.test", "Maya Manager", "senior_manager"),
    ("staff@demo.test", "Sam Staff", "staff"),
    ("auditor@demo.test", "Ari Auditor", "auditor"),
]


async def main() -> None:
    container = get_container()
    assert container.settings.is_local, "seed_dev is for CLOUD_PROVIDER=local only"
    identity = container.identity
    assert isinstance(identity, DevIdentity)

    async with tenant_session(DEMO_TENANT) as session:
        repo = TenantRepo(session)
        if await repo.get(DEMO_TENANT) is None:
            await repo.create(
                Tenant(
                    id=DEMO_TENANT,
                    name="Demo Accounting Pty Ltd",
                    slug="demo-accounting",
                    jurisdiction="AU",
                    entity_type="company",
                    abn="51824753556",
                    services=["handling_client_money", "company_or_trust_formation"],
                    size="2-10",
                    status="active",
                    tranche2_applies=True,
                    plan_code="practice",
                ),
                "practice",
            )
        users = UserRepo(session)
        ids = {}
        for email, name, role_key in USERS:
            user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
            if user is None:
                user = User(
                    external_sub=await identity.invite_user(email), email=email, full_name=name, mfa_enrolled=True
                )
                session.add(user)
                await session.flush()
            ids[role_key] = user.id
            if await users.membership(DEMO_TENANT, user.id) is None:
                role = await users.role_by_key(role_key)
                assert role is not None
                session.add(Membership(tenant_id=DEMO_TENANT, user_id=user.id, role_id=role.id))
        tenant = await repo.get(DEMO_TENANT)
        assert tenant is not None
        tenant.amlco_user_id = ids["amlco"]
        await ProgramRepo(session).ensure(DEMO_TENANT, ids["owner"])
        if not (await session.execute(select(Client))).scalars().first():
            session.add_all(
                [
                    Client(
                        tenant_id=DEMO_TENANT,
                        client_type="individual",
                        display_name="Jane Citizen",
                        given_names="Jane",
                        family_name="Citizen",
                        residential_country="AU",
                        nationality="AU",
                        created_by=ids["staff"],
                        assigned_to=ids["staff"],
                        services=["handling_client_money"],
                    ),
                    Client(
                        tenant_id=DEMO_TENANT,
                        client_type="company",
                        display_name="Harbour Holdings Pty Ltd",
                        legal_name="Harbour Holdings Pty Ltd",
                        acn="123456789",
                        country_of_incorporation="AU",
                        created_by=ids["staff"],
                        assigned_to=ids["staff"],
                        services=["company_or_trust_formation"],
                        channel="non_face_to_face",
                    ),
                    Client(
                        tenant_id=DEMO_TENANT,
                        client_type="individual",
                        display_name="Viktor Ivanoff",
                        given_names="Viktor",
                        family_name="Ivanoff",
                        residential_country="RU",
                        nationality="RU",
                        created_by=ids["amlco"],
                        assigned_to=ids["amlco"],
                    ),
                ]
            )

    async with tenant_session(None, platform=True) as session:
        admin = (await session.execute(select(User).where(User.email == "admin@complymate.test"))).scalar_one_or_none()
        if admin is None:
            session.add(
                User(
                    external_sub=await identity.invite_user("admin@complymate.test"),
                    email="admin@complymate.test",
                    full_name="Platform Admin",
                    platform_role="super_admin",
                    mfa_enrolled=True,
                )
            )
    print(await seed_reference.run({}))
    print("Seeded. Sign in with any of:", ", ".join(u[0] for u in USERS), "or admin@complymate.test")


if __name__ == "__main__":
    asyncio.run(main())
