"""Tasks, comments, mentions, notifications, shares, presence.

Revision ID: 0010
"""

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE tasks (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            type varchar(30) NOT NULL,
            title varchar(300) NOT NULL,
            description text,
            resource_type varchar(40),
            resource_id varchar(64),
            assignee_id uuid,
            created_by uuid,
            status varchar(20) NOT NULL DEFAULT 'open' CHECK (status IN ('open','done','cancelled')),
            due_date date,
            escalated_at timestamptz,
            completed_at timestamptz,
            completed_by uuid,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_tasks_tenant_assignee ON tasks (tenant_id, assignee_id, status);
        CREATE INDEX ix_tasks_tenant_due ON tasks (tenant_id, status, due_date);

        CREATE TABLE comments (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            resource_type varchar(40) NOT NULL,
            resource_id varchar(64) NOT NULL,
            author_id uuid NOT NULL,
            body text NOT NULL,
            edited_at timestamptz,
            deleted_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_comments_resource ON comments (tenant_id, resource_type, resource_id);

        CREATE TABLE mentions (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            comment_id uuid NOT NULL REFERENCES comments(id) ON DELETE CASCADE,
            user_id uuid NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_mentions_tenant ON mentions (tenant_id);

        CREATE TABLE notifications (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            user_id uuid NOT NULL,
            kind varchar(40) NOT NULL,
            title varchar(300) NOT NULL,
            body text,
            link text,
            read_at timestamptz,
            emailed_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_notifications_user ON notifications (tenant_id, user_id, read_at);

        CREATE TABLE shares (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            resource_type varchar(40) NOT NULL,
            resource_id varchar(64) NOT NULL,
            grantee_user_id uuid NOT NULL,
            granted_by uuid NOT NULL,
            permission varchar(20) NOT NULL DEFAULT 'read',
            expires_at timestamptz NOT NULL,
            revoked_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_shares_grantee ON shares (tenant_id, grantee_user_id, resource_type);

        CREATE TABLE presence_heartbeats (
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            resource_type varchar(40) NOT NULL,
            resource_id varchar(64) NOT NULL,
            user_id uuid NOT NULL,
            last_seen_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (tenant_id, resource_type, resource_id, user_id)
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS presence_heartbeats, shares, notifications, mentions, comments, tasks CASCADE")
