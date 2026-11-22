#!/usr/bin/env python3
"""Privacy audit for this repository (run before every push; CI runs it too).

Generic checks, no private terms inside this file:
  - forbidden file types tracked (office files, archives, env files, caches) outside tests/fixtures/
  - email addresses other than documented placeholders
  - phone-number-like strings and absolute home-directory paths
  - commit authors/committers that are not noreply addresses
  - OPTIONAL: your private denylist (one regex per line), via --denylist FILE or $JOBSEARCH_DENYLIST,
    checked in file names, file contents and the full git history. The denylist file itself must live
    OUTSIDE the repository and is never committed.

Usage: python3 scripts/privacy_audit.py [--denylist FILE] [--repo DIR]
Exit code 1 on any finding.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

FORBIDDEN_EXT = {".docx", ".doc", ".pdf", ".xlsx", ".xls", ".zip", ".skill", ".pyc", ".pem", ".key", ".p12"}
FORBIDDEN_NAMES = {".DS_Store", ".env"}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
ALLOWED_EMAIL_DOMAINS = {"example.com", "example.org", "example.invalid", "evil.com", "users.noreply.github.com"}
PHONE = re.compile(r"(?<![\w.])(\+|00)[0-9]{1,3}[ -]?[0-9]{2,3}[ -]?[0-9]{3}[ -]?[0-9]{2,4}(?![\w.])")
HOME_PATH = re.compile(r"(/Us" r"ers/[A-Za-z0-9._-]+|/ho" r"me/[A-Za-z0-9._-]+|[A-Za-z]:\\Us" r"ers\\)")
SKIP_CONTENT = {"scripts/privacy_audit.py"}   # this file defines the patterns


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout


def audit(repo: Path, denylist: Path | None) -> list[str]:
    problems: list[str] = []
    files = [f for f in git(repo, "ls-files").splitlines() if f]
    deny = None
    if denylist:
        patterns = [ln.strip() for ln in denylist.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]
        deny = re.compile("|".join(f"(?:{p})" for p in patterns), re.IGNORECASE) if patterns else None

    for f in files:
        p = Path(f)
        if not f.startswith("tests/fixtures/") and (p.suffix.lower() in FORBIDDEN_EXT or p.name in FORBIDDEN_NAMES or p.name.startswith(".env")):
            problems.append(f"forbidden file type tracked: {f}")
        if deny and deny.search(f):
            problems.append(f"private term in file name: {f}")
        full = repo / f
        try:
            text = full.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if f not in SKIP_CONTENT:
                for m in EMAIL.finditer(line):
                    if m.group(1).lower() not in ALLOWED_EMAIL_DOMAINS:
                        problems.append(f"{f}:{n}: non-placeholder email domain '{m.group(1)}'")
                if PHONE.search(line):
                    problems.append(f"{f}:{n}: phone-like number")
                if HOME_PATH.search(line):
                    problems.append(f"{f}:{n}: absolute home path")
            if deny and deny.search(line):
                problems.append(f"{f}:{n}: private term (denylist)")

    ident = git(repo, "log", "--all", "--format=%an <%ae>|%cn <%ce>").splitlines()
    for who in sorted(set(ident)):
        for part in who.split("|"):
            m = re.search(r"<([^>]*)>", part)
            if not m or not m.group(1).endswith("@users.noreply.github.com"):
                problems.append(f"commit identity is not a noreply address: {part}")

    if deny:
        hist = git(repo, "log", "--all", "-p", "--format=%an %ae %cn %ce%n%B")
        for n, line in enumerate(hist.splitlines(), 1):
            if deny.search(line):
                problems.append(f"private term in git history (output line {n})")
                break
    return sorted(set(problems))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--denylist", default=os.environ.get("JOBSEARCH_DENYLIST"))
    a = ap.parse_args()
    dl = Path(a.denylist).expanduser() if a.denylist else None
    if dl and not dl.exists():
        print(f"denylist not found: {dl}", file=sys.stderr)
        return 1
    repo = Path(a.repo)
    if dl and repo.resolve() in dl.resolve().parents:
        print("refusing to use a denylist stored inside the repository", file=sys.stderr)
        return 1
    problems = audit(repo, dl)
    for p in problems:
        print(p)
    print(f"privacy_audit: {'FAIL' if problems else 'OK'} ({len(problems)} finding(s)); denylist {'used' if dl else 'not used'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
