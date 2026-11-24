import os
import subprocess
import sys
from pathlib import Path

import _deps
import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def test_ensure_is_noop_when_packages_present():
    assert _deps.missing() == []
    _deps.ensure()


def test_venv_dir_prefers_plugin_data(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
    assert _deps.venv_dir() == tmp_path / "venv"
    monkeypatch.delenv("CLAUDE_PLUGIN_DATA")
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    assert _deps.venv_dir() == tmp_path / "cache" / "jobsearch-harness" / "venv"


def test_ensure_stops_instead_of_looping_when_still_missing(monkeypatch):
    monkeypatch.setattr(_deps, "MODULES", ("definitely_not_installed_pkg",))
    monkeypatch.setenv(_deps.GUARD, "1")
    with pytest.raises(SystemExit) as e:
        _deps.ensure()
    assert "definitely_not_installed_pkg" in str(e.value)


def test_ensure_reports_setup_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(_deps, "MODULES", ("definitely_not_installed_pkg",))
    monkeypatch.delenv(_deps.GUARD, raising=False)
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
    monkeypatch.setattr(_deps, "REQUIREMENTS", tmp_path / "does-not-exist.txt")
    with pytest.raises(SystemExit) as e:
        _deps.ensure()
    assert "manually" in str(e.value)


@pytest.mark.parametrize("script", ["jobprofile.py", "restyle_tracker.py", "tracker_query.py", "init_workspace.py"])
def test_entry_scripts_run_with_help(script):
    r = subprocess.run([sys.executable, str(SCRIPTS / script), "--help"], capture_output=True, text=True,
                       env={**os.environ, _deps.GUARD: "1"})
    assert r.returncode == 0, r.stderr


MODULE_TO_PACKAGE = {"yaml": "pyyaml", "jsonschema": "jsonschema", "openpyxl": "openpyxl", "docx": "python-docx", "pypdf": "pypdf"}
DEV_ONLY = {"pytest"}


def _requirement_names(path):
    import re
    names = set()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith(("#", "-")):
            names.add(re.split(r"[<>=!~\[; ]", line, maxsplit=1)[0].lower())
    return names


def test_bootstrap_modules_match_requirements():
    """_deps.ensure() must check exactly the runtime packages in requirements.txt (pytest is dev-only)."""
    req = _requirement_names(SCRIPTS.parent / "requirements.txt") - DEV_ONLY
    assert set(_deps.MODULES) == set(MODULE_TO_PACKAGE), "update MODULE_TO_PACKAGE in this test with _deps.MODULES"
    assert {MODULE_TO_PACKAGE[m] for m in _deps.MODULES} == req


def test_dev_requirements_include_runtime_and_ruff():
    text = (SCRIPTS.parent / "requirements-dev.txt").read_text(encoding="utf-8")
    assert "-r requirements.txt" in text and "ruff" in text


def test_dev_setup_check_reports_state():
    r = subprocess.run([sys.executable, str(SCRIPTS / "dev_setup.py"), "--check"], capture_output=True, text=True)
    assert r.returncode in (0, 1)
    for key in ("venv", "ruff", "hooks_path", "hooks_executable"):
        assert key in r.stdout


def test_ensure_refuses_stdin_and_dash_c_scripts(monkeypatch):
    monkeypatch.setattr(_deps, "MODULES", ("definitely_not_installed_pkg",))
    monkeypatch.delenv(_deps.GUARD, raising=False)
    for argv0 in ("-", "-c", ""):
        monkeypatch.setattr(sys, "argv", [argv0])
        with pytest.raises(SystemExit) as e:
            _deps.ensure()
        assert "stdin" in str(e.value)
