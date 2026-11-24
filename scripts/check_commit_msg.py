#!/usr/bin/env python3
"""commit-msg hook helper: keeps personal data out of commit messages and the subject line tidy.

Usage (from .githooks/commit-msg):  python3 scripts/check_commit_msg.py <message-file> [--denylist FILE]

Hard failures (exit 1):
  - empty message, or a subject longer than 72 characters
  - the message text contains a non-placeholder email, a phone-like number, an absolute home path
    (same patterns as scripts/privacy_audit.py), or a term from your private denylist
    (--denylist, $JOBSEARCH_DENYLIST, or ~/.config/jobsearch-private/denylist.txt when it exists)
Soft notes (printed, exit 0): subject is not in the `type(scope): subject` form, or ends with a period.
Merge, Revert, fixup! and squash! subjects skip the style rules but not the privacy rules.
Trailer lines (Co-Authored-By, Signed-off-by) are checked against the denylist only.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import privacy_audit as pa  # noqa: E402

MAX_SUBJECT = 72
CONVENTIONAL = re.compile(r"^(feat|fix|docs|test|tests|chore|refactor|perf|build|ci|style|revert)(\([\w./-]+\))?!?: \S")
SKIP_STYLE = re.compile(r"^(Merge |Revert |fixup! |squash! )")
TRAILER = re.compile(r"^(Co-Authored-By|Signed-off-by|Reviewed-by|Acked-by):", re.I)


def default_denylist() -> Path | None:
    env = os.environ.get("JOBSEARCH_DENYLIST")
    if env:
        return Path(env).expanduser()
    p = Path.home() / ".config" / "jobsearch-private" / "denylist.txt"
    return p if p.is_file() else None


def check(message: str, denylist: Path | None = None) -> tuple[list[str], list[str]]:
    lines = [ln for ln in message.splitlines() if not ln.startswith("#")]      # git's own comment lines
    text = "\n".join(lines).strip()
    problems: list[str] = []
    notes: list[str] = []
    if not text:
        return ["empty commit message"], notes
    subject = next(ln for ln in lines if ln.strip()).strip()
    if len(subject) > MAX_SUBJECT:
        problems.append(f"subject is {len(subject)} characters (max {MAX_SUBJECT})")
    if not SKIP_STYLE.match(subject):
        if not CONVENTIONAL.match(subject):
            notes.append("subject is not in the 'type(scope): subject' form (feat, fix, docs, test, chore, refactor ...)")
        if subject.endswith("."):
            notes.append("subject ends with a period")
    try:
        deny = pa.load_denylist(denylist)
    except (pa.AuditError, OSError) as exc:
        return [f"cannot read the denylist: {exc}"], notes
    body = [ln for ln in lines if not TRAILER.match(ln)]
    trailers = [ln for ln in lines if TRAILER.match(ln)]
    pa.scan_text("commit message", "\n".join(body), deny, problems)
    pa.scan_text("commit trailer", "\n".join(trailers), deny, problems, generic=False)
    return problems, notes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("message_file")
    ap.add_argument("--denylist")
    a = ap.parse_args(argv)
    try:
        message = Path(a.message_file).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"commit-msg: cannot read {a.message_file}: {exc}", file=sys.stderr)
        return 1
    problems, notes = check(message, Path(a.denylist).expanduser() if a.denylist else default_denylist())
    for n in notes:
        print(f"commit-msg: note: {n}", file=sys.stderr)
    for p in problems:
        print(f"commit-msg: {p}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
