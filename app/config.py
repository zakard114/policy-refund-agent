"""Project paths and environment loading."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from app.env_paths import ROOT, SHARED_LLM_ENV

DATA_DIR = ROOT / "data"
POLICY_PATH = DATA_DIR / "refund_policy.md"
EVAL_PATH = DATA_DIR / "eval_data.json"

_ENV_LOADED = False


def load_app_env() -> None:
    """Load `.env` then optional shared LLM env (without overriding local values).

    On Streamlit Community Cloud, secrets are copied into ``os.environ`` first
    by ``streamlit_app._apply_streamlit_secrets`` (dotenv must not wipe them).
    """
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    _ENV_LOADED = True

    load_dotenv(ROOT / ".env")
    if SHARED_LLM_ENV.is_file():
        load_dotenv(SHARED_LLM_ENV, override=False)

    # Stale shell exports (common when Streamlit is launched from an old terminal)
    # otherwise win over project `.env` because python-dotenv does not override by default.
    # Grafana reads pra-postgres :5435 — logging must use the same DSN.
    from dotenv import dotenv_values

    project_env = dotenv_values(ROOT / ".env")
    for key in (
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_SSLMODE",
    ):
        if project_env.get(key):
            os.environ[key] = project_env[key]

    backend = (
        os.getenv("PRA_LLM_BACKEND")
        or os.getenv("DTC_LLM_BACKEND")
        or os.getenv("EVAL_LLM_BACKEND")
        or "cerebras"
    ).lower()

    if backend == "cerebras":
        if key := os.getenv("CEREBRAS_API_KEY"):
            os.environ["OPENAI_API_KEY"] = key
        if url := os.getenv("CEREBRAS_BASE_URL"):
            os.environ["OPENAI_BASE_URL"] = url
        if model := os.getenv("CEREBRAS_MODEL"):
            os.environ["LLM_MODEL"] = model
    elif backend == "ollama":
        if key := os.getenv("OLLAMA_API_KEY"):
            os.environ["OPENAI_API_KEY"] = key
        if url := os.getenv("OLLAMA_BASE_URL"):
            os.environ["OPENAI_BASE_URL"] = url
        if model := os.getenv("OLLAMA_MODEL"):
            os.environ["LLM_MODEL"] = model
    elif backend == "openai":
        if key := os.getenv("OPENAI_API_KEY"):
            os.environ["OPENAI_API_KEY"] = key
        if model := os.getenv("OPENAI_MODEL"):
            os.environ["LLM_MODEL"] = model


def get_model_name() -> str:
    load_app_env()
    return os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL") or "gemma-4-31b"


def search_boost() -> dict[str, float]:
    """minsearch field boosts (overridable via env)."""
    load_app_env()
    return {
        "section": float(os.getenv("PRA_SEARCH_SECTION_BOOST", "4.0")),
        "keywords": float(os.getenv("PRA_SEARCH_KEYWORDS_BOOST", "2.5")),
        "text": float(os.getenv("PRA_SEARCH_TEXT_BOOST", "0.8")),
    }


def retrieval_method() -> str:
    """App retrieval: hybrid (RRF) | keyword | vector. Default hybrid after M2-4."""
    load_app_env()
    return (os.getenv("PRA_RETRIEVAL_METHOD") or "hybrid").lower().strip()
