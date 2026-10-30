"""RBAC: roles, role_permissions, memberships, invitations, api_keys. Seeds the system roles.

Revision ID: 0003
"""

from alembic import op

from complymate.domain.rbac.roles import TENANT_ROLES

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE roles (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid REFERENCES tenants(id) ON DELETE CASCADE,
            key varchar(60) NOT NULL,
            name varchar(120) NOT NULL,
            description text,
            is_system boolean NOT NULL DEFAULT false,
            base_role_key varchar(60),
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE UNIQUE INDEX uq_roles_tenant_key ON roles (coalesce(tenant_id, '00000000-0000-0000-0000-000000000000'::uuid), key);

        CREATE TABLE role_permissions (
            role_id uuid NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
            permission varchar(80) NOT NULL,
            tenant_id uuid,
            PRIMARY KEY (role_id, permission)
        );

        CREATE TABLE memberships (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role_id uuid NOT NULL REFERENCES roles(id),
            status varchar(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active','deactivated')),
            expires_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (tenant_id, user_id)
        );
        CREATE INDEX ix_memberships_user ON memberships (user_id);

        CREATE TABLE invitations (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            email varchar(320) NOT NULL,
            full_name varchar(200),
            role_id uuid NOT NULL REFERENCES roles(id),
            token_hash varchar(64) NOT NULL UNIQUE,
            invited_by uuid,
            expires_at timestamptz NOT NULL,
            accepted_at timestamptz,
            revoked_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_invitations_tenant ON invitations (tenant_id);

        CREATE TABLE api_keys (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            name varchar(120) NOT NULL,
            prefix varchar(16) NOT NULL UNIQUE,
            key_hash varchar(64) NOT NULL,
            permissions jsonb NOT NULL DEFAULT '[]',
            created_by uuid,
            last_used_at timestamptz,
            expires_at timestamptz,
            revoked_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_api_keys_tenant ON api_keys (tenant_id);
        """
    )
    for role in TENANT_ROLES.values():
        name = role.name.replace("'", "''")
        desc = role.description.replace("'", "''")
        op.execute(
            f"INSERT INTO roles (tenant_id, key, name, description, is_system) "
            f"VALUES (NULL, '{role.key}', '{name}', '{desc}', true)"
        )
        values = ", ".join(
            f"((SELECT id FROM roles WHERE tenant_id IS NULL AND key = '{role.key}'), '{p}')"
            for p in sorted(role.permissions)
        )
        op.execute(f"INSERT INTO role_permissions (role_id, permission) VALUES {values}")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS api_keys, invitations, memberships, role_permissions, roles CASCADE")
