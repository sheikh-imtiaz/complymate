"""Suspicious matter reports.

Revision ID: 0008
"""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE smr_cases (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            reference varchar(30) NOT NULL,
            client_id uuid REFERENCES clients(id) ON DELETE SET NULL,
            status varchar(30) NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft','under_review','decided_report','decided_no_report','exported')),
            raised_by uuid NOT NULL,
            assigned_to uuid,
            summary text NOT NULL,
            grounds text,
            suspicion_categories jsonb NOT NULL DEFAULT '[]',
            transaction_details jsonb NOT NULL DEFAULT '{}',
            austrac_fields jsonb NOT NULL DEFAULT '{}',
            ai_suggestion jsonb,
            decision_reason text,
            decided_by uuid,
            decided_at timestamptz,
            exported_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (tenant_id, reference)
        );

        CREATE TABLE smr_notes (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            case_id uuid NOT NULL REFERENCES smr_cases(id) ON DELETE CASCADE,
            author_id uuid NOT NULL,
            body text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_smr_notes_case ON smr_notes (case_id);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS smr_notes, smr_cases CASCADE")
