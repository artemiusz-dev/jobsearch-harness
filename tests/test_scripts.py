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


# ---- 0.3.0: DOCX-only builds, merged-profile JSON, DM checker, situation field
import json as _json
import subprocess as _sp
import sys as _sys


def _run_script(name, *args):
    return _sp.run([_sys.executable, str(__import__("pathlib").Path(__file__).resolve().parent.parent / "scripts" / name), *args],
                   capture_output=True, text=True)


def test_check_dm_flags_four_sentences_and_banned_phrases():
    ok = _run_script("check_dm.py", "Hi Piotr, I saw your team's post. I'm a Krakow-based frontend engineer, free now. Is the team on Angular or React?")
    assert ok.returncode == 0, ok.stdout
    long = _run_script("check_dm.py", "Hi Maria, I follow your posts. I build frontends. I live in Krakow. I am free now. Any openings?")
    assert long.returncode == 1 and "5 sentences" in long.stdout
    banned = _run_script("check_dm.py", "Hi Sam, happy to share my CV. Any openings?")
    assert banned.returncode == 1 and "banned phrase" in banned.stdout


def test_check_dm_abbreviations_and_decimals_do_not_split():
    r = _run_script("check_dm.py", "Hi Sam, I'm a Sr. engineer with 12.5 years, e.g. Angular. Any openings?")
    assert r.returncode == 0, r.stdout


def test_jobprofile_json_includes_preset_values(workspace):
    r = _run_script("jobprofile.py", "--workspace", str(workspace), "--json")
    assert r.returncode == 0, r.stderr
    data = _json.loads(r.stdout)
    assert data["scoring"]["rubric_version"] and "weights" in data["scoring"]
    assert "avoid_company_types" in data["targets"]


def test_build_application_docx_only_runs_text_checks(workspace, tmp_path):
    folder = workspace / "acme-backend-2026-11-01"
    folder.mkdir()
    spec = {"cv": {"title": "Senior Backend Engineer", "summary": "Backend engineer building services in Go and Python.",
                   "keywords": ["Go", "Kafka"]}}
    (folder / "spec.json").write_text(_json.dumps(spec), encoding="utf-8")
    r = _run_script("build_application.py", str(folder), "--cv", "--verify", "--docx-only", "--workspace", str(workspace))
    assert r.returncode == 2, r.stdout + r.stderr          # built, but PDF and layout unchecked
    assert "DOCX-only verification" in r.stdout
    assert "covered: Go" in r.stdout and "MISSING: Kafka" in r.stdout
    assert list(folder.glob("*.docx")) and not list(folder.glob("*.pdf"))


def test_build_application_docx_only_rejects_em_dash(workspace):
    folder = workspace / "acme-bad-2026-11-01"
    folder.mkdir()
    spec = {"cv": {"title": "Senior Backend Engineer", "summary": "Builds services " + chr(0x2014) + " fast."}}
    (folder / "spec.json").write_text(_json.dumps(spec), encoding="utf-8")
    r = _run_script("build_application.py", str(folder), "--cv", "--docx-only", "--workspace", str(workspace))
    assert r.returncode != 0 and "Em dash" in (r.stdout + r.stderr)


def test_init_workspace_passes_situation_and_greeting(tmp_path):
    import yaml
    from test_init_workspace import ANSWERS, run
    a = dict(ANSWERS, situation={"available_from": "immediately", "reason_to_give_recruiters": "Project ended."},
             reply_greeting="Alex,")
    t = tmp_path / "ws"
    assert run(tmp_path, t, answers=a).returncode == 0
    raw = yaml.safe_load((t / "profile.yaml").read_text(encoding="utf-8"))
    assert raw["situation"]["available_from"] == "immediately" and raw["style"]["reply_greeting"] == "Alex,"
