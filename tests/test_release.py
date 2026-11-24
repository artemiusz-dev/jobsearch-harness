import json
import subprocess
import sys
from pathlib import Path

import pytest
import release as rel

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "release.py"


def sh(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    (r / ".claude-plugin").mkdir(parents=True)
    (r / ".claude-plugin" / "plugin.json").write_text(json.dumps({"name": "x", "version": "0.1.0"}, indent=2) + "\n")
    (r / "CHANGELOG.md").write_text("# Changelog\n\n## 0.2.0 - 2026-11-24\n- thing\n\n## 0.1.0 - 2026-11-01\n- first\n")
    sh(tmp_path, "init", "-q", "-b", "main", str(r))
    sh(r, "config", "user.email", "1+t@users.noreply.github.com")
    sh(r, "config", "user.name", "T")
    sh(r, "add", "-A")
    sh(r, "commit", "-q", "-m", "chore(init): start")
    sh(r, "tag", "-a", "v0.1.0", "-m", "first")
    return r


def run(repo, *args):
    return subprocess.run([sys.executable, str(SCRIPT), "--repo", str(repo), *args], capture_output=True, text=True)


def test_release_bumps_commits_and_tags(repo):
    r = run(repo, "0.2.0", "--no-gates")
    assert r.returncode == 0, r.stderr
    assert json.loads((repo / ".claude-plugin" / "plugin.json").read_text())["version"] == "0.2.0"
    assert sh(repo, "log", "-1", "--format=%s") == "chore(release): v0.2.0"
    assert sh(repo, "cat-file", "-t", "v0.2.0") == "tag"          # annotated
    assert sh(repo, "status", "--porcelain") == ""
    assert run(repo, "--check-tag").returncode == 0


def test_bump_patch_needs_changelog_section(repo):
    r = run(repo, "--bump", "patch", "--no-gates")
    assert r.returncode == 1 and "0.1.1" in r.stderr and "CHANGELOG" in r.stderr
    assert not rel.tag_exists(repo, "v0.1.1")


def test_refuses_dirty_tree_duplicate_tag_and_downgrade(repo):
    (repo / "dirty.txt").write_text("x")
    assert "not clean" in run(repo, "0.2.0", "--no-gates").stderr
    (repo / "dirty.txt").unlink()
    assert "not greater" in run(repo, "0.1.0", "--no-gates").stderr
    sh(repo, "tag", "-a", "v0.2.0", "-m", "x")
    assert "already exists" in run(repo, "0.2.0", "--no-gates").stderr


def test_refuses_other_branch_unless_allowed(repo):
    sh(repo, "checkout", "-q", "-b", "feature")
    assert "release from main" in run(repo, "0.2.0", "--no-gates").stderr
    assert run(repo, "0.2.0", "--no-gates", "--allow-branch").returncode == 0


def test_check_tag_fails_when_version_is_untagged(repo):
    p = repo / ".claude-plugin" / "plugin.json"
    p.write_text(p.read_text().replace("0.1.0", "0.9.0"))
    r = run(repo, "--check-tag")
    assert r.returncode == 1 and "v0.9.0 does not exist" in r.stderr


def test_verify_tag_matches_manifest_and_changelog(repo):
    assert run(repo, "--verify-tag", "v0.1.0").returncode == 0
    assert "does not match" in run(repo, "--verify-tag", "v0.3.0").stderr
    p = repo / "CHANGELOG.md"
    p.write_text(p.read_text().replace("## 0.1.0 - 2026-11-01", "## 0.1.0"))
    assert "no '## 0.1.0" in run(repo, "--verify-tag", "v0.1.0").stderr


def test_bumped_versions():
    assert rel.bumped("1.2.3", "patch") == "1.2.4"
    assert rel.bumped("1.2.3", "minor") == "1.3.0"
    assert rel.bumped("1.2.3", "major") == "2.0.0"
    with pytest.raises(rel.ReleaseError):
        rel.parse("1.2")


def test_pre_push_hook_checks_the_tag_when_pushing_main():
    hook = (Path(__file__).resolve().parent.parent / ".githooks" / "pre-push").read_text(encoding="utf-8")
    assert "release.py --check-tag" in hook and "refs/heads/main" in hook
