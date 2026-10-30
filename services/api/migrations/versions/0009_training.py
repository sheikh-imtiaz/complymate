"""Training modules, quiz questions, assignments, attempts.

Revision ID: 0009
"""

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE training_modules (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid REFERENCES tenants(id) ON DELETE CASCADE,
            title varchar(200) NOT NULL,
            description text,
            content_md text NOT NULL DEFAULT '',
            roles jsonb NOT NULL DEFAULT '[]',
            jurisdiction varchar(2) NOT NULL DEFAULT 'AU',
            duration_minutes integer NOT NULL DEFAULT 15,
            pass_mark integer NOT NULL DEFAULT 80,
            status varchar(20) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','in_review','published','archived')),
            version integer NOT NULL DEFAULT 1,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_training_modules_tenant ON training_modules (tenant_id);

        CREATE TABLE quiz_questions (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid REFERENCES tenants(id) ON DELETE CASCADE,
            module_id uuid NOT NULL REFERENCES training_modules(id) ON DELETE CASCADE,
            question text NOT NULL,
            options jsonb NOT NULL DEFAULT '[]',
            correct_index integer NOT NULL,
            explanation text,
            source_citation jsonb,
            review_status varchar(20) NOT NULL DEFAULT 'draft' CHECK (review_status IN ('draft','approved','rejected')),
            ai_generated boolean NOT NULL DEFAULT false,
            reviewed_by uuid,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_quiz_questions_module ON quiz_questions (module_id);

        CREATE TABLE training_assignments (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            module_id uuid NOT NULL REFERENCES training_modules(id) ON DELETE CASCADE,
            user_id uuid NOT NULL,
            due_date date,
            completed_at timestamptz,
            reminded_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (tenant_id, module_id, user_id)
        );

        CREATE TABLE quiz_attempts (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            module_id uuid NOT NULL REFERENCES training_modules(id) ON DELETE CASCADE,
            user_id uuid NOT NULL,
            answers jsonb NOT NULL DEFAULT '{}',
            score numeric(5,1) NOT NULL,
            passed boolean NOT NULL,
            certificate_key text,
            completed_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_quiz_attempts_tenant_user ON quiz_attempts (tenant_id, user_id);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS quiz_attempts, training_assignments, quiz_questions, training_modules CASCADE")
