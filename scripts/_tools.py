"""Locate external programs the scripts need (standard library only)."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

SOFFICE_CANDIDATES = (
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",       # macOS app bundle (brew --cask does not always link it)
    "/opt/homebrew/bin/soffice",
    "/usr/local/bin/soffice",
    "/usr/bin/soffice",
    "/snap/bin/libreoffice",
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
)


def find_soffice() -> str | None:
    """Path to LibreOffice's soffice: $SOFFICE, then PATH, then the usual install locations."""
    env = os.environ.get("SOFFICE")
    if env and Path(env).exists():
        return env
    found = shutil.which("soffice")
    if found:
        return found
    for c in SOFFICE_CANDIDATES:
        if Path(c).exists():
            return c
    return None
