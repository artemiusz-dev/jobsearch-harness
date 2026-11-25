"""Every tracker script must follow a profile that renames every column, stage and status (no hardcoded names)."""
import datetime as dt
import subprocess
import sys
from pathlib import Path

import openpyxl
import yaml

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"

FIELDS = {"number": "No", "company": "Firma", "role": "Stanowisko", "source": "Zrodlo", "status": "Etap", "match": "Dopasowanie",
          "applied": "Wyslano", "outcome": "Wynik", "next_action": "Dalej", "folder": "Katalog", "updated": "Zmiana"}
STAGES = [{"column": "Rozmowa 1", "role": "screen"}, {"column": "Zadanie", "role": "assignment"},
          {"column": "Rozmowa tech", "role": "interview"}, {"column": "Rozmowa koncowa", "role": "final"}]
STATUSES = [{"name": "OFERTA"}, {"name": "ROZMOWA"}, {"name": "WYSLANE"}, {"name": "DO WYSLANIA"}, {"name": "ODRZUCONE", "dimmed": True}]


def setup(ws):
    f = ws / "profile.yaml"
    d = yaml.safe_load(f.read_text())
    d["tracker"] = {"sheet": "Pipeline", "salary_column": "Pensja", "fields": FIELDS, "stages": STAGES, "statuses": STATUSES,
                    "default_new_status": "DO WYSLANIA",
                    "status_roles": {"open_for_followup": ["WYSLANE"], "replied": ["ROZMOWA", "OFERTA"], "interview": ["ROZMOWA", "OFERTA"],
                                     "offer": ["OFERTA"], "closed": ["ODRZUCONE"], "in_progress": ["DO WYSLANIA"]}}
    d["followups"] = {"first_after_days": 7, "second_after_days": 14, "max_followups": 2, "marker": "kontakt {date}"}
    f.write_text(yaml.safe_dump(d), encoding="utf-8")
    old = (dt.date.today() - dt.timedelta(days=20)).isoformat()
    wb = openpyxl.Workbook()
    sh = wb.active
    sh.title = "Pipeline"
    head = [FIELDS["number"], FIELDS["company"], FIELDS["role"], FIELDS["source"], FIELDS["status"], FIELDS["match"], "Pensja",
            FIELDS["applied"], *[s["column"] for s in STAGES], FIELDS["outcome"], FIELDS["next_action"], FIELDS["folder"], FIELDS["updated"]]
    sh.append(head)
    row = {h: None for h in head}
    row.update({FIELDS["number"]: 1, FIELDS["company"]: "Globex Inc", FIELDS["role"]: "Platform", FIELDS["status"]: "WYSLANE",
                FIELDS["match"]: 70, FIELDS["applied"]: old, FIELDS["updated"]: old})
    sh.append([row[h] for h in head])
    wb.save(ws / "applications-tracker.xlsx")


def run(script, ws, *args):
    return subprocess.run([sys.executable, str(SCRIPTS / script), "--workspace", str(ws), *args], capture_output=True, text=True)


def test_query_scripts_follow_renamed_columns(workspace):
    setup(workspace)
    m = run("tracker_query.py", workspace, "match", "Globex")
    assert m.returncode == 0 and "Globex Inc" in m.stdout and "same company" in m.stdout, m.stdout + m.stderr
    q = run("tracker_query.py", workspace, "quiet")
    assert q.returncode == 0 and "Globex Inc" in q.stdout and "candidates" in q.stdout, q.stdout + q.stderr
    s = run("tracker_query.py", workspace, "summary")
    assert s.returncode == 0 and "WYSLANE" in s.stdout and "Rozmowa tech" in s.stdout, s.stdout + s.stderr
    assert run("tracker_query.py", workspace, "calibrate").returncode == 0
    assert run("tracker_query.py", workspace, "bands").returncode == 0


def test_add_update_and_restyle_follow_renamed_columns(workspace):
    setup(workspace)
    a = run("tracker_add.py", workspace, "add", "--company", "Initech", "--role", "SRE", "--match", "66")
    assert a.returncode == 0 and "DO WYSLANIA" in a.stdout, a.stdout + a.stderr          # default_new_status, not a hardcoded name
    u = run("tracker_add.py", workspace, "update", "--company", "Globex", "--status", "ROZMOWA", "--stage", "Rozmowa 1=2026-11-20",
            "--append-next-action", "kontakt 2026-11-21")
    assert u.returncode == 0, u.stdout + u.stderr
    ws = openpyxl.load_workbook(workspace / "applications-tracker.xlsx")["Pipeline"]
    head = [c.value for c in ws[1]]
    rows = {r[head.index("Firma")]: r for r in ws.iter_rows(min_row=2, values_only=True)}
    assert rows["Globex Inc"][head.index("Etap")] == "ROZMOWA" and rows["Initech"][head.index("Etap")] == "DO WYSLANIA"
    assert rows["Globex Inc"][head.index("Zmiana")] == dt.date.today().isoformat()
    assert run("restyle_tracker.py", workspace).returncode == 0


def test_followup_marker_counts_follow_ups(workspace):
    setup(workspace)
    run("tracker_add.py", workspace, "update", "--company", "Globex", "--append-next-action",
        f"kontakt {(dt.date.today() - dt.timedelta(days=2)).isoformat()}")
    q = run("tracker_query.py", workspace, "quiet")
    assert q.returncode == 0 and "Follow-up candidates (>= 7d quiet, < 2 follow-ups): 0" in q.stdout, q.stdout   # last contact 2 days ago


def test_per_status_window_overrides_the_global_one(workspace):
    setup(workspace)
    f = workspace / "profile.yaml"
    d = yaml.safe_load(f.read_text())
    d["followups"]["by_status"] = {"WYSLANE": {"first_after_days": 30}}
    f.write_text(yaml.safe_dump(d), encoding="utf-8")
    q = run("tracker_query.py", workspace, "quiet")
    assert "Follow-up candidates (>= 7d quiet, < 2 follow-ups): 0" in q.stdout, q.stdout         # applied 20 days ago, window is 30


def test_check_dm_follows_profile_limits_and_phrases(workspace):
    f = workspace / "profile.yaml"
    d = yaml.safe_load(f.read_text())
    d["style"] = {"limits": {"dm_sentences": 1}, "banned_phrases": ["nonsense phrase"], "forbid_em_dash": False}
    f.write_text(yaml.safe_dump(d), encoding="utf-8")
    two = run("check_dm.py", workspace, "Hi Sam, I build UIs. Any openings?")
    assert two.returncode == 1 and "max 1" in two.stdout
    banned = run("check_dm.py", workspace, "Hi Sam, a nonsense phrase here.")
    assert banned.returncode == 1 and "nonsense phrase" in banned.stdout
    dash = run("check_dm.py", workspace, "Hi Sam, one" + chr(0x2014) + "two.")
    assert dash.returncode == 0, dash.stdout                    # em dash allowed when the profile says so
