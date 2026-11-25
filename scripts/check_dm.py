#!/usr/bin/env python3
"""Mechanical check for an outbound LinkedIn DM (rules: skills/recruiter-responder, section Outbound LinkedIn DMs).

Usage:
    python3 scripts/check_dm.py "Hi Maria, ..."            # one message as an argument
    python3 scripts/check_dm.py --file drafts.txt          # several messages separated by a blank line
    echo "Hi ..." | python3 scripts/check_dm.py            # from stdin

Rules come from the profile (style.limits.dm_sentences, style.banned_phrases plus style.channel_banned_phrases.dm,
style.forbid_em_dash). Without a workspace the schema defaults apply.
Checks: at most the allowed sentences after the greeting, no banned phrases, no em dash. Exit code 0 = all messages
pass, 1 = at least one fails. This is a guard against miscounting by eye; it does not judge tone or facts.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobprofile as jp  # noqa: E402

EM_DASH = chr(0x2014)
GREETING = re.compile(r"^\s*(hi|hello|hey|dear|cześć|czesc|dzień dobry|hallo)\b[^.!?\n]*?[,!]\s*", re.I)
ABBREV = re.compile(r"\b(e\.g|i\.e|etc|sr|jr|vs|approx)\.", re.I)


def sentences(text: str) -> list[str]:
    body = GREETING.sub("", text.strip(), count=1)
    body = ABBREV.sub(lambda m: m.group(0).replace(".", "․"), body)
    body = re.sub(r"(?<=\d)\.(?=\d)", "․", body)             # decimals
    parts = re.split(r"(?<=[.!?])\s+", body.strip())
    return [p.replace("․", ".") for p in parts if p.strip()]


def load_rules(workspace=None) -> dict:
    """{'max_sentences', 'banned', 'forbid_em_dash'} from the profile; schema defaults when no workspace is found."""
    try:
        prof = jp.load_profile(workspace)
        return {"max_sentences": prof.limit("dm_sentences"), "banned": prof.banned_phrases("dm"),
                "forbid_em_dash": prof["style"]["forbid_em_dash"]}
    except jp.ProfileError as e:
        if "No profile.yaml" not in str(e):
            sys.exit(str(e))            # a profile exists but is invalid: say so instead of silently using defaults
        d = jp.schema_defaults("style")["style"]
        banned = list(d["banned_phrases"]) + list(d["channel_banned_phrases"].get("dm", []))
        return {"max_sentences": d["limits"]["dm_sentences"], "banned": banned, "forbid_em_dash": d["forbid_em_dash"]}


def check(text: str, rules: dict | None = None) -> list[str]:
    rules = rules or load_rules()
    problems = []
    n = len(sentences(text))
    if n > rules["max_sentences"]:
        problems.append(f"{n} sentences after the greeting (max {rules['max_sentences']}): fold the location or availability into the pitch sentence")
    low = text.lower()
    for b in rules["banned"]:
        if b in low:
            problems.append(f"banned phrase: {b!r}")
    if rules["forbid_em_dash"] and EM_DASH in text:
        problems.append("em dash: use a short dash")
    if not text.strip():
        problems.append("empty message")
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("text", nargs="?", help="the message")
    ap.add_argument("--file", help="file with messages separated by a blank line")
    jp.add_workspace_arg(ap)
    a = ap.parse_args(argv)
    rules = load_rules(a.workspace)
    if a.file:
        raw = open(a.file, encoding="utf-8").read()
        msgs = [m for m in re.split(r"\n\s*\n", raw) if m.strip()]
    elif a.text is not None:
        msgs = [a.text]
    else:
        msgs = [sys.stdin.read()]
    bad = 0
    for i, m in enumerate(msgs, 1):
        problems = check(m, rules)
        print(f"DM {i}: {'OK' if not problems else 'FAIL'} ({len(sentences(m))} sentence(s))")
        for p in problems:
            print(f"  - {p}")
        bad += bool(problems)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
