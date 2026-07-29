CREATE TABLE IF NOT EXISTS conversation_logs (
    id              BIGSERIAL PRIMARY KEY,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_question   TEXT NOT NULL,
    agent_answer    TEXT NOT NULL,
    latency_ms      INTEGER,
    used_citations  JSONB
);
