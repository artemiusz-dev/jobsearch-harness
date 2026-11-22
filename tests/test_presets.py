import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import jobprofile as jp

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
ROLES = sorted(p.stem for p in (ROOT / "presets" / "roles").glob("*.yaml"))
MARKETS = sorted(p.stem for p in (ROOT / "presets" / "markets").glob("*.yaml"))

BASE = {
    "schema_version": 1,
    "identity": {"full_name": "Alex Example", "email": "alex@example.com"},
    "targets": {"roles": ["Example Role"]},   # the generic role pack deliberately invents no roles
    "locations": {"accepted": [{"place": "remote", "modes": ["remote"]}]},
    "languages": {"spoken": [{"language": "English", "level": "C1"}]},
    "compensation": {"currency": "EUR", "floor_gross": 1000},
    "scoring": {"weights": {"technical": 0.3, "experience": 0.2, "culture": 0.1, "career": 0.25, "compensation": 0.15},
                "thresholds": {"strong": 75, "good": 60, "moderate": 45, "weak": 30}},
    "tracker": {"sheet": "Pipeline"},
}


def make(tmp_path, role, market):
    d = dict(BASE)
    d["presets"] = {"role": role, "market": market}
    (tmp_path / "profile.yaml").write_text(yaml.safe_dump(d))
    return tmp_path


def test_presets_exist():
    assert {"frontend", "generic", "backend", "data", "pm"} <= set(ROLES)
    assert {"generic", "poland"} <= set(MARKETS)


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("market", MARKETS)
def test_every_role_market_combo_loads(tmp_path, role, market):
    p = jp.load_profile(make(tmp_path, role, market))
    assert p["targets"]["roles"]
    assert p["rubric_hints"]["technical"]


@pytest.mark.parametrize("market", MARKETS)
def test_market_has_salary_doc(market):
    assert (ROOT / "presets" / "markets" / f"{market}.md").exists()


def run_netcalc(ws, *args):
    return subprocess.run([sys.executable, str(SCRIPTS / "netcalc.py"), "--workspace", str(ws), *args],
                          capture_output=True, text=True)


def test_poland_eor_and_jdg_match_reference_formulas(tmp_path):
    ws = make(tmp_path, "frontend", "poland")
    f = ws / "profile.yaml"
    d = yaml.safe_load(f.read_text())
    d["compensation"]["currency"] = "PLN"
    f.write_text(yaml.safe_dump(d))
    r = run_netcalc(ws, "22000", "--structure", "eor")
    assert "20,256" in r.stdout, r.stdout + r.stderr
    r = run_netcalc(ws, "22000", "--structure", "jdg")
    assert "16,58" in r.stdout, r.stdout + r.stderr


def test_poland_uop_points_to_calculator(tmp_path):
    r = run_netcalc(make(tmp_path, "frontend", "poland"), "22000", "--structure", "uop")
    assert "official calculator" in r.stdout


def test_generic_flat_needs_a_rate(tmp_path):
    r = run_netcalc(make(tmp_path, "generic", "generic"), "1000")
    assert r.returncode != 0 and "effective_deduction_rate" in (r.stdout + r.stderr)


def test_generic_flat_with_rate(tmp_path):
    ws = make(tmp_path, "generic", "generic")
    f = ws / "profile.yaml"
    d = yaml.safe_load(f.read_text())
    d["market_params"] = {"generic_flat": {"effective_deduction_rate": 0.3}}
    f.write_text(yaml.safe_dump(d))
    assert "700" in run_netcalc(ws, "1000").stdout
