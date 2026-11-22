import json
import subprocess
import sys
from pathlib import Path

import jobprofile as jp
from conftest import make_base_cv

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "init_workspace.py"

ANSWERS = {
    "full_name": "Alex Example", "email": "alex@example.com",
    "roles": ["Senior Frontend Engineer"],
    "locations": [{"place": "remote", "modes": ["remote"]}],
    "floor_gross": 20000, "floor_net": 14000, "ask_gross": 22000,
    "languages": [{"language": "English", "level": "C1"}],
}


def run(tmp_path, target, answers=ANSWERS, market="poland", role="frontend", cv=True):
    a = tmp_path / "answers.json"
    a.write_text(json.dumps(answers))
    cmd = [sys.executable, str(SCRIPT), "--target", str(target), "--answers", str(a), "--market", market, "--role", role]
    if cv:
        c = tmp_path / "cv.docx"
        make_base_cv(c)
        cmd += ["--cv", str(c)]
    return subprocess.run(cmd, capture_output=True, text=True)


def test_creates_valid_workspace(tmp_path):
    t = tmp_path / "ws"
    r = run(tmp_path, t)
    assert r.returncode == 0, r.stderr
    p = jp.load_profile(t)
    assert p.currency == "PLN" and p.salary_column == "Salary (PLN gross)"
    for f in ["CLAUDE.md", "docs/scoring-rubric.md", "docs/salary-rules.md", "knowledge-base.md",
              "interview-kb-hard-skills.md", "interview-kb-soft-skills.md", "pipeline.md",
              "application-forms.md", "_template.md", "cv_base/README.md", "cv_base/base_cv.docx",
              "applications-tracker.xlsx", ".gitignore"]:
        assert (t / f).exists(), f
    assert not list(t.rglob("*.skeleton.md"))
    assert "Poland market pack" in (t / "docs" / "salary-rules.md").read_text()
    assert "CV structure OK" in r.stdout


def test_tracker_has_expected_headers(tmp_path):
    import openpyxl
    t = tmp_path / "ws"
    run(tmp_path, t)
    ws = openpyxl.load_workbook(t / "applications-tracker.xlsx")["Pipeline"]
    headers = [c.value for c in ws[1]]
    assert headers[6] == "Salary (PLN gross)" and headers[0] == "#" and len(headers) == 16


def test_refuses_non_empty_target(tmp_path):
    t = tmp_path / "ws"
    t.mkdir()
    (t / "keep.txt").write_text("x")
    r = run(tmp_path, t)
    assert r.returncode != 0 and "not empty" in r.stderr
    assert (t / "keep.txt").read_text() == "x"


def test_missing_answer_fails_and_leaves_nothing(tmp_path):
    t = tmp_path / "ws"
    bad = {k: v for k, v in ANSWERS.items() if k != "floor_gross"}
    r = run(tmp_path, t, answers=bad)
    assert r.returncode != 0 and "floor_gross" in r.stderr


def test_invalid_profile_cleans_up(tmp_path):
    t = tmp_path / "ws"
    bad = dict(ANSWERS, languages=[{"language": "English", "level": "fluent"}])
    r = run(tmp_path, t, answers=bad)
    assert r.returncode != 0 and not t.exists()


def test_generic_market_needs_currency(tmp_path):
    r = run(tmp_path, tmp_path / "ws", market="generic", role="generic")
    assert r.returncode != 0 and "currency" in r.stderr


def test_no_personal_data_in_workspace_templates(tmp_path):
    t = tmp_path / "ws"
    run(tmp_path, t)
    claude = (t / "CLAUDE.md").read_text()
    assert "alex@example.com" not in claude          # personal facts live in profile.yaml only
