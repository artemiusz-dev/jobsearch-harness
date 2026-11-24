#!/usr/bin/env python3
"""One-command developer setup for a clone of this repository (standard library only).

    python3 scripts/dev_setup.py            # venv + dependencies (incl. ruff) + git hooks
    python3 scripts/dev_setup.py --check    # report the state, change nothing
    python3 scripts/dev_setup.py --no-venv  # only enable the git hooks

Creates .venv (if missing), installs requirements-dev.txt into it, makes the hooks in .githooks
executable and sets `core.hooksPath` for THIS clone only (never the global git config).
Hooks: pre-commit (privacy audit, noreply author, ruff on staged files), commit-msg (privacy and subject
checks), pre-push (ruff, pytest, full privacy audit).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV = ROOT / ".venv"
HOOKS = ROOT / ".githooks"


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def git_config(*args: str) -> str:
    r = subprocess.run(["git", "-C", str(ROOT), "config", *args], capture_output=True, text=True)
    return r.stdout.strip()


def state() -> dict:
    py = venv_python()
    has_ruff = (py.parent / ("ruff.exe" if os.name == "nt" else "ruff")).exists()
    return {
        "venv": py.exists(),
        "ruff": has_ruff,
        "hooks_path": git_config("--local", "core.hooksPath") == ".githooks",
        "hooks_executable": all(os.access(h, os.X_OK) for h in HOOKS.iterdir() if h.is_file()),
    }


def report(s: dict) -> int:
    for k, v in s.items():
        print(f"  {'ok     ' if v else 'MISSING'} {k}")
    return 0 if all(s.values()) else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="report the state and exit 1 if anything is missing")
    ap.add_argument("--no-venv", action="store_true", help="skip the virtual environment, only enable the hooks")
    a = ap.parse_args(argv)
    if a.check:
        return report(state())
    if not (ROOT / ".git").exists():
        print("dev_setup: not a git clone (no .git); nothing to hook.", file=sys.stderr)
        return 1
    if not a.no_venv:
        if not venv_python().exists():
            print(f"Creating {VENV} ...")
            subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
        print("Installing requirements-dev.txt ...")
        subprocess.run([str(venv_python()), "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
                        "-r", str(ROOT / "requirements-dev.txt")], check=True)
    for h in HOOKS.iterdir():
        if h.is_file():
            h.chmod(h.stat().st_mode | 0o111)
    subprocess.run(["git", "-C", str(ROOT), "config", "--local", "core.hooksPath", ".githooks"], check=True)
    print("Git hooks enabled for this clone (core.hooksPath = .githooks). State:")
    return report(state())


if __name__ == "__main__":
    sys.exit(main())
