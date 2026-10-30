"""Core: tenants, tenant_settings, users.

Revision ID: 0002
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE tenants (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            name varchar(200) NOT NULL,
            slug varchar(80) NOT NULL UNIQUE,
            jurisdiction varchar(2) NOT NULL DEFAULT 'AU' CHECK (jurisdiction IN ('AU','NZ')),
            entity_type varchar(40),
            abn varchar(20),
            nzbn varchar(20),
            services jsonb NOT NULL DEFAULT '[]',
            size varchar(20),
            status varchar(20) NOT NULL DEFAULT 'trial' CHECK (status IN ('trial','active','suspended','cancelled')),
            tranche2_applies boolean,
            amlco_user_id uuid,
            plan_code varchar(20) NOT NULL DEFAULT 'solo',
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        );

        CREATE TABLE tenant_settings (
            tenant_id uuid PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
            mfa_required boolean NOT NULL DEFAULT true,
            session_timeout_minutes integer NOT NULL DEFAULT 30 CHECK (session_timeout_minutes BETWEEN 5 AND 720),
            ip_allow_list jsonb NOT NULL DEFAULT '[]',
            retention_years integer NOT NULL DEFAULT 7 CHECK (retention_years >= 7),
            branding jsonb NOT NULL DEFAULT '{}',
            integrations jsonb NOT NULL DEFAULT '{}',
            onboarding jsonb NOT NULL DEFAULT '{}',
            allow_support_impersonation boolean NOT NULL DEFAULT false,
            encrypted_data_key bytea,
            updated_at timestamptz NOT NULL DEFAULT now()
        );

        CREATE TABLE users (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            external_sub varchar(200) NOT NULL UNIQUE,
            email varchar(320) NOT NULL UNIQUE,
            full_name varchar(200),
            platform_role varchar(40) CHECK (platform_role IN ('super_admin','platform_support','content_manager')),
            status varchar(20) NOT NULL DEFAULT 'active',
            mfa_enrolled boolean NOT NULL DEFAULT false,
            last_login_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_users_email_lower ON users (lower(email));
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS users, tenant_settings, tenants CASCADE")
