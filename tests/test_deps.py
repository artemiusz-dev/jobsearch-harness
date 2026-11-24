import os
import subprocess
import sys
from pathlib import Path

import pytest

import _deps

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
