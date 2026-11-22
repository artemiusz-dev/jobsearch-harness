import pytest
import yaml

import jobprofile as jp


def test_example_loads_with_presets_and_defaults(workspace):
    p = jp.load_profile(workspace)
    assert p.currency == "EUR"
    assert p.salary_column == "Salary (EUR gross)"
    assert p["followups"]["stale_after_days"] == 60          # default from schema
    assert p.band_edges == (45, 60, 75)


def test_user_values_beat_presets(workspace):
    p = jp.load_profile(workspace)
    assert p["targets"]["exclude_keywords"] == ["intern", "junior"]   # profile overrides backend preset


def test_weights_must_sum_to_one(workspace):
    f = workspace / "profile.yaml"
    d = yaml.safe_load(f.read_text())
    d["scoring"]["weights"]["technical"] = 0.5
    f.write_text(yaml.safe_dump(d))
    with pytest.raises(jp.ProfileError, match="sum to 1.0"):
        jp.load_profile(workspace)


def test_thresholds_must_descend(workspace):
    f = workspace / "profile.yaml"
    d = yaml.safe_load(f.read_text())
    d["scoring"]["thresholds"]["good"] = 80
    f.write_text(yaml.safe_dump(d))
    with pytest.raises(jp.ProfileError, match="descending"):
        jp.load_profile(workspace)


def test_absolute_paths_rejected(workspace):
    f = workspace / "profile.yaml"
    d = yaml.safe_load(f.read_text())
    d["paths"]["tracker"] = "/abs/tracker.xlsx"
    f.write_text(yaml.safe_dump(d))
    with pytest.raises(jp.ProfileError, match="workspace-relative"):
        jp.load_profile(workspace)


def test_missing_workspace_errors(tmp_path, monkeypatch):
    monkeypatch.delenv("JOBSEARCH_WORKSPACE", raising=False)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(jp.ProfileError):
        jp.load_profile()


def test_output_stem(workspace):
    p = jp.load_profile(workspace)
    assert p.output_stem("acme", "CV") == "Alex-Example-acme-CV"
