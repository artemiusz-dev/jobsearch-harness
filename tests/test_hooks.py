import subprocess
import sys
from pathlib import Path

import check_commit_msg as ccm

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
HOOKS = Path(__file__).resolve().parent.parent / ".githooks"


def test_clean_conventional_message_passes():
    problems, notes = ccm.check("fix(build): keep the DOCX when soffice is missing\n\nBody text.\n")
    assert problems == [] and notes == []


def test_free_form_subject_is_only_a_note():
    problems, notes = ccm.check("Fix CI: pin runner.\n")
    assert problems == [] and len(notes) == 2


def test_empty_and_comment_only_messages_fail():
    assert ccm.check("")[0] == ["empty commit message"]
    assert ccm.check("# Please enter the commit message\n# more\n")[0] == ["empty commit message"]


def test_long_subject_fails():
    problems, _ = ccm.check("fix: " + "x" * 80)
    assert any("max 72" in p for p in problems)


def test_privacy_patterns_in_message_fail():
    home = "/" + "Users/someone/project"
    assert any("home path" in p for p in ccm.check(f"fix: read {home}\n")[0])
    email = "jane@" + "realcompany.net"          # built at runtime so the repository audit sees no real-looking data
    phone = "+48 " + "111 222 333"
    assert any("email" in p for p in ccm.check(f"fix: contact {email}\n")[0])
    assert any("phone" in p for p in ccm.check(f"fix: call {phone}\n")[0])


def test_trailers_skip_generic_checks_but_not_denylist(tmp_path):
    deny = tmp_path / "deny.txt"
    deny.write_text("secretclient\n", encoding="utf-8")
    ok = "fix: tidy\n\nCo-Authored-By: Claude <noreply@" + "anthropic.com>\n"
    assert ccm.check(ok, deny)[0] == []
    bad = "fix: tidy\n\nCo-Authored-By: secretclient person\n"
    assert any("denylist" in p for p in ccm.check(bad, deny)[0])
    assert any("denylist" in p for p in ccm.check("fix: work for secretclient\n", deny)[0])


def test_merge_subject_skips_style_notes():
    assert ccm.check("Merge branch 'main' into feature\n") == ([], [])


def test_cli_exit_codes(tmp_path):
    good, bad = tmp_path / "good", tmp_path / "bad"
    good.write_text("docs: update readme\n", encoding="utf-8")
    bad.write_text("docs: " + "y" * 90 + "\n", encoding="utf-8")
    run = lambda f: subprocess.run([sys.executable, str(SCRIPTS / "check_commit_msg.py"), str(f)], capture_output=True, text=True)  # noqa: E731
    assert run(good).returncode == 0
    assert run(bad).returncode == 1


def test_hook_files_are_executable_and_fail_closed():
    for name in ("pre-commit", "commit-msg", "pre-push"):
        h = HOOKS / name
        assert h.exists(), name
        assert h.stat().st_mode & 0o111, f"{name} is not executable"
        assert "set -euo pipefail" in h.read_text(encoding="utf-8"), f"{name} must fail closed"
