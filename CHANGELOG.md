# Changelog

## 0.3.1 - 2026-11-24
- Developer hooks: `scripts/dev_setup.py` (venv, dependencies, ruff, `core.hooksPath` for the clone), a `commit-msg` hook (`scripts/check_commit_msg.py`: no home paths, real emails, phone numbers or denylist terms in commit messages; subject length), a `pre-push` hook (ruff, pytest, full privacy audit) and ruff on staged files in `pre-commit`.
- `ruff.toml` and a clean `ruff check`; ruff runs in CI.
- Tests that keep `_deps.MODULES` in step with `requirements.txt`.

## 0.3.0 - 2026-11-24
- `build_application.py` builds DOCX only when LibreOffice is missing (or with `--docx-only`), runs text checks on the DOCX (email, `must_contain`, em dash, keyword coverage) and exits 2 so callers know page fit and layout were not checked. Previously it crashed after writing the DOCX and skipped every check.
- `jobprofile.py --json` prints the merged profile (presets included); all skills now read the merged profile instead of the raw `profile.yaml`, which missed preset values such as `avoid_company_types`.
- New `scripts/check_dm.py`: mechanical check for outbound LinkedIn DMs (max 3 sentences after the greeting, banned phrases, em dash). `recruiter-responder` must run it instead of self-certifying the count; it also must not invent the topic of a context hook.
- `jd-analyzer` and the rubric: ambiguous work-rights wording ("EU work permission required") is `Eligibility: FLAG, user decides`, never a quiet PASS.
- New optional `situation` profile section (`available_from`, `reason_to_give_recruiters`, `search_priority`, `relocation_messaging`, `notes`), passed through by `init-workspace` together with `reply_greeting`, and described in the workspace `CLAUDE.md`.
- `cv-tailor`: documents build exit codes; the summary opening must match the CV title's role family.

## 0.2.1 - 2026-11-24
- Scripts now bootstrap their own dependencies (`scripts/_deps.py`): when PyYAML, openpyxl, python-docx, jsonschema or pypdf are missing, they are installed once into a private venv (`$CLAUDE_PLUGIN_DATA/venv` or `~/.cache/jobsearch-harness/venv`) and the command is re-run there. Plain `python3 <plugin>/scripts/...` now works with any Python.
- `init-workspace` writes `scoring.rubric_version: v2` explicitly, so skills reading `profile.yaml` directly stamp the right rubric.

## 0.2.0 - 2026-11-24
- recruiter-responder: new "Outbound LinkedIn DMs" section (2-3 sentence cap, three-part structure, banned phrases, example closers); humanize rule links to it.
- Optional `style.reply_greeting` profile field (schema, example, workspace `CLAUDE.md` rule) for chat replies.

## 0.1.0 - 2026-11-22
- Plugin and marketplace manifests.
- Skills: init-workspace, job-scanner, jd-analyzer, cv-tailor, cover-letter-writer, followup-tracker, recruiter-responder, interview-prep, interview-drillbook, interview-material-reviewer, human-text, save-context.
- Scripts: profile loader, spec-driven CV/letter builder, PDF and layout verifiers, tracker query and restyle, cleanup, net-pay estimator, workspace initializer.
- Config schema, role presets (frontend, generic, backend, data, pm) and market packs (generic, poland).
- Workspace template with rules, docs and skeletons.
- Board adapter contract (no scrapers included).
- Hardening from the definition-of-done review: safer init-workspace cleanup, validated preset and path names, CV structure detection in any section order, PDF conversion timeouts and stale-output protection, whole-word company matching, status-role mapping, content-verified tracker restyle that keeps links and comments, narrower cleanup, and a privacy audit that inspects Office documents and the git index.
