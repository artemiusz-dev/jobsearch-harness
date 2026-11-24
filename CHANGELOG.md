# Changelog

## 0.5.1 - 2026-11-25
- `tracker_query.py summary`: rows per status, stage-column counts and the age of open applications in one call. `followup-tracker` uses it (and `quiet`) instead of reading the xlsx with its own `openpyxl` snippet, which failed on machines without the package.
- `job-scanner`: a board that returns zero results is retried once with a looser query before it is reported as "no data" (a stacked filter on justjoinit matched nothing).
- `interview-drillbook` runs the material-reviewer checks itself and reports critical findings, since drill books copy knowledge-base answers that can contain unsupported claims.

## 0.5.0 - 2026-11-25
- `tracker_query.py calibrate`: reply rate per Match % band for applications old enough to have had a reply, with 95% Wilson intervals, bands under 30 applications marked and ignored, and a plain verdict on whether the score predicts replies (thresholds are only worth changing when it does).
- New `scripts/score_compare.py`: mean, range and difference to a reference across repeated analyses of one posting, overall and per dimension.
- `docs/scoring-rubric.md` explains how to read both and says when to change thresholds.

## 0.4.0 - 2026-11-25
- `tracker_add.py add|update`: the only way skills change tracker rows. Backs up first (never overwriting a backup, including two in one second; `restyle_tracker.py` had the same flaw and is fixed), validates status and dates, refuses the same company and role (fuzzy match, exit 2), asks when an update matches no or several rows, then restyles. Skills and the workspace `CLAUDE.md` route all tracker edits through it.
- PDF builds: LibreOffice is found in the usual install locations (macOS app bundle, Homebrew, Windows, snap) or via `$SOFFICE`, not only on `PATH`. Entry headers are kept with their first bullet automatically, which fixed orphaned headers at a page break. Keyword coverage accepts plural/singular variants.
- `cv-tailor`: exit 1 (too many pages, layout problem) is not done: shorten or extend `drop` and rebuild up to three times; a CV is presented only when it passes or the failing check is named.
- `init-workspace` asks explicitly for primary/secondary/avoided stacks, depth-risk topics and rubric hints (the cause of mis-scored full-stack roles) and warns that thresholds are uncalibrated; `init_workspace.py` writes them.
- `_deps.ensure()` explains itself when a script comes from stdin or `-c` instead of silently doing nothing.
- `release.py` runs the privacy audit with your private denylist like the hooks do.

## 0.3.2 - 2026-11-24
- Commit subjects must be `type(scope): subject` (scope required); the `commit-msg` hook rejects anything else (Merge, Revert, fixup! and squash! are exempt).
- Every released version is tagged: new `scripts/release.py` (clean tree, main branch, CHANGELOG section, gates, `chore(release): vX.Y.Z` commit, annotated tag, optional push), `pre-push` blocks pushing `main` when the `plugin.json` version has no tag, CI checks a pushed `v*` tag against `plugin.json` and the changelog.
- Missing tags for 0.1.0, 0.2.0 and 0.2.1 added retroactively.

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
