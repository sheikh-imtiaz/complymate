"""Watchlists (global reference data) and screening runs/matches.

Revision ID: 0007
"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE watchlist_versions (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            source varchar(20) NOT NULL,
            version_label varchar(100) NOT NULL,
            checksum varchar(64) NOT NULL,
            entry_count integer NOT NULL DEFAULT 0,
            is_current boolean NOT NULL DEFAULT false,
            fetched_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE UNIQUE INDEX uq_watchlist_current ON watchlist_versions (source) WHERE is_current;

        CREATE TABLE watchlist_entries (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            version_id uuid NOT NULL REFERENCES watchlist_versions(id) ON DELETE CASCADE,
            source varchar(20) NOT NULL,
            reference varchar(60) NOT NULL,
            entity_type varchar(20) NOT NULL,
            primary_name text NOT NULL,
            aliases jsonb NOT NULL DEFAULT '[]',
            normalized_names text[] NOT NULL,
            search_text text NOT NULL,
            dob varchar(60),
            nationality varchar(200),
            program text
        );
        CREATE INDEX ix_watchlist_entries_version ON watchlist_entries (version_id);
        CREATE INDEX ix_watchlist_entries_trgm ON watchlist_entries USING gin (search_text gin_trgm_ops);

        CREATE TABLE screening_runs (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            client_id uuid NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
            trigger varchar(20) NOT NULL,
            watchlist_version_ids jsonb NOT NULL DEFAULT '[]',
            screened_names jsonb NOT NULL DEFAULT '[]',
            status varchar(20) NOT NULL DEFAULT 'completed',
            match_count integer NOT NULL DEFAULT 0,
            pep_declared boolean NOT NULL DEFAULT false,
            started_by uuid,
            completed_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_screening_runs_client ON screening_runs (client_id);
        CREATE INDEX ix_screening_runs_tenant ON screening_runs (tenant_id);

        CREATE TABLE screening_matches (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            run_id uuid NOT NULL REFERENCES screening_runs(id) ON DELETE CASCADE,
            client_id uuid NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
            party_id uuid,
            entry_id uuid NOT NULL REFERENCES watchlist_entries(id),
            subject_name text NOT NULL,
            matched_name text NOT NULL,
            score numeric(5,1) NOT NULL,
            method varchar(30) NOT NULL,
            status varchar(20) NOT NULL DEFAULT 'open'
                CHECK (status IN ('open','true_match','false_positive','needs_info','superseded')),
            reviewed_by uuid,
            reviewed_at timestamptz,
            review_note text,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_screening_matches_tenant_status ON screening_matches (tenant_id, status);
        CREATE INDEX ix_screening_matches_client ON screening_matches (client_id);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS screening_matches, screening_runs, watchlist_entries, watchlist_versions CASCADE")
