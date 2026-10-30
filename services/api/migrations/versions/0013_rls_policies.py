"""Row-Level Security on every tenant table. Second lock after the API permission check.

* app.tenant_id   — set per transaction by db/session.py
* app.user_id     — lets a user list their own memberships before choosing a tenant
* app.is_platform — platform staff context; NEVER grants access to ID documents, parties or SMRs

SECURITY DEFINER functions resolve invitation and API key lookups that happen before the tenant is known.

Revision ID: 0013
"""

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

T = "tenant_id = app_current_tenant()"
P = "app_is_platform()"

# Strict tenant isolation, no platform access (sensitive client data).
STRICT = [
    "client_parties",
    "client_documents",
    "verifications",
    "smr_cases",
    "smr_notes",
]
# Tenant data that platform staff may read/maintain for support (metadata only).
TENANT_OR_PLATFORM = [
    "tenant_settings",
    "subscriptions",
    "usage_counters",
    "impersonation_sessions",
    "invitations",
    "api_keys",
    "chat_messages",
    "ai_feedback",
]
# Ordinary tenant tables.
TENANT_ONLY = [
    "programs",
    "program_versions",
    "program_sections",
    "program_approvals",
    "clients",
    "risk_assessments",
    "risk_factors",
    "edd_tasks",
    "screening_runs",
    "screening_matches",
    "training_assignments",
    "quiz_attempts",
    "tasks",
    "comments",
    "mentions",
    "notifications",
    "shares",
    "presence_heartbeats",
    "chat_sessions",
    "report_jobs",
    "exports",
]
# Platform content (tenant_id NULL) readable by all tenants; tenants may add their own rows.
SHARED_CONTENT = ["training_modules", "quiz_questions", "feature_flags"]


def _enable(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def upgrade() -> None:
    for t in STRICT:
        _enable(t)
        op.execute(f"CREATE POLICY tenant_isolation ON {t} USING ({T}) WITH CHECK ({T})")

    for t in TENANT_OR_PLATFORM:
        _enable(t)
        op.execute(f"CREATE POLICY tenant_isolation ON {t} USING ({T} OR {P}) WITH CHECK ({T} OR {P})")

    for t in TENANT_ONLY:
        _enable(t)
        op.execute(f"CREATE POLICY tenant_isolation ON {t} USING ({T}) WITH CHECK ({T})")

    for t in SHARED_CONTENT:
        _enable(t)
        op.execute(f"CREATE POLICY content_read ON {t} FOR SELECT USING (tenant_id IS NULL OR {T} OR {P})")
        op.execute(f"CREATE POLICY content_write ON {t} FOR INSERT WITH CHECK ({T} OR {P})")
        op.execute(f"CREATE POLICY content_update ON {t} FOR UPDATE USING ({T} OR {P}) WITH CHECK ({T} OR {P})")
        op.execute(f"CREATE POLICY content_delete ON {t} FOR DELETE USING ({T} OR {P})")

    # tenants: own tenant, tenants the user belongs to (for the tenant switcher), or platform.
    _enable("tenants")
    op.execute(
        f"""CREATE POLICY tenant_access ON tenants
            USING (id = app_current_tenant() OR {P}
                   OR id IN (SELECT m.tenant_id FROM memberships m WHERE m.user_id = app_current_user()))
            WITH CHECK (id = app_current_tenant() OR {P})"""
    )

    # memberships: own tenant, own memberships, or platform.
    _enable("memberships")
    op.execute(
        f"CREATE POLICY membership_access ON memberships USING ({T} OR user_id = app_current_user() OR {P}) "
        f"WITH CHECK ({T} OR {P})"
    )

    # roles & role_permissions: system roles are global; custom roles belong to a tenant.
    for t in ("roles", "role_permissions"):
        _enable(t)
    op.execute(
        f"""CREATE POLICY role_read ON roles FOR SELECT
            USING (tenant_id IS NULL OR {T} OR {P}
                   OR id IN (SELECT m.role_id FROM memberships m WHERE m.user_id = app_current_user()))"""
    )
    op.execute(f"CREATE POLICY role_write ON roles FOR INSERT WITH CHECK ({T})")
    op.execute(f"CREATE POLICY role_update ON roles FOR UPDATE USING ({T}) WITH CHECK ({T})")
    op.execute(f"CREATE POLICY role_delete ON roles FOR DELETE USING ({T})")
    op.execute(
        f"""CREATE POLICY role_perm_read ON role_permissions FOR SELECT
            USING (tenant_id IS NULL OR {T} OR {P}
                   OR role_id IN (SELECT m.role_id FROM memberships m WHERE m.user_id = app_current_user()))"""
    )
    op.execute(f"CREATE POLICY role_perm_write ON role_permissions FOR INSERT WITH CHECK ({T})")
    op.execute(f"CREATE POLICY role_perm_delete ON role_permissions FOR DELETE USING ({T})")

    # audit_events: append-only; tenant rows for the tenant, platform rows (tenant_id NULL) for platform.
    _enable("audit_events")
    op.execute(f"CREATE POLICY audit_read ON audit_events FOR SELECT USING ({T} OR {P})")
    op.execute(f"CREATE POLICY audit_insert ON audit_events FOR INSERT WITH CHECK ({T} OR (tenant_id IS NULL AND {P}))")

    # Lookups before the tenant is known.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app_invitation_tenant(p_token_hash text) RETURNS uuid
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS
        $$ SELECT tenant_id FROM invitations WHERE token_hash = p_token_hash $$;

        CREATE OR REPLACE FUNCTION app_api_key_lookup(p_prefix text)
        RETURNS TABLE (id uuid, tenant_id uuid, key_hash text, permissions jsonb, created_by uuid,
                       expires_at timestamptz, revoked_at timestamptz)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS
        $$ SELECT id, tenant_id, key_hash, permissions, created_by, expires_at, revoked_at
           FROM api_keys WHERE prefix = p_prefix $$;

        CREATE OR REPLACE FUNCTION app_active_tenant_ids() RETURNS SETOF uuid
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS
        $$ SELECT id FROM tenants WHERE status IN ('trial','active') $$;

        CREATE OR REPLACE FUNCTION app_slug_taken(p_slug text) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS
        $$ SELECT EXISTS (SELECT 1 FROM tenants WHERE slug = p_slug) $$;

        REVOKE ALL ON FUNCTION app_slug_taken(text) FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION app_slug_taken(text) TO complymate_app;
        REVOKE ALL ON FUNCTION app_invitation_tenant(text) FROM PUBLIC;
        REVOKE ALL ON FUNCTION app_api_key_lookup(text) FROM PUBLIC;
        REVOKE ALL ON FUNCTION app_active_tenant_ids() FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION app_invitation_tenant(text), app_api_key_lookup(text), app_active_tenant_ids()
            TO complymate_app;
        """
    )


def downgrade() -> None:
    for t in (
        STRICT
        + TENANT_OR_PLATFORM
        + TENANT_ONLY
        + SHARED_CONTENT
        + ["tenants", "memberships", "roles", "role_permissions", "audit_events"]
    ):
        op.execute(f"ALTER TABLE {t} DISABLE ROW LEVEL SECURITY")
    op.execute(
        "DROP FUNCTION IF EXISTS app_invitation_tenant(text), app_api_key_lookup(text), app_active_tenant_ids(), "
        "app_slug_taken(text)"
    )
