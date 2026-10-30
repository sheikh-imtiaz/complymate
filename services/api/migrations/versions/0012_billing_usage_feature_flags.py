"""Plans, subscriptions, usage counters, feature flags, impersonation, report jobs, exports, Stripe events.

Revision ID: 0012
"""

import json

from alembic import op

from complymate.domain.billing.plans import PLANS

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE plans (
            code varchar(20) PRIMARY KEY,
            name varchar(60) NOT NULL,
            price_cents integer NOT NULL,
            currency varchar(3) NOT NULL DEFAULT 'aud',
            max_users integer NOT NULL,
            limits jsonb NOT NULL DEFAULT '{}',
            stripe_price_id varchar(100)
        );

        CREATE TABLE subscriptions (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL UNIQUE REFERENCES tenants(id) ON DELETE CASCADE,
            plan_code varchar(20) NOT NULL REFERENCES plans(code),
            status varchar(20) NOT NULL DEFAULT 'trialing',
            stripe_customer_id varchar(100),
            stripe_subscription_id varchar(100),
            seats integer NOT NULL DEFAULT 1,
            trial_ends_at timestamptz,
            current_period_end timestamptz,
            onboarding_paid boolean NOT NULL DEFAULT false,
            updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_subscriptions_customer ON subscriptions (stripe_customer_id);

        CREATE TABLE usage_counters (
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            period varchar(7) NOT NULL,
            metric varchar(40) NOT NULL,
            value bigint NOT NULL DEFAULT 0,
            PRIMARY KEY (tenant_id, period, metric)
        );

        CREATE TABLE feature_flags (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            key varchar(60) NOT NULL,
            tenant_id uuid REFERENCES tenants(id) ON DELETE CASCADE,
            enabled boolean NOT NULL DEFAULT false,
            updated_by uuid,
            updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE UNIQUE INDEX uq_feature_flags_key_tenant
            ON feature_flags (key, coalesce(tenant_id, '00000000-0000-0000-0000-000000000000'::uuid));

        CREATE TABLE impersonation_sessions (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            support_user_id uuid NOT NULL,
            reason text NOT NULL,
            duration_minutes integer NOT NULL,
            consented_by uuid,
            consented_at timestamptz,
            expires_at timestamptz,
            ended_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_impersonation_tenant ON impersonation_sessions (tenant_id);

        CREATE TABLE report_jobs (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            report_type varchar(40) NOT NULL,
            params jsonb NOT NULL DEFAULT '{}',
            format varchar(10) NOT NULL DEFAULT 'csv',
            status varchar(20) NOT NULL DEFAULT 'queued',
            requested_by uuid,
            schedule_cron varchar(60),
            recipients jsonb NOT NULL DEFAULT '[]',
            export_id uuid,
            error text,
            completed_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_report_jobs_tenant ON report_jobs (tenant_id, created_at);

        CREATE TABLE exports (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            kind varchar(40) NOT NULL,
            storage_key text NOT NULL,
            filename varchar(255) NOT NULL,
            content_type varchar(100) NOT NULL,
            size_bytes bigint NOT NULL,
            created_by uuid,
            expires_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_exports_tenant ON exports (tenant_id, created_at);

        CREATE TABLE stripe_events (
            id varchar(100) PRIMARY KEY,
            type varchar(100) NOT NULL,
            processed_at timestamptz NOT NULL DEFAULT now(),
            payload_summary text
        );
        """
    )
    for plan in PLANS.values():
        op.execute(
            f"INSERT INTO plans (code, name, price_cents, max_users, limits) VALUES "
            f"('{plan.code}', '{plan.name}', {plan.price_cents}, {plan.max_users}, '{json.dumps(plan.limits)}')"
        )


def downgrade() -> None:
    op.execute(
        "DROP TABLE IF EXISTS stripe_events, exports, report_jobs, impersonation_sessions, feature_flags, "
        "usage_counters, subscriptions, plans CASCADE"
    )
