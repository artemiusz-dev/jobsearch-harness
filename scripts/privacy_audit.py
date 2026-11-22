#!/usr/bin/env python3
"""Privacy audit for this repository (run before every push; CI runs it too).

Generic checks, no private terms inside this file. It audits what is staged or committed (the git
index), not unstaged working-tree edits:
  - forbidden file types tracked (office files, archives, env files, caches) outside tests/fixtures/
  - email addresses other than documented placeholders; phone-number-like strings; absolute home paths
  - inside tracked Office documents (docx/xlsx/pptx): their XML text and the author fields in docProps
  - commit authors/committers that are not noreply addresses
  - OPTIONAL: your private denylist (one regex per line; blank lines and # comments ignored), via
    --denylist FILE or $JOBSEARCH_DENYLIST, checked in file names, file contents (including Office
    document XML) and the full git history. The denylist file must live OUTSIDE the repository and is
    never committed.

Usage: python3 scripts/privacy_audit.py [--denylist FILE] [--repo DIR]
Exit code 1 on any finding or error.
"""
from __future__ import annotations

import argparse
import io
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

FORBIDDEN_EXT = {".docx", ".doc", ".pdf", ".xlsx", ".xls", ".pptx", ".zip", ".skill", ".pyc", ".pem", ".key", ".p12"}
FORBIDDEN_NAMES = {".DS_Store", ".env"}
OFFICE_EXT = {".docx", ".xlsx", ".pptx"}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
ALLOWED_EMAIL_ADDRESSES = {"noreply@github.com"}          # the address GitHub itself commits as
ALLOWED_EMAIL_DOMAINS = {"example.com", "example.org", "example.invalid", "evil.com", "users.noreply.github.com"}
PHONE = re.compile(
    r"(?<![\w.])(?:(?:\+|00)[0-9]{1,3}[ -]?[0-9]{2,3}[ -]?[0-9]{3}[ -]?[0-9]{2,4}"       # international
    r"|\(?[0-9]{3}\)?[ .-][0-9]{3}[ .-][0-9]{4})(?![\w.])")                              # national, 3-3-4
HOME_PATH = re.compile(r"(/Us" r"ers/[A-Za-z0-9._-]+|/ho" r"me/[A-Za-z0-9._-]+|[A-Za-z]:\\Us" r"ers\\)")
ALLOWED_DOC_AUTHORS = {"", "Example Author", "python-docx", "openpyxl", "python-pptx"}
DOC_AUTHOR_FIELDS = re.compile(r"<(?:dc:creator|cp:lastModifiedBy)>([^<]*)</(?:dc:creator|cp:lastModifiedBy)>")
ALLOWED_IDENTITY_SUFFIX = "@users.noreply.github.com"
ALLOWED_IDENTITIES = {"noreply@github.com"}           # commits GitHub itself creates (web merges, PR merge refs)
SKIP_CONTENT = {"scripts/privacy_audit.py"}           # this file defines the patterns


class AuditError(Exception):
    pass


def git(repo: Path, *args: str, binary: bool = False):
    try:
        r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True)
    except FileNotFoundError:
        raise AuditError("git is not installed") from None
    except subprocess.CalledProcessError as exc:
        raise AuditError(f"git {' '.join(args[:2])} failed: {exc.stderr.decode('utf-8', 'replace').strip()}") from None
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")


def load_denylist(path: Path | None):
    if not path:
        return None
    patterns = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    if not patterns:
        return None
    try:
        return re.compile("|".join(f"(?:{p})" for p in patterns), re.IGNORECASE)
    except re.error as exc:
        raise AuditError(f"invalid regular expression in the denylist ({exc})") from None


def scan_text(label: str, text: str, deny, problems: list[str], generic: bool = True):
    for n, line in enumerate(text.splitlines(), 1):
        if generic:
            for m in EMAIL.finditer(line):
                if m.group(1).lower() not in ALLOWED_EMAIL_DOMAINS and m.group(0).lower() not in ALLOWED_EMAIL_ADDRESSES:
                    problems.append(f"{label}:{n}: non-placeholder email domain '{m.group(1)}'")
            if PHONE.search(line):
                problems.append(f"{label}:{n}: phone-like number")
            if HOME_PATH.search(line):
                problems.append(f"{label}:{n}: absolute home path")
        if deny and deny.search(line):
            problems.append(f"{label}:{n}: private term (denylist)")


def scan_office(label: str, blob: bytes, deny, problems: list[str]):
    try:
        zf = zipfile.ZipFile(io.BytesIO(blob))
    except zipfile.BadZipFile:
        problems.append(f"{label}: not a valid Office archive (cannot be inspected)")
        return
    for info in zf.infolist():
        if not info.filename.lower().endswith((".xml", ".rels")):
            continue
        xml = zf.read(info).decode("utf-8", "replace")
        part = f"{label}!{info.filename}"
        if info.filename == "docProps/core.xml":
            for author in DOC_AUTHOR_FIELDS.findall(xml):
                if author not in ALLOWED_DOC_AUTHORS:
                    problems.append(f"{part}: document author/last-modified-by field is not a placeholder ('{author}')")
        # tags are noise for line-based scanning: scan the text between them
        scan_text(part, re.sub(r"<[^>]+>", "\n", xml), deny, problems)


def audit(repo: Path, denylist: Path | None) -> list[str]:
    problems: list[str] = []
    deny = load_denylist(denylist)
    files = [f for f in git(repo, "ls-files").splitlines() if f]

    for f in files:
        p = Path(f)
        in_fixtures = f.startswith("tests/fixtures/")
        if not in_fixtures and (p.suffix.lower() in FORBIDDEN_EXT or p.name in FORBIDDEN_NAMES or p.name.startswith(".env")):
            problems.append(f"forbidden file type tracked: {f}")
        if deny and deny.search(f):
            problems.append(f"private term in file name: {f}")
        blob = git(repo, "show", f":{f}", binary=True)          # the staged/committed content
        if p.suffix.lower() in OFFICE_EXT:
            scan_office(f, blob, deny, problems)
            continue
        try:
            text = blob.decode("utf-8")
        except UnicodeDecodeError:
            text = blob.decode("latin-1")                        # other binaries: best-effort byte scan
        scan_text(f, text, deny, problems, generic=f not in SKIP_CONTENT)

    try:
        git(repo, "rev-parse", "--verify", "HEAD")
        has_commits = True
    except AuditError:
        has_commits = False                                      # fresh repository: nothing to check in history yet
    identities = git(repo, "log", "--all", "--format=%an <%ae>|%cn <%ce>").splitlines() if has_commits else []
    for who in sorted(set(identities)):
        for part in who.split("|"):
            m = re.search(r"<([^>]*)>", part)
            email = m.group(1) if m else ""
            if not (email.endswith(ALLOWED_IDENTITY_SUFFIX) or email in ALLOWED_IDENTITIES):
                problems.append(f"commit identity is not a noreply address: {part}")

    if deny and has_commits:
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
    try:
        problems = audit(repo, dl)
    except AuditError as exc:
        print(f"privacy_audit: {exc}", file=sys.stderr)
        return 1
    for p in problems:
        print(p)
    print(f"privacy_audit: {'FAIL' if problems else 'OK'} ({len(problems)} finding(s)); denylist {'used' if dl else 'not used'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
