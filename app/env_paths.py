"""E: paths and shared workspace discovery (Projects/llm/<repo> layout)."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def find_workspace_root(start: Path = ROOT) -> Path:
    """Walk up until ZoomCamp/LLM exists (E:\\IT_SPACES\\AI).

    Falls back to ``ROOT`` when running outside the full workspace layout
    (e.g. Kestra Process runner with only the project mounted).
    """
    for path in (start, *start.parents):
        if (path / "ZoomCamp" / "LLM").is_dir():
            return path
    return start


WORKSPACE_ROOT = find_workspace_root()
WORKSPACE_CACHE = WORKSPACE_ROOT / ".cache"
SHARED_LLM_ENV = WORKSPACE_ROOT / "ZoomCamp" / "LLM" / ".env"

_APPLIED = False


def apply_e_drive_env() -> None:
    global _APPLIED
    if _APPLIED:
        return
    _APPLIED = True

    project_cache = ROOT / ".cache"
    paths = {
        "hf": project_cache / "huggingface",
        "tmp": project_cache / "tmp",
        "uv": WORKSPACE_CACHE / "uv",
        "pip": WORKSPACE_CACHE / "pip",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)

    defaults = {
        "HF_HOME": str(paths["hf"]),
        "HF_HUB_CACHE": str(paths["hf"] / "hub"),
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "HF_HUB_DISABLE_SYMLINKS_WARNING": "1",
        "UV_CACHE_DIR": str(paths["uv"]),
        "PIP_CACHE_DIR": str(paths["pip"]),
        "TMP": str(paths["tmp"]),
        "TEMP": str(paths["tmp"]),
        "TRANSFORMERS_CACHE": str(paths["hf"] / "transformers"),
        "SENTENCE_TRANSFORMERS_HOME": str(paths["hf"] / "sentence_transformers"),
        "PRA_PROJECT_ROOT": str(ROOT),
    }
    for key, value in defaults.items():
        os.environ.setdefault(key, value)


apply_e_drive_env()
