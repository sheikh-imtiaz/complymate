"""Rule library (pgvector), chat sessions/messages, AI feedback, LLM call log.

Revision ID: 0011
"""

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE kb_sources (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            jurisdiction varchar(2) NOT NULL,
            title varchar(300) NOT NULL,
            url text,
            publisher varchar(100) NOT NULL,
            doc_type varchar(40) NOT NULL DEFAULT 'guidance',
            storage_key text,
            content_hash varchar(64),
            last_checked_at timestamptz,
            indexed_at timestamptz,
            status varchar(20) NOT NULL DEFAULT 'active',
            chunk_count integer NOT NULL DEFAULT 0,
            created_at timestamptz NOT NULL DEFAULT now()
        );

        CREATE TABLE kb_chunks (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            source_id uuid NOT NULL REFERENCES kb_sources(id) ON DELETE CASCADE,
            chunk_index integer NOT NULL,
            heading text,
            content text NOT NULL,
            tokens integer NOT NULL DEFAULT 0,
            embedding vector(1024) NOT NULL,
            metadata jsonb NOT NULL DEFAULT '{}'
        );
        CREATE INDEX ix_kb_chunks_source ON kb_chunks (source_id);
        CREATE INDEX ix_kb_chunks_embedding ON kb_chunks USING hnsw (embedding vector_cosine_ops);
        CREATE INDEX ix_kb_chunks_fts ON kb_chunks USING gin (to_tsvector('english', content));

        CREATE TABLE chat_sessions (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            user_id uuid NOT NULL,
            title varchar(200) NOT NULL DEFAULT 'New conversation',
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_chat_sessions_user ON chat_sessions (tenant_id, user_id);

        CREATE TABLE chat_messages (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            session_id uuid NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
            role varchar(20) NOT NULL,
            content text NOT NULL,
            citations jsonb NOT NULL DEFAULT '[]',
            model varchar(120),
            prompt_version varchar(40),
            tool_calls jsonb NOT NULL DEFAULT '[]',
            input_tokens integer NOT NULL DEFAULT 0,
            output_tokens integer NOT NULL DEFAULT 0,
            cost_usd numeric(10,5) NOT NULL DEFAULT 0,
            guardrail_action varchar(40),
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_chat_messages_session ON chat_messages (session_id, created_at);

        CREATE TABLE ai_feedback (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            message_id uuid NOT NULL REFERENCES chat_messages(id) ON DELETE CASCADE,
            user_id uuid NOT NULL,
            rating varchar(20) NOT NULL CHECK (rating IN ('helpful','wrong')),
            comment text,
            review_status varchar(20) NOT NULL DEFAULT 'open',
            reviewed_by uuid,
            resolution text,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_ai_feedback_status ON ai_feedback (review_status, rating);

        CREATE TABLE llm_calls (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid,
            purpose varchar(40) NOT NULL,
            model varchar(120) NOT NULL,
            prompt_version varchar(40),
            input_tokens integer NOT NULL DEFAULT 0,
            output_tokens integer NOT NULL DEFAULT 0,
            cost_usd numeric(10,5) NOT NULL DEFAULT 0,
            latency_ms integer NOT NULL DEFAULT 0,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_llm_calls_tenant_time ON llm_calls (tenant_id, created_at);
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TABLE IF EXISTS llm_calls, ai_feedback, chat_messages, chat_sessions, kb_chunks, kb_sources CASCADE"
    )
