import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "privacy_audit.py"


def sh(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def make_repo(tmp_path, email="bot@users.noreply.github.com"):
    r = tmp_path / "r"
    r.mkdir()
    sh(r, "init", "-q")
    sh(r, "config", "user.name", "x")
    sh(r, "config", "user.email", email)
    return r


def commit(r, name, content):
    (r / name).write_text(content)
    sh(r, "add", "-A")
    sh(r, "commit", "-q", "--no-verify", "-m", "m")


def run(r, *extra):
    return subprocess.run([sys.executable, str(SCRIPT), "--repo", str(r), *extra], capture_output=True, text=True)


def test_clean_repo_passes(tmp_path):
    r = make_repo(tmp_path)
    commit(r, "a.md", "contact: someone@example.com\n")
    assert run(r).returncode == 0


def test_flags_real_looking_email_phone_path_and_filetype(tmp_path):
    r = make_repo(tmp_path)
    commit(r, "a.md", "mail me: jane" + "@realmail.net\ncall +4" + "8 123 456 789\n/Us" + "ers/jane/work\n")
    (r / "cv.docx").write_text("x")
    sh(r, "add", "-A")
    sh(r, "commit", "-q", "--no-verify", "-m", "m2")
    out = run(r).stdout
    assert "realmail.net" in out and "phone-like" in out and "home path" in out and "cv.docx" in out


def test_flags_non_noreply_author(tmp_path):
    r = make_repo(tmp_path, email="jane" + "@realmail.net")
    commit(r, "a.md", "hello\n")
    assert "noreply" in run(r).stdout


def test_denylist_checks_content_names_and_history(tmp_path):
    r = make_repo(tmp_path)
    commit(r, "a.md", "this mentions Secretco\n")
    deny = tmp_path / "deny.txt"
    deny.write_text("secretco\n")
    out = run(r, "--denylist", str(deny)).stdout
    assert "denylist" in out
    # removing it from the tree must still be caught in history
    commit(r, "a.md", "clean now\n")
    out = run(r, "--denylist", str(deny)).stdout
    assert "git history" in out


def test_refuses_denylist_inside_repo(tmp_path):
    r = make_repo(tmp_path)
    commit(r, "a.md", "x\n")
    d = r / "deny.txt"
    d.write_text("x\n")
    assert run(r, "--denylist", str(d)).returncode == 1
