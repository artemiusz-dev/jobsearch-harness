import subprocess
import sys
from pathlib import Path

import docx
import openpyxl

import jobprofile as jp
from lib import cvbuild as cb

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def run(script, ws, *args):
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args, "--workspace", str(ws)],
                          capture_output=True, text=True)


def test_tracker_match_fuzzy(workspace):
    # script takes --workspace after the subcommand args only at top level, so put it first
    r = subprocess.run([sys.executable, str(SCRIPTS / "tracker_query.py"), "--workspace", str(workspace),
                        "match", "Acme"], capture_output=True, text=True)
    assert r.returncode == 0 and "Acme Group" in r.stdout


def test_tracker_quiet_and_bands(workspace):
    base = [sys.executable, str(SCRIPTS / "tracker_query.py"), "--workspace", str(workspace)]
    q = subprocess.run(base + ["quiet", "--days", "10"], capture_output=True, text=True)
    assert q.returncode == 0 and "Globex Inc" in q.stdout
    b = subprocess.run(base + ["bands"], capture_output=True, text=True)
    assert b.returncode == 0 and "60-74" in b.stdout and "75+" in b.stdout


def test_restyle_sorts_backs_up_and_keeps_rows(workspace):
    r = run("restyle_tracker.py", workspace)
    assert r.returncode == 0, r.stderr
    assert list((workspace / "_backup").glob("applications-tracker_*.xlsx"))
    ws = openpyxl.load_workbook(workspace / "applications-tracker.xlsx")["Pipeline"]
    statuses = [row[4] for row in ws.iter_rows(min_row=2, values_only=True)]
    assert statuses == ["OFFER", "APPLIED", "BACKLOG", "REJECTED"]


def test_cleanup_dry_run_does_not_delete(workspace):
    junk = workspace / ".DS_Store"
    junk.write_text("x")
    r = run("cleanup.py", workspace)
    assert r.returncode == 0 and "DRY RUN" in r.stdout and junk.exists()
    r = run("cleanup.py", workspace, "--execute")
    assert not junk.exists()


def test_cleanup_never_touches_extensionless_files(workspace):
    keep = workspace / "Makefile"
    keep.write_text("x")
    run("cleanup.py", workspace, "--execute")
    assert keep.exists()


def test_cv_map_by_headings(workspace):
    prof = jp.load_profile(workspace)
    P = docx.Document(str(prof.path("base_cv"))).paragraphs
    m = cb.cv_map(prof, P)
    assert (m["name"], m["title"], m["contact"]) == (0, 1, 2)
    assert m["summary"] == 4 and len(m["skills"]) == 3


def test_cv_edit_applies_without_hardcoded_indices(workspace):
    prof = jp.load_profile(workspace)
    c = {"title": "Staff Backend Engineer", "summary": "New summary.", "skills": [["Languages", "Rust"]]}
    d, _ = cb._apply_cv(prof, c, 0)
    texts = [p.text for p in d.paragraphs]
    assert "Staff Backend Engineer" in texts and "New summary." in texts
    assert "Languages: Rust" in texts and not any(t.startswith("Data:") for t in texts)


def test_em_dash_rejected(workspace):
    prof = jp.load_profile(workspace)
    import pytest
    with pytest.raises(SystemExit):
        cb._check_text(prof, "bad — dash")
