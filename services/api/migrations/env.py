"""Alembic environment. Runs as the OWNER role (DATABASE_ADMIN_URL or DB_ADMIN_SECRET_ARN), never the app role.

Migrations use a synchronous psycopg connection: migration files contain multi-statement SQL (functions, policies)
which asyncpg cannot run as one prepared statement.
"""

from __future__ import annotations

import asyncio
import os

from alembic import context
from sqlalchemy import create_engine

from complymate.db import models  # noqa: F401  (registers tables)
from complymate.db.base import Base

config = context.config
target_metadata = Base.metadata


def _admin_url() -> str:
    url = os.environ.get("DATABASE_ADMIN_URL")
    if not url:
        from complymate.container import get_container

        url = asyncio.run(get_container().database_url(admin=True))
    return url.replace("+asyncpg", "+psycopg")


def run_migrations_offline() -> None:
    context.configure(url=_admin_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connect_args = {} if os.environ.get("CLOUD_PROVIDER", "local") == "local" else {"sslmode": "require"}
    engine = create_engine(_admin_url(), connect_args=connect_args)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
