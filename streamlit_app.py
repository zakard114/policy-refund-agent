"""Streamlit entry point — lives at repo root (Streamlit adds this dir to sys.path).

Run:
    uv run --no-sync pra-streamlit
    uv run --no-sync streamlit run streamlit_app.py
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

from app.streamlit_ui import main

main()
