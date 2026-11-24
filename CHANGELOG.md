# Changelog

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
