"""Programs, versions, sections, approvals.

Revision ID: 0005
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE programs (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            name varchar(200) NOT NULL DEFAULT 'AML/CTF Program',
            status varchar(30) NOT NULL DEFAULT 'draft',
            current_version_id uuid,
            approved_version_id uuid,
            interview_answers jsonb NOT NULL DEFAULT '{}',
            risk_methodology jsonb NOT NULL DEFAULT '{}',
            next_review_due date,
            created_by uuid,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (tenant_id)
        );

        CREATE TABLE program_versions (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            program_id uuid NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
            version_number integer NOT NULL,
            status varchar(30) NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft','in_review','awaiting_signoff','approved','superseded')),
            change_summary text,
            created_by uuid,
            submitted_by uuid,
            submitted_at timestamptz,
            reviewed_by uuid,
            approved_by uuid,
            approved_at timestamptz,
            locked boolean NOT NULL DEFAULT false,
            snapshot jsonb,
            draft_status varchar(30),
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (program_id, version_number)
        );
        CREATE INDEX ix_program_versions_tenant ON program_versions (tenant_id);

        CREATE TABLE program_sections (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            version_id uuid NOT NULL REFERENCES program_versions(id) ON DELETE CASCADE,
            key varchar(60) NOT NULL,
            title varchar(200) NOT NULL,
            position integer NOT NULL,
            content_html text NOT NULL DEFAULT '',
            citations jsonb NOT NULL DEFAULT '[]',
            ai_generated boolean NOT NULL DEFAULT false,
            ai_accepted boolean,
            ai_draft_html text,
            tracked_changes jsonb NOT NULL DEFAULT '[]',
            locked_by uuid,
            locked_until timestamptz,
            updated_by uuid,
            updated_at timestamptz,
            UNIQUE (version_id, key)
        );
        CREATE INDEX ix_program_sections_tenant ON program_sections (tenant_id);

        CREATE TABLE program_approvals (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            version_id uuid NOT NULL REFERENCES program_versions(id) ON DELETE CASCADE,
            step varchar(30) NOT NULL,
            decision varchar(20) NOT NULL CHECK (decision IN ('approved','rejected')),
            decided_by uuid NOT NULL,
            decided_role varchar(60) NOT NULL,
            comment text,
            decided_at timestamptz NOT NULL
        );
        CREATE INDEX ix_program_approvals_tenant ON program_approvals (tenant_id);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS program_approvals, program_sections, program_versions, programs CASCADE")
