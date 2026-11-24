"""Regression tests for the findings of the Definition-of-Done review."""
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

import docx
import jobprofile as jp
import openpyxl
import pytest
import yaml
from conftest import make_base_cv
from lib import cvbuild as cb
from openpyxl.comments import Comment

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
PYTHON = sys.executable


def edit_profile(ws, fn):
    f = ws / "profile.yaml"
    d = yaml.safe_load(f.read_text())
    fn(d)
    f.write_text(yaml.safe_dump(d))


def run(script, ws, *args, env=None):
    return subprocess.run([PYTHON, str(SCRIPTS / script), "--workspace", str(ws), *args],
                          capture_output=True, text=True, env=env)


# ---------------------------------------------------------------- jobprofile
@pytest.mark.parametrize("name", ["../x", "../../etc/passwd", "UPPER", "a/b"])
def test_preset_names_cannot_traverse(workspace, name):
    edit_profile(workspace, lambda d: d.__setitem__("presets", {"market": name, "role": "backend"}))
    with pytest.raises(jp.ProfileError, match="preset name"):
        jp.load_profile(workspace)


def test_path_fields_cannot_escape_workspace(workspace):
    edit_profile(workspace, lambda d: d["paths"].__setitem__("output_dir_pattern", "../{company_slug}"))
    with pytest.raises(jp.ProfileError, match="output_dir_pattern"):
        jp.load_profile(workspace)
    edit_profile(workspace, lambda d: d["paths"].__setitem__("output_dir_pattern", "{company_slug}"))
    edit_profile(workspace, lambda d: d["tracker"].__setitem__("archives", ["../old.xlsx"]))
    with pytest.raises(jp.ProfileError, match="archives"):
        jp.load_profile(workspace)


def test_output_names_never_collide_and_validate_placeholders(workspace):
    edit_profile(workspace, lambda d: d["identity"].__setitem__("output_name_pattern", "{first}-{last}-{company_slug}-CV"))
    p = jp.load_profile(workspace)
    assert p.output_stem("acme", "CV") != p.output_stem("acme", "Cover-Letter")
    edit_profile(workspace, lambda d: d["identity"].__setitem__("output_name_pattern", "{first}-{role_slug}"))
    with pytest.raises(jp.ProfileError, match="unsupported placeholder"):
        jp.load_profile(workspace)


@pytest.mark.parametrize("full_name,expected_prefix", [
    ("Łukasz Żak", "Łukasz-Zak-"),
    ("Иван Петров", "Иван-Петров-"),
    ("José García", "Jose-Garcia-"),
])
def test_names_from_any_script_survive_in_file_names(workspace, full_name, expected_prefix):
    edit_profile(workspace, lambda d: d["identity"].__setitem__("full_name", full_name))
    assert jp.load_profile(workspace).output_stem("acme", "CV").startswith(expected_prefix)


def test_defaults_apply_to_array_items(workspace):
    edit_profile(workspace, lambda d: d.__setitem__("boards", [{"id": "x"}]))
    b = jp.load_profile(workspace)["boards"][0]
    assert b["enabled"] is True and b["max_results"] == 50


def test_invalid_email_rejected(workspace):
    edit_profile(workspace, lambda d: d["identity"].__setitem__("email", "not-an-email"))
    with pytest.raises(jp.ProfileError, match="email"):
        jp.load_profile(workspace)


# ---------------------------------------------------------------- cv structure
def build_cv_doc(path: Path, paragraphs, skills_runs=2):
    d = docx.Document()
    for kind, text in paragraphs:
        p = d.add_paragraph()
        if kind == "skill":
            lab, val = text
            if skills_runs == 2:
                p.add_run(lab + ": ")
                p.add_run(val)
            else:
                p.add_run(f"{lab}: {val}")
        elif kind == "empty":
            pass
        else:
            p.add_run(text)
    d.save(path)


HEADER = [("t", "ALEX EXAMPLE"), ("t", "Skills Engineer"), ("t", "alex@example.com")]


def test_sections_in_any_order_and_other_headings_end_the_skills_block(workspace):
    cv = workspace / "cv_base" / "base_cv.docx"
    build_cv_doc(cv, HEADER + [
        ("t", "PROFESSIONAL SUMMARY"), ("t", "Summary."),
        ("t", "PROFESSIONAL EXPERIENCE"), ("t", "Job"), ("t", "Did things."),
        ("t", "TECHNICAL SKILLS"), ("skill", ("Languages", "Go")), ("skill", ("Data", "SQL")),
        ("t", "EDUCATION"), ("t", "Some University"),
    ])
    m = cb.cv_map(jp.load_profile(workspace), docx.Document(str(cv)).paragraphs)
    texts = [p.text for p in docx.Document(str(cv)).paragraphs]
    assert [texts[i] for i in m["skills"]] == ["Languages: Go", "Data: SQL"]
    assert texts[m["skills_heading"]] == "TECHNICAL SKILLS"          # not the 'Skills Engineer' title line


@pytest.mark.parametrize("runs", [1, 2])
def test_skills_lines_work_with_one_or_two_runs(workspace, runs):
    cv = workspace / "cv_base" / "base_cv.docx"
    build_cv_doc(cv, HEADER + [
        ("t", "PROFESSIONAL SUMMARY"), ("t", "Summary."), ("t", "TECHNICAL SKILLS"),
        ("skill", ("Languages", "Go")), ("skill", ("Data", "SQL")), ("t", "PROFESSIONAL EXPERIENCE"), ("t", "Job"),
    ], skills_runs=runs)
    d, _ = cb._apply_cv(jp.load_profile(workspace), {"skills": [["Languages", "Rust"]]}, 0)
    texts = [p.text for p in d.paragraphs]
    assert "Languages: Rust" in texts and not any(t.startswith("Data:") for t in texts)


def test_empty_title_paragraph_and_short_cv_give_clean_errors(workspace):
    cv = workspace / "cv_base" / "base_cv.docx"
    build_cv_doc(cv, [("t", "ONLY"), ("t", "TWO")])
    with pytest.raises(SystemExit, match="at least three"):
        cb.cv_map(jp.load_profile(workspace), docx.Document(str(cv)).paragraphs)
    p = docx.Document().add_paragraph()           # no runs at all
    cb.settext(p, "filled")
    assert p.text == "filled"


def test_missing_heading_message_names_the_keyword(workspace):
    cv = workspace / "cv_base" / "base_cv.docx"
    build_cv_doc(cv, HEADER + [("t", "PROFESSIONAL SUMMARY"), ("t", "Summary."), ("t", "PROFESSIONAL EXPERIENCE")])
    with pytest.raises(SystemExit, match="SKILLS"):
        cb.cv_map(jp.load_profile(workspace), docx.Document(str(cv)).paragraphs)


def test_em_dash_checked_in_every_spec_field_and_file_names_are_plain(workspace):
    prof = jp.load_profile(workspace)
    dash = chr(0x2014)
    with pytest.raises(SystemExit, match="Em dash"):
        cb._check_text(prof, *cb._strings({"letter": {"closing": f"Best {dash} Alex"}, "cv": {"keywords": [f"a{dash}b"]}}))
    for bad in ["../x", "/abs/x", "a/b", "..", ""]:
        with pytest.raises(SystemExit, match="file_name"):
            cb._safe_name(bad)
    assert cb._safe_name("Alex-Example-CV") == "Alex-Example-CV"


def test_to_pdf_reports_failures_and_removes_stale_output(tmp_path, monkeypatch):
    docx_path = tmp_path / "x.docx"
    docx_path.write_text("x")
    stale = tmp_path / "x.pdf"
    stale.write_text("old build")

    class Result:
        returncode, stdout, stderr = 7, "", "boom"
    monkeypatch.setattr(cb.subprocess, "run", lambda *a, **k: Result())
    with pytest.raises(RuntimeError, match="exit 7.*boom"):
        cb.to_pdf(str(docx_path), str(tmp_path))
    assert not stale.exists()                                   # a stale PDF can never pass for a fresh one

    def hang(*a, **k):
        raise subprocess.TimeoutExpired(cmd="soffice", timeout=1)
    monkeypatch.setattr(cb.subprocess, "run", hang)
    with pytest.raises(RuntimeError, match="did not finish"):
        cb.to_pdf(str(docx_path), str(tmp_path), timeout=1)

    def missing(*a, **k):
        raise FileNotFoundError("soffice")
    monkeypatch.setattr(cb.subprocess, "run", missing)
    with pytest.raises(RuntimeError, match="not found"):
        cb.to_pdf(str(docx_path), str(tmp_path))


# ---------------------------------------------------------------- init_workspace
ANSWERS = {
    "full_name": "Alex Example", "email": "alex@example.com", "roles": ["Senior Backend Engineer"],
    "locations": [{"place": "remote", "modes": ["remote"]}], "currency": "EUR",
    "floor_gross": 20000, "languages": [{"language": "English", "level": "C1"}],
}


def init(tmp_path, target, answers=ANSWERS, cv=None, market="generic", role="backend"):
    a = tmp_path / "answers.json"
    a.write_text(json.dumps(answers))
    cmd = [PYTHON, str(SCRIPTS / "init_workspace.py"), "--target", str(target), "--answers", str(a),
           "--market", market, "--role", role]
    if cv:
        cmd += ["--cv", str(cv)]
    return subprocess.run(cmd, capture_output=True, text=True)


def test_init_failure_keeps_a_directory_the_user_made(tmp_path):
    t = tmp_path / "mine"
    t.mkdir()
    bad = dict(ANSWERS, languages=[{"language": "English", "level": "fluent"}])
    r = init(tmp_path, t, answers=bad)
    assert r.returncode != 0
    assert t.exists() and list(t.iterdir()) == []


def test_init_validates_cv_before_writing_anything(tmp_path):
    t = tmp_path / "ws"
    r = init(tmp_path, t, cv=tmp_path / "missing.docx")
    assert r.returncode != 0 and ".docx" in r.stderr and not t.exists()
    # a retry with a good CV then works
    cv = tmp_path / "cv.docx"
    make_base_cv(cv)
    assert init(tmp_path, t, cv=cv).returncode == 0


def test_init_rejects_bad_preset_names(tmp_path):
    r = init(tmp_path, tmp_path / "ws", market="../evil")
    assert r.returncode != 0 and "Invalid" in r.stderr and not (tmp_path / "ws").exists()


def test_init_tracker_uses_profile_columns(tmp_path):
    t = tmp_path / "ws"
    assert init(tmp_path, t).returncode == 0
    headers = [c.value for c in openpyxl.load_workbook(t / "applications-tracker.xlsx")["Pipeline"][1]]
    assert headers == jp.load_profile(t).tracker_columns


# ---------------------------------------------------------------- tracker_query
def tracker_with(ws, rows):
    f = ws / "applications-tracker.xlsx"
    wb = openpyxl.load_workbook(f)
    sheet = wb["Pipeline"]
    for r in rows:
        sheet.append(r)
    wb.save(f)


def row(company, role="Dev", status="APPLIED", score=70, applied=None, updated=None):
    old = (dt.date.today() - dt.timedelta(days=15)).isoformat()
    return [None, company, role, "board", status, score, "", applied or old, None, None, None, None, None, "", "", updated or old]


def query(ws, *args):
    return run("tracker_query.py", ws, *args)


def test_company_match_is_by_whole_words(workspace):
    tracker_with(workspace, [row("Google"), row("Acme Labs")])
    assert "Google" not in query(workspace, "match", "Go").stdout
    assert "Acme Labs" in query(workspace, "match", "Acme").stdout


def test_renamed_statuses_work_through_status_roles(workspace):
    edit_profile(workspace, lambda d: d["tracker"].update({
        "statuses": [{"name": "Submitted"}, {"name": "Done"}],
        "status_roles": {"open_for_followup": ["Submitted"], "replied": ["Done"], "interview": ["Done"], "offer": ["Done"]}}))
    tracker_with(workspace, [row("Globex", status="Submitted")])
    r = query(workspace, "quiet", "--days", "10")
    assert "Globex" in r.stdout


def test_empty_and_missing_trackers_do_not_crash(workspace):
    f = workspace / "applications-tracker.xlsx"
    wb = openpyxl.Workbook()
    wb.active.title = "Pipeline"                      # sheet exists but has no rows at all
    wb.save(f)
    r = query(workspace, "match", "Acme")
    assert r.returncode == 0 and "Traceback" not in r.stderr
    f.unlink()
    r = query(workspace, "quiet")
    assert r.returncode == 1 and "No tracker" in r.stdout and "Traceback" not in r.stderr


def test_archive_without_the_sheet_is_skipped_with_a_message(workspace):
    other = openpyxl.Workbook()
    other.active.title = "Other"
    other.save(workspace / "old.xlsx")
    edit_profile(workspace, lambda d: d["tracker"].__setitem__("archives", ["old.xlsx"]))
    r = query(workspace, "match", "Acme")
    assert r.returncode == 0 and "no sheet named" in r.stderr and "Traceback" not in r.stderr


# ---------------------------------------------------------------- restyle_tracker
def test_restyle_carries_links_comments_and_formats_with_their_rows(workspace):
    f = workspace / "applications-tracker.xlsx"
    wb = openpyxl.load_workbook(f)
    ws = wb["Pipeline"]
    hdr = [c.value for c in ws[1]]
    folder, status, applied = hdr.index("Folder") + 1, hdr.index("Status") + 1, hdr.index("Applied") + 1
    # make_tracker rows: BACKLOG(2), APPLIED(3), OFFER(4), REJECTED(5): sorting reorders them
    ws.cell(row=4, column=folder).hyperlink = "https://example.com/offer"
    ws.cell(row=4, column=folder).value = "offer-folder"
    ws.cell(row=4, column=folder).comment = Comment("offer note", "me")
    ws.cell(row=4, column=applied).value = dt.datetime(2026, 1, 2)
    ws.cell(row=4, column=applied).number_format = "yyyy-mm-dd"
    wb.save(f)
    assert run("restyle_tracker.py", workspace).returncode == 0
    ws = openpyxl.load_workbook(f)["Pipeline"]
    first = [c for c in ws[2]]
    assert first[status - 1].value == "OFFER"                                  # sorted to the top
    assert first[folder - 1].hyperlink.target == "https://example.com/offer"   # link moved with its row
    assert first[folder - 1].comment.text == "offer note"
    assert first[applied - 1].number_format == "yyyy-mm-dd"
    assert ws.cell(row=3, column=folder).hyperlink is None                     # and left the old row


def test_restyle_stops_cleanly_on_missing_required_column(workspace):
    f = workspace / "applications-tracker.xlsx"
    wb = openpyxl.load_workbook(f)
    ws = wb["Pipeline"]
    ws.cell(row=1, column=[c.value for c in ws[1]].index("Status") + 1).value = "State"
    wb.save(f)
    before = f.read_bytes()
    r = run("restyle_tracker.py", workspace)
    assert r.returncode == 1 and "missing required column" in r.stderr and "Traceback" not in r.stderr
    assert f.read_bytes() == before and not (workspace / "_backup").exists()


def test_restyle_parses_datetime_strings(workspace):
    tracker_with(workspace, [row("Newer", status="APPLIED", updated="2026-11-20 00:00:00"),
                             row("Older", status="APPLIED", updated="2026-01-01")])
    assert run("restyle_tracker.py", workspace).returncode == 0
    ws = openpyxl.load_workbook(workspace / "applications-tracker.xlsx")["Pipeline"]
    applied = [r[1] for r in ws.iter_rows(min_row=2, values_only=True) if r[4] == "APPLIED"]
    assert applied.index("Newer") < applied.index("Older")


# ---------------------------------------------------------------- cleanup
def test_cleanup_only_removes_real_unpacked_office_dirs(workspace):
    real = workspace / "acme-2026-01-01" / "unpacked"
    (real / "word").mkdir(parents=True)
    (real / "[Content_Types].xml").write_text("<x/>")
    user_data = workspace / "globex-2026-01-01" / "unpacked"
    user_data.mkdir(parents=True)
    (user_data / "offer.txt").write_text("keep me")
    link = workspace / "link-2026-01-01"
    link.mkdir()
    (link / "unpacked").symlink_to(real)
    r = run("cleanup.py", workspace, "--execute")
    assert r.returncode == 0, r.stderr + r.stdout
    assert not real.exists() and (user_data / "offer.txt").exists()
    assert (link / "unpacked").is_symlink()                      # symlinks are never followed or deleted


# ---------------------------------------------------------------- netcalc
def test_netcalc_reports_incomplete_health_tiers(workspace):
    edit_profile(workspace, lambda d: d.update({
        "presets": {"role": "backend", "market": "poland"},
        "compensation": {"currency": "PLN", "floor_gross": 20000},
        "market_params": {"poland": {"jdg_ryczalt": {"rate": 0.12, "zus_monthly": 1000, "accounting_monthly": 0,
                                                     "health_deductible_share": 0.5,
                                                     "health_monthly": [{"up_to": 1, "amount": 10}]}}}}))
    r = run("netcalc.py", workspace, "20000", "--structure", "jdg")
    assert r.returncode != 0 and "up_to: null" in r.stderr and "Traceback" not in r.stderr


def test_netcalc_warns_when_structure_is_ignored(workspace):
    edit_profile(workspace, lambda d: d.__setitem__("market_params", {"generic_flat": {"effective_deduction_rate": 0.3}}))
    r = run("netcalc.py", workspace, "1000", "--structure", "jdg")
    assert "ignored" in r.stderr and "700" in r.stdout


# ---------------------------------------------------------------- verify scripts
def pdf_with_pages(path: Path, n: int, text="Hello demo"):
    """A minimal valid PDF with n pages that each carry a text layer."""
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>"]
    kids = " ".join(f"{3 + 2 * i} 0 R" for i in range(n))
    objs.append(f"<< /Type /Pages /Kids [{kids}] /Count {n} >>".encode())
    font_id = 3 + 2 * n
    for i in range(n):
        content_id = 4 + 2 * i
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents {content_id} 0 R "
                    f"/Resources << /Font << /F1 {font_id} 0 R >> >> >>".encode())
        stream = f"BT /F1 12 Tf 72 700 Td ({text}) Tj ET".encode()
        objs.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n{0:010d} 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.write_bytes(bytes(out))


def test_verify_pdf_max_pages(tmp_path):
    p = tmp_path / "x.pdf"
    pdf_with_pages(p, 3)
    r = subprocess.run([PYTHON, str(SCRIPTS / "verify_pdf.py"), str(p), "--max-pages", "2"], capture_output=True, text=True)
    assert r.returncode == 1 and "at most 2" in r.stderr
    pdf_with_pages(p, 1)
    r = subprocess.run([PYTHON, str(SCRIPTS / "verify_pdf.py"), str(p), "--max-pages", "2"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr        # one page is within the limit


def test_verify_layout_exit_codes_distinguish_bad_invocation_from_no_extractor(tmp_path):
    p = tmp_path / "x.pdf"
    pdf_with_pages(p, 1)
    no_poppler = dict(os.environ, PATH=str(tmp_path))            # nothing on PATH: no pdftotext
    r = subprocess.run([PYTHON, str(SCRIPTS / "verify_layout.py"), str(p)], capture_output=True, text=True, env=no_poppler)
    assert r.returncode == 3 and "skipped" in r.stderr
    r = subprocess.run([PYTHON, str(SCRIPTS / "verify_layout.py"), str(tmp_path / "missing.pdf")], capture_output=True, text=True)
    assert r.returncode == 2 and "not found" in r.stderr


# ---------------------------------------------------------------- second review round
def cv_paragraphs(path, lines):
    """lines: (text, style) with style in plain | bold | heading."""
    d = docx.Document()
    for text, style in lines:
        if style == "heading":
            d.add_paragraph(text, style="Heading 1")
        else:
            p = d.add_paragraph()
            p.add_run(text).bold = style == "bold"
    d.save(path)
    return docx.Document(str(path)).paragraphs


H3 = [("ALEX EXAMPLE", "plain"), ("Engineer", "plain"), ("alex@example.com", "plain")]


def test_real_heading_beats_a_short_body_line_containing_the_keyword(workspace):
    P = cv_paragraphs(workspace / "x.docx", H3 + [
        ("PROFESSIONAL SUMMARY", "plain"), ("Summary.", "plain"),
        ("PROFESSIONAL EXPERIENCE", "plain"), ("Strong SQL skills", "plain"), ("Did things.", "plain"),
        ("TECHNICAL SKILLS", "plain"), ("Languages: Go", "plain")])
    m = cb.cv_map(jp.load_profile(workspace), P)
    assert P[m["skills_heading"]].text == "TECHNICAL SKILLS"
    assert [P[i].text for i in m["skills"]] == ["Languages: Go"]


def test_plain_title_case_heading_is_used_when_nothing_better_exists(workspace):
    P = cv_paragraphs(workspace / "x.docx", H3 + [
        ("PROFESSIONAL SUMMARY", "plain"), ("Summary.", "plain"), ("Technical skills", "plain"),
        ("Languages: Go", "plain"), ("PROFESSIONAL EXPERIENCE", "plain"), ("Job", "plain")])
    m = cb.cv_map(jp.load_profile(workspace), P)
    assert P[m["skills_heading"]].text == "Technical skills"


@pytest.mark.parametrize("line", ["GO, PYTHON, SQL", "PYTHON | GO | SQL", "AWS/GCP/AZURE"])
def test_all_caps_skills_lines_do_not_end_the_skills_block(workspace, line):
    P = cv_paragraphs(workspace / "x.docx", H3 + [
        ("PROFESSIONAL SUMMARY", "plain"), ("Summary.", "plain"), ("TECHNICAL SKILLS", "plain"),
        (line, "plain"), ("Data: Postgres", "plain"), ("PROFESSIONAL EXPERIENCE", "plain"), ("Job", "plain")])
    m = cb.cv_map(jp.load_profile(workspace), P)
    assert [P[i].text for i in m["skills"]] == [line, "Data: Postgres"]


@pytest.mark.parametrize("style", ["bold", "heading"])
def test_bold_or_styled_headings_end_the_skills_block(workspace, style):
    P = cv_paragraphs(workspace / "x.docx", H3 + [
        ("PROFESSIONAL SUMMARY", "plain"), ("Summary.", "plain"), ("PROFESSIONAL EXPERIENCE", "plain"), ("Job", "plain"),
        ("TECHNICAL SKILLS", "plain"), ("Languages: Go", "plain"), ("Education", style), ("Some University", "plain")])
    m = cb.cv_map(jp.load_profile(workspace), P)
    assert [P[i].text for i in m["skills"]] == ["Languages: Go"]


def test_other_headings_setting_ends_the_block_for_plain_headings(workspace):
    lines = H3 + [("PROFESSIONAL SUMMARY", "plain"), ("Summary.", "plain"), ("PROFESSIONAL EXPERIENCE", "plain"),
                  ("Job", "plain"), ("TECHNICAL SKILLS", "plain"), ("Languages: Go", "plain"),
                  ("Certifications", "plain"), ("Some Cert", "plain")]
    P = cv_paragraphs(workspace / "x.docx", lines)
    assert len(cb.cv_map(jp.load_profile(workspace), P)["skills"]) == 3          # swallowed without the setting
    edit_profile(workspace, lambda d: d.__setitem__("cv_map", {"other_headings": ["certification"]}))
    assert len(cb.cv_map(jp.load_profile(workspace), P)["skills"]) == 1


def test_overridden_statuses_need_matching_status_roles(workspace):
    edit_profile(workspace, lambda d: d["tracker"].__setitem__("statuses", [{"name": "Submitted"}, {"name": "Done"}]))
    with pytest.raises(jp.ProfileError, match="status_roles.*APPLIED"):
        jp.load_profile(workspace)                                                # roles fall back to defaults that do not exist
    edit_profile(workspace, lambda d: d["tracker"].__setitem__("status_roles", {"open_for_followup": ["Missing"]}))
    with pytest.raises(jp.ProfileError, match="Missing"):
        jp.load_profile(workspace)
    edit_profile(workspace, lambda d: d["tracker"].__setitem__("status_roles", {"open_for_followup": ["Submitted"]}))
    assert jp.load_profile(workspace)["tracker"]["status_roles"]["open_for_followup"] == ["Submitted"]


def test_overriding_statuses_with_the_default_names_needs_no_roles(workspace):
    defaults = [{"name": n} for n in ["APPLIED", "CV SENT", "SCREENING", "INTERVIEW", "OFFER"]]
    edit_profile(workspace, lambda d: d["tracker"].__setitem__("statuses", defaults))
    jp.load_profile(workspace)


def test_one_word_names_are_not_doubled(workspace):
    edit_profile(workspace, lambda d: d["identity"].__setitem__("full_name", "Madonna"))
    assert jp.load_profile(workspace).output_stem("acme", "CV") == "Madonna-acme-CV"


def test_restyle_needs_only_the_columns_it_uses(workspace):
    f = workspace / "applications-tracker.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Pipeline"
    ws.append(["#", "Status", "Updated", "Notes"])
    ws.append([None, "BACKLOG", "2026-01-01", "a"])
    ws.append([None, "OFFER", "2026-02-01", "b"])
    wb.save(f)
    assert run("restyle_tracker.py", workspace).returncode == 0
    ws = openpyxl.load_workbook(f)["Pipeline"]
    assert [r[1] for r in ws.iter_rows(min_row=2, values_only=True)] == ["OFFER", "BACKLOG"]


def test_audit_survives_unreadable_index_entries_and_ignores_binary_noise(tmp_path):
    from test_privacy_audit import commit, make_repo, sh
    from test_privacy_audit import run as audit_run
    r = make_repo(tmp_path)
    commit(r, "a.md", "clean\n")
    (r / "icon.bin").write_bytes(b"\x89PNG\x00\x01" + b"mail jane" + b"@realmail.net 555-" + b"123-4567" + b"\xff\xfe")
    sh(r, "add", "-A")
    sh(r, "update-index", "--add", "--cacheinfo", "160000," + "1" * 40 + ",submod")      # a gitlink: no blob to read
    out = audit_run(r)
    assert "submod" in out.stdout and "cannot be read" in out.stdout and "Traceback" not in out.stderr
    assert "realmail" not in out.stdout and "phone-like" not in out.stdout                 # binary noise is not flagged
