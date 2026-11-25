"""The profile is the single source of truth for personal rules: new sections validate, default in one place and reject typos."""
import shutil
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import jobprofile as jp  # noqa: E402


def ws(tmp_path, extra=None):
    data = yaml.safe_load((ROOT / "config" / "profile.example.yaml").read_text(encoding="utf-8"))
    for k, v in (extra or {}).items():
        data[k] = jp.deep_merge(data.get(k, {}), v) if isinstance(v, dict) else v
    (tmp_path / "profile.yaml").write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return tmp_path


def test_defaults_come_from_the_schema_only(tmp_path):
    p = jp.load_profile(ws(tmp_path))
    assert p.limit("dm_sentences") == 3 and p.limit("followup_words") == [60, 120]
    assert p["followups"]["history_window_days"] == 60 and p["followups"]["draft_only"] is True
    assert p["cv"]["paper"] == "A4" and p["letter"]["closing"] == "Best regards,"
    assert "greenhouse.io" in p["security"]["trusted_ats_domains"]
    assert p.default_new_status == "To Apply"
    assert p.status_role("closed") == ["SKIP", "REJECTED", "WITHDRAWN"]


def test_actively_exploring_is_banned_everywhere_by_default(tmp_path):
    assert "actively exploring new opportunities" in jp.load_profile(ws(tmp_path)).banned_phrases()


def test_banned_list_is_replaced_not_appended_and_channels_extend(tmp_path):
    p = jp.load_profile(ws(tmp_path, {"style": {"banned_phrases": ["Synergy"], "channel_banned_phrases": {"dm": ["Worth discussing?"]}}}))
    assert p.banned_phrases() == ["synergy"]
    assert p.banned_phrases("dm") == ["synergy", "worth discussing?"]


def test_per_status_followup_windows_and_marker(tmp_path):
    p = jp.load_profile(ws(tmp_path, {"followups": {"by_status": {"SCREENING": {"first_after_days": 4}}, "marker": "fup {date}"}}))
    assert p.followup_days("SCREENING") == (4, 14)
    assert p.followup_days("APPLIED") == (7, 14)
    assert p.followup_marker("2026-01-02") == "fup 2026-01-02"


@pytest.mark.parametrize("extra,needle", [
    ({"followups": {"by_status": {"NOPE": {"first_after_days": 3}}}}, "by_status"),
    ({"followups": {"marker": "followed up"}}, "marker"),
    ({"tracker": {"default_new_status": "NOPE"}}, "default_new_status"),
    ({"tracker": {"columns": ["Company", "Status"], "stages": [{"column": "Intro Call"}]}}, "stages"),
    ({"scoring": {"depth_risk_penalty": {"min": 9, "max": 3}}}, "depth_risk_penalty"),
    ({"referral": {"contacts_file": "../x.txt"}}, "contacts_file"),
])
def test_cross_field_errors(tmp_path, extra, needle):
    with pytest.raises(jp.ProfileError, match=needle):
        jp.load_profile(ws(tmp_path, extra))


def test_unknown_keys_in_new_sections_are_rejected(tmp_path):
    with pytest.raises(jp.ProfileError):
        jp.load_profile(ws(tmp_path, {"style": {"limits": {"dm_sentence": 2}}}))
    with pytest.raises(jp.ProfileError):
        jp.load_profile(ws(tmp_path, {"cv": {"papper": "A4"}}))


def test_company_lists_gates_modifiers_and_tracks_validate(tmp_path):
    p = jp.load_profile(ws(tmp_path, {
        "targets": {"companies": {"blacklist": ["Acme"], "never_contact": ["Globex"]},
                    "search_tracks": [{"id": "fs", "tag": "[FS]", "roles": ["Senior Fullstack Engineer"], "countries": ["PL", "PT"]}]},
        "scoring": {"gates": {"custom": [{"name": "on-call", "match": ["24/7 on-call"], "action": "flag"}]},
                    "modifiers": [{"when": ["fintech"], "dimension": "career", "delta": 5}]}}))
    assert p["targets"]["companies"]["blacklist"] == ["Acme"]
    assert p["scoring"]["modifiers"][0]["delta"] == 5


def test_example_profile_stays_valid():
    d = Path(__file__).parent
    tmp = d / "_ws_example_tmp"
    tmp.mkdir(exist_ok=True)
    try:
        shutil.copy(ROOT / "config" / "profile.example.yaml", tmp / "profile.yaml")
        jp.load_profile(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
