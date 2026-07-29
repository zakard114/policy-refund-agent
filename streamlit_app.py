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
    """Map Streamlit Cloud secrets → env vars before app.config loads."""
    try:
        import streamlit as st

        secrets = getattr(st, "secrets", None)
        if secrets is None:
            return
        for key in secrets:
            value = secrets[key]
            if isinstance(value, dict):
                continue
            os.environ.setdefault(str(key), str(value))
    except Exception:  # noqa: BLE001 — local/dev without secrets.toml is fine
        return


_apply_streamlit_secrets()

from app.streamlit_ui import main

main()
