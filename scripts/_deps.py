"""Make the third-party dependencies importable, whichever Python started the script.

Skills and the workspace rules call plain `python3 <plugin>/scripts/...`. The system Python rarely has
PyYAML, openpyxl, python-docx, jsonschema and pypdf, so every entry script calls `ensure()` before its
third-party imports. If something is missing, `ensure()` creates a private virtual environment once
(`$CLAUDE_PLUGIN_DATA/venv`, else `~/.cache/jobsearch-harness/venv`), installs requirements.txt into it
and re-runs the same command inside it. Nothing is installed into the system Python or the plugin folder.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

REQUIREMENTS = Path(__file__).resolve().parent.parent / "requirements.txt"
MODULES = ("yaml", "jsonschema", "openpyxl", "docx", "pypdf")
GUARD = "JOBSEARCH_DEPS_BOOTSTRAPPED"


def missing() -> list[str]:
    return [m for m in MODULES if importlib.util.find_spec(m) is None]


def venv_dir() -> Path:
    base = os.environ.get("CLAUDE_PLUGIN_DATA")
    root = Path(base) if base else Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "jobsearch-harness"
    return root / "venv"


def _venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _build_venv(venv: Path) -> Path:
    py = _venv_python(venv)
    if py.exists():
        return py
    print(f"jobsearch-harness: installing dependencies into {venv} (first run only)...", file=sys.stderr)
    try:
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True, stdout=subprocess.DEVNULL)
        subprocess.run([str(py), "-m", "pip", "install", "--quiet", "--disable-pip-version-check", "-r", str(REQUIREMENTS)], check=True)
    except (subprocess.CalledProcessError, OSError) as e:
        raise SystemExit(
            f"Could not set up dependencies automatically ({e}).\n"
            f"Install them manually: {sys.executable} -m pip install -r {REQUIREMENTS}"
        ) from e
    return py


def ensure() -> None:
    """No-op when everything imports; otherwise re-exec the current command inside the private venv."""
    gone = missing()
    if not gone:
        return
    if os.environ.get(GUARD):
        raise SystemExit(
            f"Missing Python packages {gone} even inside {venv_dir()}. "
            f"Delete that folder and run again, or install {REQUIREMENTS} manually."
        )
    py = _build_venv(venv_dir())
    os.environ[GUARD] = "1"
    os.execv(str(py), [str(py), *sys.argv])
