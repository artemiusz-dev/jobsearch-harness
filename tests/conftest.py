"""Builds a fully fictional workspace in a temp dir. No real data anywhere."""
import datetime as dt
import shutil
import sys
from pathlib import Path

import docx
import openpyxl
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def make_base_cv(path: Path):
    d = docx.Document()
    lines = [
        "ALEX EXAMPLE", "Senior Backend Engineer", "alex@example.com | Berlin",
        "PROFESSIONAL SUMMARY", "Backend engineer with a fictional career.",
        "TECHNICAL SKILLS",
    ]
    for t in lines:
        d.add_paragraph(t)
    for lab, val in [("Languages", "Go, Python"), ("Data", "PostgreSQL"), ("Infra", "Kubernetes")]:
        p = d.add_paragraph()
        p.add_run(lab + ": ")
        p.add_run(val)
    for t in ["PROFESSIONAL EXPERIENCE", "Example Corp (fictional) - Senior Engineer", "Key Contributions:", "Built things."]:
        d.add_paragraph(t)
    d.save(path)


def make_tracker(path: Path, currency="EUR"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Pipeline"
    ws.append(["#", "Company", "Role", "Source", "Status", "Match %", f"Salary ({currency} gross)", "Applied",
               "Intro Call", "Assignment", "Tech Interview", "Final Interview", "Offer / Rejected",
               "Next Action", "Folder", "Updated"])
    old = (dt.date.today() - dt.timedelta(days=20)).isoformat()
    ws.append([1, "Acme Group", "Backend Engineer", "board", "BACKLOG", 50, "", None, None, None, None, None, None, "", "", "2026-01-01"])
    ws.append([2, "Globex Inc", "Platform Engineer", "board", "APPLIED", 70, "", old, None, None, None, None, None, "", "", old])
    ws.append([3, "Initech", "SRE", "board", "OFFER", 80, "", old, old, None, None, None, None, "", "", old])
    ws.append([4, "Hooli", "Dev", "board", "REJECTED", 40, "", old, None, None, None, None, None, "", "", old])
    wb.save(path)


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "ws"
    (ws / "cv_base").mkdir(parents=True)
    shutil.copy(ROOT / "config" / "profile.example.yaml", ws / "profile.yaml")
    make_base_cv(ws / "cv_base" / "base_cv.docx")
    make_tracker(ws / "applications-tracker.xlsx")
    return ws
