"""CLI wrappers for console scripts defined in pyproject.toml."""

from __future__ import annotations

import os
import subprocess
import sys

from app.env_paths import ROOT


def streamlit_main() -> None:
    """Launch the Streamlit chat UI (Module 5-1)."""
    # Windows + Anaconda-based venv: OpenBLAS/MKL can deadlock; also avoid
    # Streamlit re-spawning via conda ``_base_executable``.
    env = {
        **os.environ,
        "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false",
        "STREAMLIT_SERVER_FILE_WATCHER_TYPE": "none",
        "PYTHONNOUSERSITE": "1",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "PYTHONEXECUTABLE": sys.executable,
    }
    raise SystemExit(
        subprocess.call(
            [sys.executable, str(ROOT / "scripts" / "run_streamlit.py")],
            cwd=str(ROOT),
            env=env,
        )
    )
