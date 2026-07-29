"""Launch Streamlit without conda base_executable re-spawn issues."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"


def _force_venv_interpreter() -> None:
    """If Anaconda re-spawned us, immediately hop back into the project venv."""
    log = ROOT / ".cache" / "streamlit_launch.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    exe = Path(sys.executable).resolve()
    venv = VENV_PY.resolve()
    with log.open("a", encoding="utf-8") as fh:
        fh.write(f"pid={os.getpid()} exe={exe} venv={venv}\n")
    if not venv.is_file():
        return
    if exe == venv:
        return
    if "anaconda" in str(exe).lower() or "miniconda" in str(exe).lower():
        with log.open("a", encoding="utf-8") as fh:
            fh.write(f"hop -> {venv}\n")
        os.environ["PYTHONEXECUTABLE"] = str(venv)
        os.execv(str(venv), [str(venv), "-u", str(Path(__file__).resolve()), *sys.argv[1:]])


_force_venv_interpreter()

# Before any numpy/pyarrow import.
for key, val in (
    ("OMP_NUM_THREADS", "1"),
    ("OPENBLAS_NUM_THREADS", "1"),
    ("MKL_NUM_THREADS", "1"),
    ("NUMEXPR_NUM_THREADS", "1"),
    ("PYTHONNOUSERSITE", "1"),
    ("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false"),
    ("STREAMLIT_SERVER_FILE_WATCHER_TYPE", "none"),
):
    os.environ[key] = val

sys._base_executable = sys.executable  # type: ignore[attr-defined]
os.environ["PYTHONEXECUTABLE"] = sys.executable

try:
    import multiprocessing as _mp

    _mp.set_executable(sys.executable)
except Exception:
    pass

os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from streamlit.web import cli as stcli


def main() -> None:
    sys.argv = [
        "streamlit",
        "run",
        "streamlit_app.py",
        "--server.headless",
        "true",
        "--server.port",
        "8502",
        "--server.enableCORS",
        "false",
        "--server.enableXsrfProtection",
        "false",
    ]
    raise SystemExit(stcli.main())


if __name__ == "__main__":
    main()
