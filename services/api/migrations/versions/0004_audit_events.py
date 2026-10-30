"""Audit events: append-only (INSERT/SELECT grants only + immutability trigger), per-tenant hash chain.

Revision ID: 0004
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE audit_events (
            id uuid PRIMARY KEY,
            seq bigint GENERATED ALWAYS AS IDENTITY UNIQUE,
            tenant_id uuid,
            actor_id uuid,
            actor_role varchar(60) NOT NULL,
            action varchar(60) NOT NULL,
            resource_type varchar(60) NOT NULL,
            resource_id varchar(100),
            before jsonb,
            after jsonb,
            reason text,
            ip varchar(64),
            user_agent varchar(400),
            request_id varchar(64),
            ai jsonb,
            occurred_at timestamptz NOT NULL,
            prev_hash varchar(64),
            hash varchar(64) NOT NULL
        );
        CREATE INDEX ix_audit_tenant_seq ON audit_events (tenant_id, seq);
        CREATE INDEX ix_audit_tenant_resource ON audit_events (tenant_id, resource_type, resource_id);
        CREATE INDEX ix_audit_tenant_actor ON audit_events (tenant_id, actor_id, occurred_at);
        CREATE INDEX ix_audit_tenant_time ON audit_events (tenant_id, occurred_at);

        -- Defence in depth: even the owner cannot change history.
        CREATE OR REPLACE FUNCTION audit_events_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'audit_events is append-only';
        END $$;
        CREATE TRIGGER trg_audit_events_no_update BEFORE UPDATE OR DELETE ON audit_events
            FOR EACH ROW EXECUTE FUNCTION audit_events_immutable();
        CREATE TRIGGER trg_audit_events_no_truncate BEFORE TRUNCATE ON audit_events
            FOR EACH STATEMENT EXECUTE FUNCTION audit_events_immutable();

        REVOKE ALL ON audit_events FROM complymate_app;
        GRANT SELECT, INSERT ON audit_events TO complymate_app;

        CREATE TABLE audit_archive_cursors (
            tenant_key varchar(40) PRIMARY KEY,
            last_seq bigint NOT NULL DEFAULT 0,
            last_location text,
            updated_at timestamptz NOT NULL DEFAULT now()
        );

        CREATE TABLE audit_chain_verifications (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid,
            ok boolean NOT NULL,
            checked integer NOT NULL,
            broken_at_id varchar(64),
            reason text,
            checked_at timestamptz NOT NULL DEFAULT now()
        );
        REVOKE UPDATE, DELETE ON audit_chain_verifications FROM complymate_app;
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_chain_verifications, audit_archive_cursors CASCADE")
    op.execute("DROP TRIGGER IF EXISTS trg_audit_events_no_truncate ON audit_events")
    op.execute("DROP TRIGGER IF EXISTS trg_audit_events_no_update ON audit_events")
    op.execute("DROP TABLE IF EXISTS audit_events CASCADE")
    op.execute("DROP FUNCTION IF EXISTS audit_events_immutable()")
