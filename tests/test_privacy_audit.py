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


# ---------------------------------------------------------------- added after review
def make_docx(path, text="hello", author="Example Author"):
    import docx
    d = docx.Document()
    d.core_properties.author = author
    d.core_properties.last_modified_by = author
    d.add_paragraph(text)
    d.save(path)


def test_office_documents_are_inspected_for_text_and_authors(tmp_path):
    r = make_repo(tmp_path)
    fx = r / "tests" / "fixtures"
    fx.mkdir(parents=True)
    make_docx(fx / "ok.docx")
    sh(r, "add", "-A")
    sh(r, "commit", "-q", "--no-verify", "-m", "ok")
    assert run(r).returncode == 0
    make_docx(fx / "bad.docx", text="write to jane" + "@realmail.net", author="Jane Real")
    sh(r, "add", "-A")
    out = run(r).stdout
    assert "bad.docx" in out and "realmail.net" in out and "Jane Real" in out


def test_denylist_applies_inside_office_documents(tmp_path):
    r = make_repo(tmp_path)
    fx = r / "tests" / "fixtures"
    fx.mkdir(parents=True)
    make_docx(fx / "x.docx", text="worked at Secretco")
    sh(r, "add", "-A")
    sh(r, "commit", "-q", "--no-verify", "-m", "m")
    deny = tmp_path / "deny.txt"
    deny.write_text("# comment\n\nsecretco\n")                  # blank lines and comments are ignored
    out = run(r, "--denylist", str(deny)).stdout
    assert "x.docx" in out and "denylist" in out


def test_github_made_commits_are_accepted(tmp_path):
    r = make_repo(tmp_path, email="noreply@github.com")
    commit(r, "a.md", "hello\n")
    assert run(r).returncode == 0


def test_invalid_denylist_regex_is_a_clean_error(tmp_path):
    r = make_repo(tmp_path)
    commit(r, "a.md", "hello\n")
    deny = tmp_path / "deny.txt"
    deny.write_text("(unclosed\n")
    out = run(r, "--denylist", str(deny))
    assert out.returncode == 1 and "invalid regular expression" in out.stderr and "Traceback" not in out.stderr


def test_national_phone_formats_are_flagged(tmp_path):
    r = make_repo(tmp_path)
    commit(r, "a.md", "call 555" + "-123-4567 or (555" + ") 123-4567\n")
    assert "phone-like" in run(r).stdout


def test_audit_reads_the_index_not_unstaged_edits(tmp_path):
    r = make_repo(tmp_path)
    commit(r, "a.md", "clean\n")
    (r / "a.md").write_text("mail jane" + "@realmail.net\n")        # edited but not staged
    assert run(r).returncode == 0
    sh(r, "add", "a.md")
    assert run(r).returncode == 1


def test_fresh_repository_without_commits_is_audited(tmp_path):
    r = make_repo(tmp_path)
    (r / "a.md").write_text("hello\n")
    sh(r, "add", "-A")
    out = run(r)
    assert out.returncode == 0 and "Traceback" not in out.stderr


def test_not_a_git_repository_is_a_clean_error(tmp_path):
    out = run(tmp_path)
    assert out.returncode == 1 and "Traceback" not in out.stderr
