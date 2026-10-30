"""DB roles and grants. The app role is a plain LOGIN role: not owner, no BYPASSRLS, INSERT/SELECT only on audit.

Revision ID: 0001
"""

import os

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    password = os.environ.get("APP_DB_PASSWORD")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    if password:
        escaped = password.replace("'", "''")
        op.execute(
            f"""
            DO $$
            BEGIN
              IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'complymate_app') THEN
                CREATE ROLE complymate_app LOGIN PASSWORD '{escaped}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
              ELSE
                ALTER ROLE complymate_app WITH LOGIN PASSWORD '{escaped}';
              END IF;
            END $$;
            """
        )
    else:
        op.execute(
            """
            DO $$
            BEGIN
              IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'complymate_app') THEN
                CREATE ROLE complymate_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
              END IF;
            END $$;
            """
        )
    op.execute("GRANT USAGE ON SCHEMA public TO complymate_app")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO complymate_app"
    )
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO complymate_app")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO complymate_app")

    # RLS helper functions
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app_current_tenant() RETURNS uuid LANGUAGE sql STABLE AS
        $$ SELECT NULLIF(current_setting('app.tenant_id', true), '')::uuid $$;
        CREATE OR REPLACE FUNCTION app_current_user() RETURNS uuid LANGUAGE sql STABLE AS
        $$ SELECT NULLIF(current_setting('app.user_id', true), '')::uuid $$;
        CREATE OR REPLACE FUNCTION app_is_platform() RETURNS boolean LANGUAGE sql STABLE AS
        $$ SELECT coalesce(current_setting('app.is_platform', true), 'off') = 'on' $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS app_is_platform(), app_current_user(), app_current_tenant()")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM complymate_app")
