"""End-to-end run of the mechanical pipeline on fully fictional data, with a stub adapter (no network)."""
import datetime as dt
import json
import shutil
import subprocess
import sys
from pathlib import Path

import docx
import openpyxl
import pytest

import jobprofile as jp
from lib import cvbuild as cb

HERE = Path(__file__).resolve().parent
DEMO = HERE / "fixtures" / "demo"
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(DEMO))
import stub_adapter  # noqa: E402

ANSWERS = {
    "full_name": "Alex Example", "email": "alex@example.com", "roles": ["Senior Backend Engineer"],
    "locations": [{"place": "remote", "modes": ["remote"]}, {"place": "Berlin", "modes": ["hybrid"], "relocation": "open"}],
    "currency": "EUR", "period": "year", "floor_gross": 85000, "ask_gross": 100000,
    "languages": [{"language": "English", "level": "C1"}],
    "authorized_in": ["EU"], "effective_deduction_rate": 0.35,
}


@pytest.fixture
def ws(tmp_path):
    a = tmp_path / "answers.json"
    a.write_text(json.dumps(ANSWERS))
    target = tmp_path / "workspace"
    r = subprocess.run([sys.executable, str(SCRIPTS / "init_workspace.py"), "--target", str(target), "--answers", str(a),
                        "--cv", str(DEMO / "demo_cv.docx"), "--market", "generic", "--role", "backend"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return target


def script(name, ws, *args):
    return subprocess.run([sys.executable, str(SCRIPTS / name), "--workspace", str(ws), *args], capture_output=True, text=True)


def test_adapter_stub_follows_contract():
    results = stub_adapter.search(keywords="engineer")
    assert len(results) == 2
    assert all("description" not in r for r in results)
    detail = stub_adapter.get_details(results[0]["id"])
    assert "Go" in detail["description"]
    with pytest.raises(ValueError):
        stub_adapter.check_contract({"id": "x", "title": "t", "company": "c"})          # missing url
    with pytest.raises(ValueError):
        stub_adapter.check_contract({"id": "x", "title": "t", "company": "c", "url": "u", "secret": 1})


def test_scan_to_tracker_to_queries(ws):
    prof = jp.load_profile(ws)
    # a scan: search, fetch details, record rows the way the skills do
    old = (dt.date.today() - dt.timedelta(days=12)).isoformat()
    wb = openpyxl.load_workbook(prof.path("tracker"))
    sheet = wb[prof["tracker"]["sheet"]]
    for i, hit in enumerate(stub_adapter.search(keywords="engineer"), 1):
        d = stub_adapter.get_details(hit["id"])
        assert d["description"]
        status = "APPLIED" if i == 1 else "SKIP"
        sheet.append([None, hit["company"], hit["title"], hit["source"], status, 72 if i == 1 else 20, "",
                      old if i == 1 else None, None, None, None, None, None, "", f"demo-{i}", old])
    wb.save(prof.path("tracker"))

    r = script("restyle_tracker.py", ws)
    assert r.returncode == 0, r.stderr
    assert list((ws / "_backup").glob("applications-tracker_*.xlsx"))

    r = script("tracker_query.py", ws, "match", "Brightwave Labs")
    assert "Brightwave Labs" in r.stdout and "same company" in r.stdout
    r = script("tracker_query.py", ws, "quiet")
    assert "Brightwave" in r.stdout
    r = script("tracker_query.py", ws, "bands")
    assert "60-74" in r.stdout


def test_cv_tailoring_edits_without_soffice(ws):
    prof = jp.load_profile(ws)
    cvspec = {"title": "Staff Backend Engineer", "summary": "Invented summary for a test.",
              "skills": [["Languages", "Go"], ["Data", "PostgreSQL"]]}
    d, _ = cb._apply_cv(prof, cvspec, 0)
    texts = [p.text for p in d.paragraphs]
    assert "Staff Backend Engineer" in texts and "Languages: Go" in texts
    assert not any(t.startswith("Infrastructure:") for t in texts)           # unused skills line removed
    # the base CV itself is untouched
    base = [p.text for p in docx.Document(str(prof.path("base_cv"))).paragraphs]
    assert "Senior Backend Engineer" in base and any(t.startswith("Infrastructure:") for t in base)


@pytest.mark.skipif(shutil.which("soffice") is None, reason="LibreOffice not installed")
def test_full_build_and_verify_pdf(ws):
    folder = ws / "brightwave-labs-senior-backend-2026-11-20"
    folder.mkdir()
    (folder / "spec.json").write_text(json.dumps({
        "cv": {"title": "Senior Backend Engineer", "summary": "Invented summary for a test.", "max_pages": 2,
               "keywords": ["Go", "PostgreSQL"]},
        "letter": {"paragraphs": ["A short invented letter body."], "re": "Re: Senior Backend Engineer - Brightwave Labs"},
    }))
    r = script("build_application.py", ws, str(folder.name), "--verify")
    assert r.returncode == 0, r.stdout + r.stderr
    assert list(folder.glob("*.pdf"))
