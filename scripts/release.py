#!/usr/bin/env python3
"""Cut a release: version bump, release commit and annotated tag (standard library only).

    python3 scripts/release.py 0.4.0                 # release this version
    python3 scripts/release.py --bump patch          # next patch/minor/major from plugin.json
    python3 scripts/release.py 0.4.0 --push          # also push main and the tag to origin
    python3 scripts/release.py --check-tag           # plugin.json version has a v<version> tag on an ancestor of HEAD
    python3 scripts/release.py --verify-tag v0.4.0   # CI: tag == plugin.json version and CHANGELOG has the section

Release flow: write the `## X.Y.Z - YYYY-MM-DD` section in CHANGELOG.md and commit it with the work. This
script then refuses to run unless the tree is clean, the branch is main, the tag does not exist yet and the
CHANGELOG section exists; it runs ruff, pytest and the privacy audit (skip with --no-gates, tests only), writes
the version into .claude-plugin/plugin.json, commits `chore(release): vX.Y.Z` and creates the annotated tag.
Nothing is pushed unless --push is given. The pre-push hook blocks pushes of main when the plugin.json
version has no tag, so every released version is tagged.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
VERSION_LINE = re.compile(r'("version"\s*:\s*")([^"]+)(")')


class ReleaseError(Exception):
    pass


def git(repo: Path, *args: str, check: bool = True) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise ReleaseError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout.strip()


def manifest(repo: Path) -> Path:
    return repo / ".claude-plugin" / "plugin.json"


def current_version(repo: Path) -> str:
    return json.loads(manifest(repo).read_text(encoding="utf-8"))["version"]


def changelog_has(repo: Path, version: str) -> bool:
    text = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    return re.search(rf"^## {re.escape(version)} - \d{{4}}-\d{{2}}-\d{{2}}\s*$", text, re.M) is not None


def parse(version: str) -> tuple[int, int, int]:
    m = SEMVER.match(version)
    if not m:
        raise ReleaseError(f"version must look like 1.2.3 (got {version!r})")
    return int(m[1]), int(m[2]), int(m[3])


def bumped(version: str, part: str) -> str:
    a, b, c = parse(version)
    return {"major": f"{a + 1}.0.0", "minor": f"{a}.{b + 1}.0", "patch": f"{a}.{b}.{c + 1}"}[part]


def tag_exists(repo: Path, tag: str) -> bool:
    return bool(git(repo, "tag", "-l", tag, check=False))


def check_tag(repo: Path) -> None:
    """plugin.json's version must be tagged, and the tag must be an ancestor of HEAD."""
    ver = current_version(repo)
    tag = f"v{ver}"
    if not tag_exists(repo, tag):
        raise ReleaseError(f"plugin.json is at {ver} but tag {tag} does not exist. Run `git fetch --tags`, or release it with scripts/release.py {ver}")
    r = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", tag, "HEAD"], capture_output=True)
    if r.returncode != 0:
        raise ReleaseError(f"tag {tag} is not an ancestor of HEAD")


def verify_tag(repo: Path, tag: str) -> None:
    ver = current_version(repo)
    if tag != f"v{ver}":
        raise ReleaseError(f"tag {tag} does not match plugin.json version {ver}")
    if not changelog_has(repo, ver):
        raise ReleaseError(f"CHANGELOG.md has no '## {ver} - YYYY-MM-DD' section")


def gates(repo: Path) -> None:
    py = repo / ".venv" / "bin" / "python"
    exe = str(py) if py.exists() else sys.executable
    ruff = repo / ".venv" / "bin" / "ruff"
    steps = []
    if ruff.exists():
        steps.append([str(ruff), "check", "scripts", "tests"])
    audit = [exe, "scripts/privacy_audit.py"]
    deny = Path(os.environ.get("JOBSEARCH_DENYLIST", Path.home() / ".config" / "jobsearch-private" / "denylist.txt"))
    if deny.is_file():
        audit += ["--denylist", str(deny)]
    steps += [[exe, "-m", "pytest", "-q"], audit]
    for cmd in steps:
        print("release: running", " ".join(Path(c).name if i == 0 else c for i, c in enumerate(cmd)))
        r = subprocess.run(cmd, cwd=repo)
        if r.returncode != 0:
            raise ReleaseError(f"gate failed: {' '.join(cmd)}")


def release(repo: Path, version: str, run_gates: bool, push: bool, allow_branch: bool = False) -> None:
    new = parse(version)
    old = parse(current_version(repo))
    if new <= old:
        raise ReleaseError(f"{version} is not greater than the current version {current_version(repo)}")
    tag = f"v{version}"
    if tag_exists(repo, tag):
        raise ReleaseError(f"tag {tag} already exists")
    if git(repo, "status", "--porcelain"):
        raise ReleaseError("working tree is not clean: commit or stash first")
    branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if branch != "main" and not allow_branch:
        raise ReleaseError(f"release from main (on {branch}); use --allow-branch to override")
    if not changelog_has(repo, version):
        raise ReleaseError(f"CHANGELOG.md needs a '## {version} - YYYY-MM-DD' section first")
    if run_gates:
        gates(repo)
    path = manifest(repo)
    text = path.read_text(encoding="utf-8")
    path.write_text(VERSION_LINE.sub(rf"\g<1>{version}\g<3>", text, count=1), encoding="utf-8")
    git(repo, "add", str(path.relative_to(repo)))
    git(repo, "commit", "-q", "-m", f"chore(release): {tag}")
    git(repo, "tag", "-a", tag, "-m", f"jobsearch-harness {version}")
    print(f"release: committed and tagged {tag} (not pushed)")
    if push:
        git(repo, "push", "origin", "main")
        git(repo, "push", "origin", tag)
        print(f"release: pushed main and {tag} to origin")
    else:
        print(f"release: push when ready:  git push origin main && git push origin {tag}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("version", nargs="?", help="new version, e.g. 0.4.0")
    ap.add_argument("--bump", choices=("patch", "minor", "major"))
    ap.add_argument("--push", action="store_true", help="also push main and the tag to origin")
    ap.add_argument("--no-gates", action="store_true", help="skip ruff/pytest/privacy audit (for tests only)")
    ap.add_argument("--allow-branch", action="store_true", help="release from a branch other than main")
    ap.add_argument("--check-tag", action="store_true", help="verify plugin.json's version is tagged")
    ap.add_argument("--verify-tag", metavar="TAG", help="verify TAG matches plugin.json and CHANGELOG (CI)")
    ap.add_argument("--repo", default=str(ROOT), help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    repo = Path(a.repo)
    try:
        if a.check_tag:
            check_tag(repo)
            print(f"release: v{current_version(repo)} is tagged")
            return 0
        if a.verify_tag:
            verify_tag(repo, a.verify_tag)
            print(f"release: {a.verify_tag} matches plugin.json and CHANGELOG")
            return 0
        if bool(a.version) == bool(a.bump):
            ap.error("give a version or --bump, not both")
        release(repo, a.version or bumped(current_version(repo), a.bump), not a.no_gates, a.push, a.allow_branch)
    except ReleaseError as exc:
        print(f"release: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
