#!/usr/bin/env python3
"""Add or update one application row in the tracker, safely (backup first, validated, duplicate-aware).

    python3 scripts/tracker_add.py --workspace . add --company "Acme" --role "Senior Frontend Engineer" \\
        --status APPLIED --match 72 --source LinkedIn --salary "25-40k PLN B2B" --applied 2026-11-24 \\
        --folder acme-sr-fe-2026-11-24 --next-action "Follow up 2026-12-04"
    python3 scripts/tracker_add.py --workspace . update --company "Acme" --status SCREENING \\
        --stage "Intro Call=2026-11-30" --append-next-action "call booked"

Rules (the workspace CLAUDE.md immutability rule is enforced here):
  - The tracker is copied to <backup_dir>/<name>_YYYY-MM-DD_HHMMSS.xlsx BEFORE anything is written.
  - Status must be one of the profile's statuses; dates are YYYY-MM-DD; --stage takes "<column>=<date>" for the
    stage columns (Applied is --applied). `Updated` is set to today. The `#` column is left for restyle.
  - add: the same company (fuzzy match, as in tracker_query.py match) with the same role is refused (exit 2)
    unless --allow-duplicate; the same company with another role is added with a warning.
  - update: the row is found by company (and optionally --role). Zero or several candidates: nothing is
    written, the candidates are listed (exit 2) so the user can decide. Rows are never deleted.
  - After a write, restyle_tracker.py runs (sort, style, second backup). --dry-run changes nothing.
Exit codes: 0 done, 1 error, 2 needs a decision (duplicate or ambiguous row).
"""
from __future__ import annotations

import argparse
import datetime as dt
import difflib
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _deps  # noqa: E402

_deps.ensure()

import openpyxl  # noqa: E402
from jobprofile import ProfileError, add_workspace_arg, load_profile  # noqa: E402
from tracker_query import BASE_SUFFIXES, norm_company  # noqa: E402

FIELDS = ("company", "role", "source", "status", "match", "applied", "next_action", "folder")     # command-line fields; headers come from the profile
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class TrackerError(Exception):
    pass


def backup(tracker: Path, backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime('%Y-%m-%d_%H%M%S')
    dest, n = backup_dir / f"{tracker.stem}_{stamp}.xlsx", 1
    while dest.exists():                 # backups are immutable: two within one second must not overwrite each other
        dest = backup_dir / f"{tracker.stem}_{stamp}_{n}.xlsx"
        n += 1
    shutil.copy2(tracker, dest)
    return dest


def check_date(label: str, value: str) -> str:
    if not DATE_RE.match(value):
        raise TrackerError(f"{label} must be YYYY-MM-DD (got {value!r})")
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        raise TrackerError(f"{label} is not a real date: {value!r}") from None
    return value


def parse_stage(items, headers):
    out = {}
    for item in items or []:
        col, sep, val = item.partition("=")
        col, val = col.strip(), val.strip()
        if not sep or col not in headers:
            raise TrackerError(f"--stage needs '<column>=<date>' with a tracker column; got {item!r} (columns: {', '.join(h for h in headers if h)})")
        out[col] = check_date(f"--stage {col}", val)
    return out


def collect(a, prof, headers):
    """Column -> value for every field given on the command line."""
    vals = {}
    for key in FIELDS:
        v = getattr(a, key, None)
        if v not in (None, ""):
            vals[prof.col(key)] = v
    status, applied, match = prof.col("status"), prof.col("applied"), prof.col("match")
    if status in vals:
        names = [s["name"] for s in prof.statuses]
        if vals[status] not in names:
            raise TrackerError(f"status {vals[status]!r} is not valid; use one of: {', '.join(names)}")
    if applied in vals:
        check_date("--applied", vals[applied])
    if match in vals:
        try:
            vals[match] = float(vals[match]) if "." in str(vals[match]) else int(vals[match])
        except ValueError:
            raise TrackerError(f"--match must be a number (got {vals[match]!r})") from None
    if getattr(a, "salary", None):
        vals[prof.salary_column] = a.salary
    vals.update(parse_stage(getattr(a, "stage", None), headers))
    for col in vals:
        if col not in headers:
            raise TrackerError(f"the tracker has no column {col!r}; fix the profile or the tracker header")
    return vals


def candidates(rows, company, role, suffixes, prof):
    target = norm_company(company, suffixes)
    if not target:
        raise TrackerError("company is empty after normalisation")
    hits = []
    for r in rows:
        c = norm_company(r[prof.col("company")], suffixes)
        if not c:
            continue
        tt, ct = set(target.split()), set(c.split())
        if difflib.SequenceMatcher(None, target, c).ratio() >= prof["tracker"]["match_ratio"] or tt <= ct or ct <= tt:
            same_role = bool(role) and role.lower() in str(r.get(prof.col("role"), "")).lower()
            hits.append((r, same_role))
    return hits


def read_rows(ws, headers, company_col):
    rows = []
    for i, cells in enumerate(ws.iter_rows(min_row=2), start=2):
        d = {h: c.value for h, c in zip(headers, cells) if h}
        if d.get(company_col):
            d["_row"] = i
            rows.append(d)
    return rows


def describe(r, prof):
    c = prof.col
    return (f"row {r['_row']}: {r[c('company')]} | {r.get(c('role'))} | {r.get(c('status'))} | "
            f"applied {r.get(c('applied'))} | updated {r.get(c('updated'))}")


def run(a) -> int:
    try:
        prof = load_profile(a.workspace)
    except ProfileError as e:
        print(str(e), file=sys.stderr)
        return 1
    tracker = prof.path("tracker")
    if not tracker.exists():
        print(f"tracker not found: {tracker}", file=sys.stderr)
        return 1
    sheet = prof["tracker"]["sheet"]
    wb = openpyxl.load_workbook(tracker)
    if sheet not in wb.sheetnames:
        print(f"sheet {sheet!r} not found (found: {', '.join(wb.sheetnames)})", file=sys.stderr)
        return 1
    ws = wb[sheet]
    headers = [c.value for c in ws[1]]
    for need in (prof.col("company"), prof.col("status"), prof.col("updated")):
        if need not in headers:
            print(f"the tracker has no {need!r} column; nothing changed", file=sys.stderr)
            return 1
    suffixes = BASE_SUFFIXES | {s.lower() for s in prof["tracker"].get("company_suffixes", [])}
    today = dt.date.today().isoformat()
    status_col, updated_col = prof.col("status"), prof.col("updated")
    try:
        vals = collect(a, prof, headers)
        rows = read_rows(ws, headers, prof.col("company"))
        hits = candidates(rows, a.company, getattr(a, "role", None), suffixes, prof)
        if a.cmd == "add":
            if not a.role:
                raise TrackerError("add needs --role")
            same = [r for r, same_role in hits if same_role]
            if same and not a.allow_duplicate:
                print("Refusing to add: the same company and role is already in the tracker:", file=sys.stderr)
                for r in same:
                    print("  " + describe(r, prof), file=sys.stderr)
                print("Use `update`, or --allow-duplicate if this is a different requisition.", file=sys.stderr)
                return 2
            for r, _ in hits:
                if r not in same:
                    print("note: same company, other role: " + describe(r, prof))
            names = [s["name"] for s in prof.statuses]
            vals.setdefault(status_col, prof.default_new_status if prof.default_new_status in names else names[0])
            vals[updated_col] = today
            row = [vals.get(h) if h else None for h in headers]
            if a.dry_run:
                print("dry run: would append", dict(vals))
                return 0
            made = backup(tracker, prof.path("backup_dir"))
            ws.append(row)
            wb.save(tracker)
            print(f"Added {a.company} | {a.role} | {vals[status_col]}. Backup: {made}")
        else:
            if not hits:
                raise TrackerError(f"no row matches company {a.company!r}")
            pick = [r for r, same_role in hits if same_role] if a.role else [r for r, _ in hits]
            if len(pick) != 1:
                print(f"{len(pick)} rows match; say which one (add --role) before anything is changed:", file=sys.stderr)
                for r in (pick or [r for r, _ in hits]):
                    print("  " + describe(r, prof), file=sys.stderr)
                return 2
            target = pick[0]
            vals.pop(prof.col("company"), None)
            vals.pop(prof.col("role"), None)
            if a.append_next_action:
                na = prof.col("next_action")
                old = str(target.get(na) or "").strip()
                vals[na] = f"{old}; {a.append_next_action}" if old else a.append_next_action
            if not vals:
                raise TrackerError("nothing to update: give --status, --stage, --next-action, ...")
            vals[updated_col] = today
            if a.dry_run:
                print(f"dry run: would update {describe(target, prof)} with", vals)
                return 0
            made = backup(tracker, prof.path("backup_dir"))
            for col, v in vals.items():
                ws.cell(row=target["_row"], column=headers.index(col) + 1, value=v)
            wb.save(tracker)
            print(f"Updated {target[prof.col('company')]} ({', '.join(vals)}). Backup: {made}")
    except TrackerError as e:
        print(f"tracker_add: {e}", file=sys.stderr)
        return 1
    r = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "restyle_tracker.py"),
                        "--workspace", str(prof.workspace)], capture_output=True, text=True)
    if r.returncode != 0:
        print("tracker_add: the row was written, but restyle_tracker.py failed:\n" + (r.stdout + r.stderr).strip(), file=sys.stderr)
        return 1
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_workspace_arg(ap)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("add", "update"):
        p = sub.add_parser(name)
        p.add_argument("--company", required=True)
        p.add_argument("--role")
        p.add_argument("--source")
        p.add_argument("--status")
        p.add_argument("--match")
        p.add_argument("--salary")
        p.add_argument("--applied")
        p.add_argument("--stage", action="append", metavar="COLUMN=DATE")
        p.add_argument("--next-action", dest="next_action")
        p.add_argument("--folder")
        p.add_argument("--dry-run", action="store_true")
        if name == "add":
            p.add_argument("--allow-duplicate", action="store_true")
        else:
            p.add_argument("--append-next-action", dest="append_next_action")
    a = ap.parse_args(argv)
    if a.cmd == "add":
        a.append_next_action = None
    return run(a)


if __name__ == "__main__":
    sys.exit(main())
