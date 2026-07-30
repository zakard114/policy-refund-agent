"""Streamlit entry point — lives at repo root (Streamlit adds this dir to sys.path).

Run:
    uv run --no-sync pra-streamlit
    uv run --no-sync streamlit run streamlit_app.py

Cloud: Streamlit Community Cloud uses this file as Main file path.
"""

from __future__ import annotations

import os

# Must run before numpy/pyarrow/streamlit import (Windows OpenBLAS deadlock).
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
os.environ.setdefault("STREAMLIT_SERVER_FILE_WATCHER_TYPE", "none")


def _apply_streamlit_secrets() -> None:
    """Map Streamlit Cloud secrets → env vars before app.config loads.

    Postgres keys always override (Cloud Neon must beat any empty/default host).
    Other keys use setdefault so local shell exports still win when intended.
    """
    try:
        import streamlit as st

        secrets = getattr(st, "secrets", None)
        if secrets is None:
            return
        force_keys = {
            "POSTGRES_HOST",
            "POSTGRES_PORT",
            "POSTGRES_DB",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "POSTGRES_SSLMODE",
        }
        for key in secrets:
            value = secrets[key]
            if isinstance(value, dict):
                continue
            name = str(key)
            text = str(value).strip()
            if not text:
                continue
            if name in force_keys:
                os.environ[name] = text
            else:
                os.environ.setdefault(name, text)
    except Exception:  # noqa: BLE001 — local/dev without secrets.toml is fine
        return


_apply_streamlit_secrets()

from app.streamlit_ui import main

main()
