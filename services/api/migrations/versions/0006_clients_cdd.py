"""Clients, parties (beneficial owners), documents, verifications, risk assessments, EDD tasks.

Revision ID: 0006
"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE clients (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            client_type varchar(20) NOT NULL CHECK (client_type IN ('individual','company','trust','partnership')),
            display_name varchar(300) NOT NULL,
            legal_name varchar(300),
            given_names varchar(200),
            family_name varchar(200),
            date_of_birth date,
            abn varchar(20),
            acn varchar(20),
            registration_number varchar(40),
            incorporated_on date,
            country_of_incorporation varchar(2),
            nationality varchar(2),
            residential_country varchar(2),
            address jsonb NOT NULL DEFAULT '{}',
            occupation varchar(200),
            services jsonb NOT NULL DEFAULT '[]',
            channel varchar(30) NOT NULL DEFAULT 'face_to_face',
            source_of_funds text,
            source_of_funds_verified boolean NOT NULL DEFAULT false,
            source_of_wealth text,
            cash_intensive boolean NOT NULL DEFAULT false,
            nominee_directors boolean NOT NULL DEFAULT false,
            bearer_shares boolean NOT NULL DEFAULT false,
            is_pep boolean NOT NULL DEFAULT false,
            pep_details text,
            status varchar(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','declined','exited')),
            risk_level varchar(10) CHECK (risk_level IN ('low','medium','high')),
            risk_score integer,
            last_screened_at timestamptz,
            next_review_date date,
            assigned_to uuid,
            created_by uuid,
            approved_by uuid,
            approved_at timestamptz,
            status_reason text,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_clients_tenant ON clients (tenant_id);
        CREATE INDEX ix_clients_tenant_status ON clients (tenant_id, status);
        CREATE INDEX ix_clients_tenant_review ON clients (tenant_id, next_review_date);
        CREATE INDEX ix_clients_name_trgm ON clients USING gin (display_name gin_trgm_ops);

        CREATE TABLE client_parties (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            client_id uuid NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
            parent_party_id uuid REFERENCES client_parties(id) ON DELETE CASCADE,
            party_type varchar(40) NOT NULL,
            is_entity boolean NOT NULL DEFAULT false,
            full_name varchar(300) NOT NULL,
            date_of_birth date,
            country varchar(2),
            ownership_percent numeric(6,3) CHECK (ownership_percent IS NULL OR (ownership_percent >= 0 AND ownership_percent <= 100)),
            has_control boolean NOT NULL DEFAULT false,
            is_pep boolean NOT NULL DEFAULT false,
            verified boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_client_parties_client ON client_parties (client_id);
        CREATE INDEX ix_client_parties_tenant ON client_parties (tenant_id);

        CREATE TABLE client_documents (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            client_id uuid NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
            party_id uuid REFERENCES client_parties(id) ON DELETE SET NULL,
            doc_type varchar(40) NOT NULL,
            storage_key text NOT NULL,
            filename varchar(255) NOT NULL,
            content_type varchar(100) NOT NULL,
            size_bytes bigint NOT NULL,
            sha256 varchar(64) NOT NULL,
            encrypted boolean NOT NULL DEFAULT true,
            ocr_status varchar(20) NOT NULL DEFAULT 'pending',
            ocr_fields jsonb NOT NULL DEFAULT '{}',
            ocr_confidence jsonb NOT NULL DEFAULT '{}',
            ocr_confirmed boolean NOT NULL DEFAULT false,
            confirmed_by uuid,
            uploaded_by uuid,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_client_documents_client ON client_documents (client_id);
        CREATE INDEX ix_client_documents_tenant ON client_documents (tenant_id);

        CREATE TABLE verifications (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            client_id uuid NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
            party_id uuid REFERENCES client_parties(id) ON DELETE SET NULL,
            method varchar(20) NOT NULL DEFAULT 'manual',
            checklist jsonb NOT NULL DEFAULT '{}',
            result varchar(20) NOT NULL DEFAULT 'pending',
            verified_by uuid,
            verified_at timestamptz,
            provider_ref varchar(200),
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_verifications_client ON verifications (client_id);
        CREATE INDEX ix_verifications_tenant ON verifications (tenant_id);

        CREATE TABLE risk_assessments (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            client_id uuid NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
            rules_version varchar(40) NOT NULL,
            score integer NOT NULL,
            level varchar(10) NOT NULL,
            reasons jsonb NOT NULL DEFAULT '[]',
            facts jsonb NOT NULL DEFAULT '{}',
            status varchar(20) NOT NULL DEFAULT 'proposed',
            override_level varchar(10),
            override_reason text,
            created_by uuid,
            approved_by uuid,
            approved_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_risk_assessments_client ON risk_assessments (client_id);
        CREATE INDEX ix_risk_assessments_tenant ON risk_assessments (tenant_id);

        CREATE TABLE risk_factors (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            assessment_id uuid NOT NULL REFERENCES risk_assessments(id) ON DELETE CASCADE,
            factor_key varchar(80) NOT NULL,
            category varchar(20) NOT NULL,
            description text NOT NULL,
            points integer NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_risk_factors_assessment ON risk_factors (assessment_id);
        CREATE INDEX ix_risk_factors_tenant ON risk_factors (tenant_id);

        CREATE TABLE edd_tasks (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            client_id uuid NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
            assessment_id uuid REFERENCES risk_assessments(id) ON DELETE SET NULL,
            key varchar(60) NOT NULL,
            title varchar(300) NOT NULL,
            status varchar(20) NOT NULL DEFAULT 'open' CHECK (status IN ('open','done','waived')),
            evidence jsonb NOT NULL DEFAULT '{}',
            completed_by uuid,
            completed_at timestamptz,
            due_date date,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_edd_tasks_client ON edd_tasks (client_id);
        CREATE INDEX ix_edd_tasks_tenant ON edd_tasks (tenant_id);
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TABLE IF EXISTS edd_tasks, risk_factors, risk_assessments, verifications, client_documents, "
        "client_parties, clients CASCADE"
    )
