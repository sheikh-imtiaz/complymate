"""Test fixtures.

Unit tests need nothing. Integration tests need PostgreSQL 16 + pgvector: set TEST_DATABASE_ADMIN_URL (owner
role on an empty database with the vector/pgcrypto/pg_trgm extensions available), or have Docker running and
Testcontainers starts `pgvector/pgvector:pg16`.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from typing import Any

import pytest

os.environ.setdefault("CLOUD_PROVIDER", "local")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DEV_JWT_SECRET", "test-secret")
os.environ.setdefault("APP_DB_PASSWORD", "app_test_password")
os.environ.setdefault("LOG_LEVEL", "WARNING")


class InMemoryStorage:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], tuple[bytes, str, dict[str, str]]] = {}

    async def put_object(
        self, bucket: str, key: str, data: bytes, content_type: str, metadata: dict[str, str] | None = None
    ) -> None:
        self.objects[(bucket, key)] = (data, content_type, metadata or {})

    async def get_object(self, bucket: str, key: str) -> Any:
        from complymate.ports.storage import StoredObject

        data, ct, md = self.objects[(bucket, key)]
        return StoredObject(key, data, ct, md)

    async def delete_object(self, bucket: str, key: str) -> None:
        self.objects.pop((bucket, key), None)

    async def presigned_get_url(self, bucket: str, key: str, expires_seconds: int = 300) -> str:
        return f"memory://{bucket}/{key}"


@pytest.fixture(scope="session")
def pg_urls() -> Iterator[tuple[str, str]]:
    admin = os.environ.get("TEST_DATABASE_ADMIN_URL")
    if admin:
        app = admin.replace(
            admin.split("://", 1)[1].split("@", 1)[0], f"complymate_app:{os.environ['APP_DB_PASSWORD']}"
        )
        yield admin, app
        return
    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError:  # pragma: no cover
        pytest.skip("integration tests need TEST_DATABASE_ADMIN_URL or testcontainers")
    try:
        container = PostgresContainer(
            "pgvector/pgvector:pg16", username="complymate_owner", password="owner", dbname="complymate"
        )
        container.start()
    except Exception as exc:
        pytest.skip(f"no database available for integration tests: {exc}")
    host, port = container.get_container_host_ip(), container.get_exposed_port(5432)
    yield (
        f"postgresql+asyncpg://complymate_owner:owner@{host}:{port}/complymate",
        f"postgresql+asyncpg://complymate_app:{os.environ['APP_DB_PASSWORD']}@{host}:{port}/complymate",
    )
    container.stop()


@pytest.fixture(scope="session")
def migrated(pg_urls: tuple[str, str]) -> tuple[str, str]:
    from alembic import command
    from alembic.config import Config

    admin, app = pg_urls
    os.environ["DATABASE_ADMIN_URL"] = admin
    os.environ["DATABASE_URL"] = app
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(here, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(here, "migrations"))
    command.downgrade(cfg, "base") if os.environ.get("TEST_RESET_DB") else None
    command.upgrade(cfg, "head")
    return admin, app


@pytest.fixture(scope="session")
def container(migrated: tuple[str, str]) -> Iterator[Any]:
    from complymate.config import Settings
    from complymate.container import build_container, set_container

    admin, app = migrated
    settings = Settings(
        cloud_provider="local",
        database_url=app,
        database_admin_url=admin,
        dev_jwt_secret="test-secret",
        environment="test",
        audit_sink_dir="/tmp/complymate-test-audit",
    )
    c = build_container(settings)
    c.storage = InMemoryStorage()  # type: ignore[assignment]
    c.queue.run_inline = False  # type: ignore[attr-defined]
    set_container(c)
    yield c
    set_container(None)


@pytest.fixture(scope="session")
async def admin_engine(migrated: tuple[str, str]) -> AsyncIterator[Any]:
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(migrated[0])
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
async def http(container: Any) -> AsyncIterator[Any]:
    import httpx

    from complymate.main import app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client


@dataclass
class Firm:
    tenant_id: uuid.UUID
    users: dict[str, uuid.UUID]
    emails: dict[str, str]


@pytest.fixture(scope="session")
def token(container: Any) -> Any:
    def make(email: str) -> str:
        sub = f"dev-{uuid.uuid5(uuid.NAMESPACE_URL, email.lower())}"
        return container.identity.issue_token(sub, email)

    return make


@pytest.fixture(scope="session")
def headers(token: Any) -> Any:
    def make(email: str, tenant_id: uuid.UUID | None = None) -> dict[str, str]:
        h = {"Authorization": f"Bearer {token(email)}"}
        if tenant_id:
            h["X-Tenant-Id"] = str(tenant_id)
        return h

    return make


@pytest.fixture(scope="session")
def make_firm(admin_engine: Any, container: Any) -> Any:
    """Creates a firm with one user per role directly in the DB (owner connection bypasses RLS)."""
    from sqlalchemy import text

    async def make(
        name: str,
        roles: tuple[str, ...] = ("owner", "amlco", "senior_manager", "staff", "auditor"),
        plan: str = "practice",
    ) -> Firm:
        tid = uuid.uuid4()
        tag = tid.hex[:6]
        users: dict[str, uuid.UUID] = {}
        emails: dict[str, str] = {}
        async with admin_engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO tenants (id, name, slug, jurisdiction, status, plan_code, services) "
                    "VALUES (:id, :n, :s, 'AU', 'active', :p, '[\"handling_client_money\"]')"
                ),
                {"id": tid, "n": name, "s": f"{tag}-firm", "p": plan},
            )
            await conn.execute(text("INSERT INTO tenant_settings (tenant_id) VALUES (:id)"), {"id": tid})
            await conn.execute(
                text("INSERT INTO subscriptions (tenant_id, plan_code, status) VALUES (:id, :p, 'active')"),
                {"id": tid, "p": plan},
            )
            for role in roles:
                email = f"{role}.{tag}@test.example"
                uid = uuid.uuid4()
                await conn.execute(
                    text(
                        "INSERT INTO users (id, external_sub, email, full_name, mfa_enrolled) VALUES (:id, :sub, :e, :n, true)"
                    ),
                    {
                        "id": uid,
                        "sub": f"dev-{uuid.uuid5(uuid.NAMESPACE_URL, email)}",
                        "e": email,
                        "n": f"{role.title()} {tag}",
                    },
                )
                await conn.execute(
                    text(
                        "INSERT INTO memberships (tenant_id, user_id, role_id) "
                        "VALUES (:t, :u, (SELECT id FROM roles WHERE tenant_id IS NULL AND key = :k))"
                    ),
                    {"t": tid, "u": uid, "k": role},
                )
                users[role], emails[role] = uid, email
            if "amlco" in users:
                await conn.execute(
                    text("UPDATE tenants SET amlco_user_id = :u WHERE id = :t"), {"u": users["amlco"], "t": tid}
                )
        return Firm(tid, users, emails)

    return make


@pytest.fixture(scope="session")
async def seeded_watchlist(container: Any) -> None:
    from complymate.workers import refresh_watchlists

    await refresh_watchlists.run({"skip_rescreen": True})
