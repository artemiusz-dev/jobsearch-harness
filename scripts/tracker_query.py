#!/usr/bin/env python3
"""Read-only queries over the applications tracker (live) and optional archived snapshots.

Why this exists: state should move through a tool, not through the conversation. Reading hundreds of
archived rows into context to check one company name is slow, and fuzzy-matching by eye misses
near-duplicates like "Acme (Labs)" vs "Acme Group (Labs)".

This script NEVER writes to any tracker, so the immutability rule (backup before write) does not apply.

Usage (from the workspace, or pass --workspace):
  python3 scripts/tracker_query.py match "Acme Group" [--role "backend"]
  python3 scripts/tracker_query.py quiet [--days N]
  python3 scripts/tracker_query.py bands

match  Fuzzy company lookup across the live tracker and any tracker.archives snapshots from profile.yaml.
       Use before any JD analysis.
quiet  Open applications (APPLIED / CV SENT) with no reply for N days (default followups.first_after_days)
       and fewer than followups.max_followups logged follow-ups. Follow-ups are counted from the marker
       "followed up YYYY-MM-DD" in Next Action. Rows quiet for followups.stale_after_days or more are listed
       as stale-sweep candidates (propose only; the user confirms any status change).
calibrate  Like bands, but only matured applications, with 95% intervals and a plain verdict on whether the score predicts replies.
bands  Funnel by Match % band (reply / interview / offer rates). Band edges come from scoring.thresholds.
       Live and archive are reported separately because rubrics may differ between them.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _deps  # noqa: E402

_deps.ensure()

import openpyxl  # noqa: E402
from jobprofile import ProfileError, add_workspace_arg, load_profile  # noqa: E402

BASE_SUFFIXES = {
    "group", "inc", "inc.", "ltd", "llc", "gmbh", "ag", "sa", "s.a.", "corp", "corporation", "co", "limited",
    "technologies", "technology", "software", "solutions", "systems", "holding", "plc", "bv", "srl", "oy", "ab",
}


def norm_company(name: str, suffixes: set[str]) -> str:
    s = str(name or "").lower()
    s = re.sub(r"\(.*?\)", " ", s)  # drop parenthetical sub-brands
    s = re.sub(r"[^\w ]+|_", " ", s)
    toks = [t for t in s.split() if t not in suffixes]
    return " ".join(toks)


def load(path: Path, sheet: str):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        if sheet not in wb.sheetnames:
            print(f"! {path.name}: no sheet named '{sheet}' (found: {', '.join(wb.sheetnames)}); skipped", file=sys.stderr)
            return []
        rows = list(wb[sheet].iter_rows(values_only=True))
    finally:
        wb.close()
    if not rows:
        return []
    head = [str(h) for h in rows[0]]
    out = []
    for r in rows[1:]:
        d = dict(zip(head, r))
        if d.get("Company"):
            d["_src"] = path.name
            out.append(d)
    return out


def all_sources(prof):
    sheet = prof["tracker"]["sheet"]
    live = prof.path("tracker")
    srcs = [("live", load(live, sheet))] if live.exists() else []
    for rel in prof["tracker"].get("archives", []):
        p = prof.workspace / rel
        if p.exists():
            srcs.append(("archive:" + p.name, load(p, sheet)))
    return srcs


def to_date(v):
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except (ValueError, TypeError):
        return None


def to_score(v):
    try:
        return float(str(v).replace("%", "").strip())
    except (ValueError, TypeError):
        return None


def cmd_match(prof, a):
    suffixes = BASE_SUFFIXES | {s.lower() for s in prof["tracker"].get("company_suffixes", [])}
    target = norm_company(a.company, suffixes)
    if not target:
        print("empty company after normalisation")
        return 1
    hits = []
    for label, rows in all_sources(prof):
        for r in rows:
            c = norm_company(r["Company"], suffixes)
            if not c:
                continue
            ratio = difflib.SequenceMatcher(None, target, c).ratio()
            tt, ct = set(target.split()), set(c.split())
            contained = tt <= ct or ct <= tt          # whole-word containment: "go" must not match "google"
            if ratio >= 0.85 or contained:
                if a.role and a.role.lower() not in str(r.get("Role", "")).lower():
                    tag = "same company, other role"
                else:
                    tag = "same company" if not a.role else "same company + role"
                hits.append((label, r, tag, ratio))
    if not hits:
        print(f"No match for '{a.company}' (normalised: '{target}') in live or archive.")
        return 0
    print(f"{len(hits)} match(es) for '{a.company}' (normalised: '{target}'):")
    for label, r, tag, _ratio in hits:
        print(
            f"- [{label}] {r['Company']} | {r.get('Role')} | {r.get('Status')} | "
            f"match {r.get('Match %')} | applied {r.get('Applied')} | "
            f"outcome {r.get('Offer / Rejected')} | updated {r.get('Updated')} | {tag}"
        )
    return 0


def cmd_quiet(prof, a):
    fu_cfg = prof["followups"]
    days_min = a.days if a.days is not None else fu_cfg["first_after_days"]
    max_fu, stale_days = fu_cfg["max_followups"], fu_cfg["stale_after_days"]
    today = dt.date.today()
    if not prof.path("tracker").exists():
        print(f"No tracker at {prof.path('tracker')}")
        return 1
    roles = prof["tracker"]["status_roles"]
    rows = load(prof.path("tracker"), prof["tracker"]["sheet"])
    cand, stale = [], []
    for r in rows:
        if r.get("Status") not in roles["open_for_followup"]:
            continue
        na = str(r.get("Next Action") or "")
        fu = re.findall(r"followed up (\d{4}-\d{2}-\d{2})", na)
        dates = [to_date(x) for x in fu] + [to_date(r.get("Applied"))]
        dates = [d for d in dates if d]
        last = max(dates) if dates else None
        if last is None:
            print(f"! no parsable Applied date, skipped: {r['Company']} | {r.get('Role')}")
            continue
        days = (today - last).days
        item = (days, r["Company"], r.get("Role"), r.get("Status"), len(fu), r.get("Applied"))
        if days >= stale_days:
            stale.append(item)
        if days >= days_min and len(fu) < max_fu:
            cand.append(item)
    cand.sort(reverse=True)
    print(f"Follow-up candidates (>= {days_min}d quiet, < {max_fu} follow-ups): {len(cand)}")
    for d, c, role, st, n, ap in cand:
        print(f"- {d:>3}d | {c} | {role} | {st} | follow-ups {n} | applied {ap}")
    stale.sort(reverse=True)
    print(f"\nStale-sweep candidates (>= {stale_days}d quiet; propose only, user confirms): {len(stale)}")
    for d, c, role, st, n, _ap in stale:
        print(f"- {d:>3}d | {c} | {role} | {st} | follow-ups {n}")
    return 0


def make_band(edges):
    lo, mid, hi = edges
    labels = [f"<{lo}", f"{lo}-{mid - 1}", f"{mid}-{hi - 1}", f"{hi}+"]

    def band(s):
        return labels[0] if s < lo else labels[1] if s < mid else labels[2] if s < hi else labels[3]
    return band, labels


def cmd_bands(prof, a):
    band, labels = make_band(prof.band_edges)
    roles = prof["tracker"]["status_roles"]
    for label, rows in all_sources(prof):
        stats: dict[str, dict[str, int]] = {}
        for r in rows:
            s = to_score(r.get("Match %"))
            applied = to_date(r.get("Applied")) is not None  # rows without an Applied date (direct/referral) are excluded
            if s is None or not applied:
                continue
            b = stats.setdefault(band(s), dict(n=0, replied=0, interview=0, offer=0))
            b["n"] += 1
            if r.get("Intro Call") or r.get("Status") in roles["replied"]:
                b["replied"] += 1
            if r.get("Tech Interview") or r.get("Final Interview") or r.get("Status") in roles["interview"]:
                b["interview"] += 1
            if r.get("Status") in roles["offer"]:
                b["offer"] += 1
        tag = f"rubric {prof['scoring']['rubric_version']}" if label == "live" else "archive: rubric may differ"
        print(f"\n{label} ({tag}) - applications with a Match % and an Applied date")
        if not stats:
            print("  (none)")
            continue
        print("  band    | applied | replied | interview | offer")
        for k in labels:
            if k in stats:
                v = stats[k]
                print(f"  {k:<7} | {v['n']:>7} | {v['replied']:>7} | {v['interview']:>9} | {v['offer']:>5}")
    print("\nDo not compare live and archive bands directly if the rubric changed. "
          "Re-tune only after ~30 live applications with outcomes.")
    return 0


def cmd_calibrate(prof, a):
    from lib import calibration as cal
    band, labels = make_band(prof.band_edges)
    roles = prof["tracker"]["status_roles"]
    today = dt.date.today()
    for label, rows in all_sources(prof):
        stats, too_recent = cal.band_stats(rows, band, roles, today, a.mature_days, to_score, to_date)
        tag = f"rubric {prof['scoring']['rubric_version']}" if label == "live" else "archive: rubric may differ"
        print(f"\n{label} ({tag}) - applied at least {a.mature_days} days ago ({too_recent} newer applications left out)")
        if not stats:
            print("  (none)")
            continue
        print("  band    | applied | replied (95% interval) | interview | offer")
        for k in labels:
            if k in stats:
                v = stats[k]
                star = "*" if v["n"] < cal.MIN_N else " "
                print(f"  {k:<7} | {v['n']:>6}{star} | {cal.fmt_rate(v['replied'], v['n']):<22} | {v['interview']:>9} | {v['offer']:>5}")
        for line in cal.verdict(labels, stats):
            print("  -> " + line)
    print("\nA reply is an intro call or a status in tracker.status_roles.replied. Archives use another rubric: read them "
          "separately. Thresholds live in profile.yaml (scoring.thresholds); change them only after the verdict says the bands separate.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_workspace_arg(ap)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("match")
    m.add_argument("company")
    m.add_argument("--role")
    m.set_defaults(fn=cmd_match)
    q = sub.add_parser("quiet")
    q.add_argument("--days", type=int)
    q.set_defaults(fn=cmd_quiet)
    b = sub.add_parser("bands")
    b.set_defaults(fn=cmd_bands)
    c = sub.add_parser("calibrate")
    c.add_argument("--mature-days", type=int, default=14, help="ignore applications newer than this (a reply needs time)")
    c.set_defaults(fn=cmd_calibrate)
    a = ap.parse_args()
    try:
        prof = load_profile(a.workspace)
    except ProfileError as e:
        sys.exit(str(e))
    return a.fn(prof, a)


if __name__ == "__main__":
    sys.exit(main())
