"""Postgres conversation logging + user feedback for Module 5 monitoring."""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any

from app.config import load_app_env

logger = logging.getLogger(__name__)

_SCHEMA_READY = False
_SCHEMA_LOCK = threading.Lock()
_LAST_ERROR: str | None = None

DDL = """
CREATE TABLE IF NOT EXISTS conversation_logs (
    id              BIGSERIAL PRIMARY KEY,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_question   TEXT NOT NULL,
    agent_answer    TEXT NOT NULL,
    latency_ms      INTEGER,
    used_citations  JSONB,
    feedback        SMALLINT,
    feedback_comment TEXT,
    feedback_at     TIMESTAMPTZ
);
"""

# Existing DBs created before feedback columns.
_MIGRATE = (
    "ALTER TABLE conversation_logs ADD COLUMN IF NOT EXISTS feedback SMALLINT",
    "ALTER TABLE conversation_logs ADD COLUMN IF NOT EXISTS feedback_comment TEXT",
    "ALTER TABLE conversation_logs ADD COLUMN IF NOT EXISTS feedback_at TIMESTAMPTZ",
)


def last_db_error() -> str | None:
    """Most recent logging/connect failure (for UI diagnostics)."""
    return _LAST_ERROR


def _dsn() -> str:
    """Build a libpq URL. Set POSTGRES_SSLMODE=require for Neon/Supabase."""
    from urllib.parse import quote_plus

    load_app_env()
    host = (os.getenv("POSTGRES_HOST") or "localhost").strip()
    # Accidental "host:5432" from Neon PGHOST copy → strip port (we set it separately).
    if host.count(":") == 1 and host.rsplit(":", 1)[-1].isdigit():
        host, port_in_host = host.rsplit(":", 1)
        if not os.getenv("POSTGRES_PORT"):
            os.environ["POSTGRES_PORT"] = port_in_host
    port = (os.getenv("POSTGRES_PORT") or "5435").strip()
    db = (os.getenv("POSTGRES_DB") or "policy_refund_agent").strip()
    user = quote_plus((os.getenv("POSTGRES_USER") or "pra").strip())
    password = quote_plus((os.getenv("POSTGRES_PASSWORD") or "pra").strip())
    sslmode = (os.getenv("POSTGRES_SSLMODE") or "disable").strip() or "disable"
    # Neon connection strings include channel_binding=require; keep it for remote SSL.
    qs = f"sslmode={sslmode}"
    if sslmode in ("require", "verify-ca", "verify-full"):
        qs += "&channel_binding=require"
    return f"postgresql://{user}:{password}@{host}:{port}/{db}?{qs}"


def _connect():
    import psycopg

    load_app_env()
    # Neon free tier scales to zero — cold start often exceeds 5s.
    sslmode = (os.getenv("POSTGRES_SSLMODE") or "disable").strip().lower()
    timeout = 30 if sslmode in ("require", "verify-ca", "verify-full") else 5
    return psycopg.connect(_dsn(), connect_timeout=timeout)


def ensure_schema() -> None:
    """Create conversation_logs + feedback columns if missing (idempotent)."""
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    with _SCHEMA_LOCK:
        if _SCHEMA_READY:
            return
        with _connect() as conn:
            conn.execute(DDL)
            for stmt in _MIGRATE:
                conn.execute(stmt)
            conn.commit()
        _SCHEMA_READY = True


def log_conversation(
    *,
    user_question: str,
    agent_answer: str,
    latency_ms: int | None,
    used_citations: list[dict[str, Any]] | None = None,
    background: bool = False,
) -> int | None:
    """Insert one conversation row. Returns new row id (None if failed / background).

    ``background=True`` fires a daemon thread (UI-only; id not returned).
    Failures are logged, never raised to callers.
    """

    def _write() -> int | None:
        try:
            ensure_schema()
            citations = used_citations or []
            compact = [
                {
                    "id": c.get("id"),
                    "section": c.get("section"),
                }
                for c in citations
            ]
            with _connect() as conn:
                row = conn.execute(
                    """
                    INSERT INTO conversation_logs
                        (created_at, user_question, agent_answer, latency_ms, used_citations)
                    VALUES (%s, %s, %s, %s, %s::jsonb)
                    RETURNING id
                    """,
                    (
                        datetime.now(timezone.utc),
                        user_question,
                        agent_answer,
                        latency_ms,
                        json.dumps(compact, ensure_ascii=False),
                    ),
                ).fetchone()
                conn.commit()
                return int(row[0]) if row else None
        except Exception as exc:  # noqa: BLE001 — monitoring must not break Q&A
            global _LAST_ERROR
            _LAST_ERROR = f"{type(exc).__name__}: {exc}"
            logger.exception("conversation_logs insert failed")
            return None

    if background:
        threading.Thread(target=_write, daemon=True, name="pra-db-log").start()
        return None
    return _write()


def save_feedback(
    *,
    log_id: int,
    feedback: int,
    comment: str | None = None,
) -> bool:
    """
    Store user feedback on an existing conversation row.

    ``feedback``: +1 (helpful) or -1 (not helpful). Returns True on success.
    """
    if feedback not in (1, -1):
        raise ValueError("feedback must be +1 or -1")
    try:
        ensure_schema()
        with _connect() as conn:
            cur = conn.execute(
                """
                UPDATE conversation_logs
                SET feedback = %s,
                    feedback_comment = %s,
                    feedback_at = %s
                WHERE id = %s
                """,
                (
                    feedback,
                    (comment or "").strip() or None,
                    datetime.now(timezone.utc),
                    log_id,
                ),
            )
            conn.commit()
            return cur.rowcount > 0
    except Exception as exc:  # noqa: BLE001
        global _LAST_ERROR
        _LAST_ERROR = f"{type(exc).__name__}: {exc}"
        logger.exception("conversation_logs feedback update failed (id=%s)", log_id)
        return False
