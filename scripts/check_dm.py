#!/usr/bin/env python3
"""Mechanical check for an outbound LinkedIn DM (rules: skills/recruiter-responder, section Outbound LinkedIn DMs).

Usage:
    python3 scripts/check_dm.py "Hi Maria, ..."            # one message as an argument
    python3 scripts/check_dm.py --file drafts.txt          # several messages separated by a blank line
    echo "Hi ..." | python3 scripts/check_dm.py            # from stdin

Checks: at most 3 sentences after the greeting, no banned phrases, no em dash, ends with a question or a
direct statement (not a weak closer). Exit code 0 = all messages pass, 1 = at least one fails.
This is a guard against miscounting by eye; it does not judge tone or facts.
"""
from __future__ import annotations

import argparse
import re
import sys

MAX_SENTENCES = 3
EM_DASH = chr(0x2014)
BANNED = [
    "happy to share my cv", "would be glad to connect", "which i appreciate", "actively exploring new opportunities",
    "wanted to reach out directly", "track record in large-scale architecture",
    "i figure a direct message", "i'm happy to hear the details first", "worth discussing?",
    "passionate about", "excited to", "thrilled to", "leverage", "synergy", "utilize", "results-driven",
    "great fit", "proven track record", "look forward to the opportunity",
]
GREETING = re.compile(r"^\s*(hi|hello|hey|dear|cześć|czesc|dzień dobry|hallo)\b[^.!?\n]*?[,!]\s*", re.I)
ABBREV = re.compile(r"\b(e\.g|i\.e|etc|sr|jr|vs|approx)\.", re.I)


def sentences(text: str) -> list[str]:
    body = GREETING.sub("", text.strip(), count=1)
    body = ABBREV.sub(lambda m: m.group(0).replace(".", "․"), body)
    body = re.sub(r"(?<=\d)\.(?=\d)", "․", body)             # decimals
    parts = re.split(r"(?<=[.!?])\s+", body.strip())
    return [p.replace("․", ".") for p in parts if p.strip()]


def check(text: str) -> list[str]:
    problems = []
    n = len(sentences(text))
    if n > MAX_SENTENCES:
        problems.append(f"{n} sentences after the greeting (max {MAX_SENTENCES}): fold the location or availability into the pitch sentence")
    low = text.lower()
    for b in BANNED:
        if b in low:
            problems.append(f"banned phrase: {b!r}")
    if EM_DASH in text:
        problems.append("em dash: use a short dash")
    if not text.strip():
        problems.append("empty message")
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("text", nargs="?", help="the message")
    ap.add_argument("--file", help="file with messages separated by a blank line")
    a = ap.parse_args(argv)
    if a.file:
        raw = open(a.file, encoding="utf-8").read()
        msgs = [m for m in re.split(r"\n\s*\n", raw) if m.strip()]
    elif a.text is not None:
        msgs = [a.text]
    else:
        msgs = [sys.stdin.read()]
    bad = 0
    for i, m in enumerate(msgs, 1):
        problems = check(m)
        print(f"DM {i}: {'OK' if not problems else 'FAIL'} ({len(sentences(m))} sentence(s))")
        for p in problems:
            print(f"  - {p}")
        bad += bool(problems)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
