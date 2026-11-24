import subprocess
import sys
from pathlib import Path

import openpyxl

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "tracker_add.py"


def run(ws, *args):
    return subprocess.run([sys.executable, str(SCRIPT), "--workspace", str(ws), *args], capture_output=True, text=True)


def rows(ws):
    sheet = openpyxl.load_workbook(ws / "applications-tracker.xlsx")["Pipeline"]
    head = [c.value for c in sheet[1]]
    return [dict(zip(head, [c.value for c in r])) for r in sheet.iter_rows(min_row=2) if r[1].value]


def backups(ws):
    return sorted((ws / "_backup").glob("applications-tracker_*.xlsx")) if (ws / "_backup").exists() else []


def test_add_creates_backup_row_and_restyles(workspace):
    before = len(rows(workspace))
    r = run(workspace, "add", "--company", "Zeta Labs", "--role", "Senior Backend Engineer", "--status", "APPLIED",
            "--match", "72", "--applied", "2026-11-24", "--folder", "zeta-2026-11-24", "--next-action", "Follow up")
    assert r.returncode == 0, r.stderr
    got = [x for x in rows(workspace) if x["Company"] == "Zeta Labs"]
    assert len(rows(workspace)) == before + 1 and got[0]["Status"] == "APPLIED" and got[0]["Match %"] == 72
    assert got[0]["Updated"]                       # set to today
    assert len(backups(workspace)) >= 2            # ours (before writing) plus restyle's


def test_add_refuses_same_company_and_role_but_allows_other_role(workspace):
    first = rows(workspace)[0]
    dup = run(workspace, "add", "--company", first["Company"], "--role", first["Role"], "--status", "To Apply")
    assert dup.returncode == 2 and "already in the tracker" in dup.stderr
    other = run(workspace, "add", "--company", first["Company"], "--role", "Totally Different Role", "--status", "To Apply")
    assert other.returncode == 0 and "other role" in other.stdout


def test_add_fuzzy_duplicate_variant_is_caught(workspace):
    first = rows(workspace)[0]
    variant = first["Company"] + " Group"
    r = run(workspace, "add", "--company", variant, "--role", first["Role"])
    assert r.returncode == 2


def test_invalid_status_and_dates_change_nothing(workspace):
    n = len(backups(workspace))
    bad_status = run(workspace, "add", "--company", "Q", "--role", "R", "--status", "MAYBE")
    assert bad_status.returncode == 1 and "not valid" in bad_status.stderr
    bad_date = run(workspace, "add", "--company", "Q", "--role", "R", "--applied", "24/11/2026")
    assert bad_date.returncode == 1 and "YYYY-MM-DD" in bad_date.stderr
    bad_stage = run(workspace, "add", "--company", "Q", "--role", "R", "--stage", "Nope=2026-11-24")
    assert bad_stage.returncode == 1
    assert len(backups(workspace)) == n and not [x for x in rows(workspace) if x["Company"] == "Q"]


def test_update_sets_status_stage_and_appends_next_action(workspace):
    target = [x for x in rows(workspace) if x["Status"] == "APPLIED"][0]
    r = run(workspace, "update", "--company", target["Company"], "--status", "SCREENING",
            "--stage", "Intro Call=2026-11-30", "--append-next-action", "call booked")
    assert r.returncode == 0, r.stderr
    got = [x for x in rows(workspace) if x["Company"] == target["Company"]][0]
    assert got["Status"] == "SCREENING" and str(got["Intro Call"])[:10] == "2026-11-30"
    assert str(got["Next Action"]).endswith("call booked")


def test_update_ambiguous_or_missing_row_writes_nothing(workspace):
    run(workspace, "add", "--company", "Twin Corp", "--role", "Engineer A", "--status", "To Apply")
    run(workspace, "add", "--company", "Twin Corp", "--role", "Engineer B", "--status", "To Apply")
    n = len(backups(workspace))
    amb = run(workspace, "update", "--company", "Twin Corp", "--status", "APPLIED")
    assert amb.returncode == 2 and "2 rows match" in amb.stderr
    miss = run(workspace, "update", "--company", "Does Not Exist Ltd", "--status", "APPLIED")
    assert miss.returncode == 1 and "no row matches" in miss.stderr
    assert len(backups(workspace)) == n
    ok = run(workspace, "update", "--company", "Twin Corp", "--role", "Engineer B", "--status", "APPLIED")
    assert ok.returncode == 0


def test_dry_run_changes_nothing(workspace):
    n_rows, n_backups = len(rows(workspace)), len(backups(workspace))
    r = run(workspace, "add", "--company", "Dry Co", "--role", "R", "--status", "APPLIED", "--dry-run")
    assert r.returncode == 0 and "dry run" in r.stdout
    assert len(rows(workspace)) == n_rows and len(backups(workspace)) == n_backups
