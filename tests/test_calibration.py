import datetime as dt
import subprocess
import sys
from pathlib import Path

import openpyxl
import score_compare as sc
from lib import calibration as cal

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
ROLES = {"replied": ["SCREENING", "INTERVIEW", "OFFER"], "interview": ["INTERVIEW", "OFFER"], "offer": ["OFFER"]}


def test_wilson_interval_is_sane():
    lo, hi = cal.wilson(0, 0)
    assert (lo, hi) == (0.0, 0.0)
    lo, hi = cal.wilson(5, 50)
    assert 0.04 < lo < 0.10 < hi < 0.22
    lo, hi = cal.wilson(50, 50)
    assert hi == 1.0 and lo > 0.9


def _rows(spec):
    today = dt.date(2026, 11, 25)
    rows = []
    for score, n, replied, age in spec:
        for i in range(n):
            rows.append({"Match %": score, "Applied": (today - dt.timedelta(days=age)).isoformat(),
                         "Status": "SCREENING" if i < replied else "APPLIED"})
    return rows, today


def _band(s):
    return "<60" if s < 60 else "60-74" if s < 75 else "75+"


def test_band_stats_skip_recent_and_count_replies():
    rows, today = _rows([(50, 40, 2, 30), (80, 40, 20, 30), (80, 10, 10, 3)])
    stats, recent = cal.band_stats(rows, _band, ROLES, today, 14, lambda v: float(v), lambda v: dt.date.fromisoformat(v))
    assert recent == 10 and stats["<60"]["n"] == 40 and stats["75+"]["replied"] == 20


def test_verdict_detects_separation_and_small_samples():
    rows, today = _rows([(50, 60, 3, 30), (80, 60, 30, 30)])
    stats, _ = cal.band_stats(rows, _band, ROLES, today, 14, float, dt.date.fromisoformat)
    text = " ".join(cal.verdict(["<60", "60-74", "75+"], stats))
    assert "replies more often" in text and "thresholds are doing work" in text
    flat_rows, _ = _rows([(50, 60, 6, 30), (80, 60, 7, 30)])
    flat, _ = cal.band_stats(flat_rows, _band, ROLES, today, 14, float, dt.date.fromisoformat)
    assert "does not yet predict" in " ".join(cal.verdict(["<60", "60-74", "75+"], flat))
    tiny_rows, _ = _rows([(50, 5, 1, 30)])
    tiny, _ = cal.band_stats(tiny_rows, _band, ROLES, today, 14, float, dt.date.fromisoformat)
    assert "too few" in " ".join(cal.verdict(["<60", "60-74", "75+"], tiny))


def test_calibrate_cli_runs_on_the_fixture_tracker(workspace):
    p = workspace / "applications-tracker.xlsx"
    wb = openpyxl.load_workbook(p)
    ws = wb["Pipeline"]
    head = [c.value for c in ws[1]]
    for i in range(40):
        row = {h: None for h in head}
        row.update({"Company": f"Co{i}", "Role": "Dev", "Status": "SCREENING" if i % 4 == 0 else "APPLIED", "Match %": 70,
                    "Applied": (dt.date.today() - dt.timedelta(days=40)).isoformat(), "Updated": dt.date.today().isoformat()})
        ws.append([row[h] for h in head])
    wb.save(p)
    r = subprocess.run([sys.executable, str(SCRIPTS / "tracker_query.py"), "--workspace", str(workspace), "calibrate"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "replied (95% interval)" in r.stdout and "Fewer than two bands" in r.stdout


ANALYSIS = """# JD Analysis
| Dimension | Weight | Score | Note |
|---|---|---|---|
| Technical Skills Match | 30% | {t} | x |
| Experience Match | 20% | 70 | x |
| Behavioral/Culture Fit | 10% | 60 | x |
| Career Alignment | 25% | 80 | x |
| Compensation | 15% | 90 | x |

**Overall Score: {o}** - Good Fit
"""
NEW_STYLE = """| Technical | 0.30 | 64 | x |
| Experience | 0.20 | 66 | x |
| Culture | 0.10 | 62 | x |
| Career | 0.25 | 78 | x |
| Compensation | 0.15 | 90 | x |
**Overall Score: 72** - Good
"""


def test_parse_reads_both_table_styles():
    old = sc.parse(ANALYSIS.format(t=80, o=82))
    assert old == {"overall": 82.0, "Technical": 80.0, "Experience": 70.0, "Culture": 60.0, "Career": 80.0, "Compensation": 90.0}
    new = sc.parse(NEW_STYLE)
    assert new["Technical"] == 64.0 and new["Culture"] == 62.0 and new["overall"] == 72.0


def test_cli_prints_mean_spread_and_delta(tmp_path):
    ref = tmp_path / "ref.md"
    ref.write_text(ANALYSIS.format(t=80, o=82))
    runs = []
    for i, (t, o) in enumerate([(64, 72), (66, 73), (65, 72)]):
        f = tmp_path / f"r{i}.md"
        f.write_text(ANALYSIS.format(t=t, o=o))
        runs.append(str(f))
    r = subprocess.run([sys.executable, str(SCRIPTS / "score_compare.py"), "--reference", str(ref), *runs], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "mean 72.3" in r.stdout and "-9.7" in r.stdout and "Technical" in r.stdout
