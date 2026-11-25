# Changelog

## 1.0.0 - 2026-11-25
- First stable release: personal rules have a single source (`profile.yaml` plus workspace docs), scripts and skills hold none, and drift tests guard it.
- README points to `docs/parity.md` and `docs/migration.md`.

## 0.9.0 - 2026-11-25
- Parity verified against a real standalone setup (read-only, old project hashed before and after): `tracker_query quiet` returns the same 91 candidates as the old script; `match` returns the same rows for the checked companies except where the old character-ratio matcher produced false positives (whole-word matching is stricter by design); a real application spec builds with the same file names, page counts and letter text, and CV text differing only in trailing whitespace.
- `docs/migration.md`: how to move from a standalone setup to the plugin without touching it.
- `docs/parity.md` statuses reflect what is enforced.

## 0.8.0 - 2026-11-25
- Drift protection (`tests/test_drift.py`): the example profile and `init_workspace.py` must equal the schema defaults; the scoring rubric and tracker-schema docs must quote the schema defaults (weights, thresholds, technical floor, statuses, column order); the banned phrase list and ATS domains must not be copied into scripts or the workspace `CLAUDE.md`; every `$P.<field>` reference in skills and templates must exist in the schema.
- Skill lint: no status names or numeric limits (days, words, characters) inside skills (generic writing and review skills are listed exceptions); frontmatter `name` matches the directory.
- Adapter resolution is explicit: `boards[].tools.{search,details}` names the exact tools, else the scanner looks inside the MCP server named by `adapter`; an unresolvable board is reported as "adapter unavailable" and skipped. `docs/adapters.md` explains why a bare prefix is not enough.
- `tracker-schema.md` documents `tracker.fields` and `tracker.stages` instead of telling users to keep default column names.

## 0.7.0 - 2026-11-25
- Personal values are read from the profile instead of being written into scripts and skills:
  - tracker scripts (`tracker_add`, `tracker_query`, `restyle_tracker`, `lib/calibration`) take column headers from `tracker.fields`, stage columns and their roles from `tracker.stages`, the new-row status from `tracker.default_new_status`, the follow-up marker from `followups.marker`, per-status windows from `followups.by_status`, and the fuzzy-match ratio and calibration sample size from `tracker.*`. A profile that renames every column, stage and status works end to end (`tests/test_rename_everything.py`).
  - `check_dm.py` reads sentence cap, banned phrases (global plus the dm channel) and the em-dash rule from `style`; without a workspace it uses schema defaults, and an invalid profile is an error.
  - `cvbuild.py` reads paper size, CV page limit, date format, salutation, closing and letter page count from `cv` and `letter`.
- Skills no longer carry day counts, word limits, status names or phrase lists of their own: `followup-tracker`, `recruiter-responder`, `job-scanner`, `jd-analyzer`, `cover-letter-writer`, `cv-tailor`, `interview-prep`, `human-text` point to `$P.followups`, `$P.style.limits`, `$P.scoring.posting_health`, `$P.tracker.status_roles` and so on. The workspace `CLAUDE.md` and `humanize-rule.md` do the same; the banned list lives only in `style.banned_phrases`.
- New behaviour: search tracks per board, named company lists, excluded industries, custom gates and modifiers in scanning and analysis; prior applications within `followups.history_window_days` shown in the scan notes, in `analysis.md` and before recruiter replies.
- `recruiter-responder` no longer tells the user to say they are "actively exploring" (the phrase is banned everywhere).

## 0.6.0 - 2026-11-25
- Profile schema extended so personal rules have one home: `targets.companies` (blacklist, whitelist, watch, never-contact), `targets.search_tracks`, `targets.excluded_industries`, `scoring.gates.custom`, `scoring.modifiers`, `scoring.posting_health`, `scoring.signal_stacks`, `compensation` (floors per type, compare-in, never-quote-net), `work_authorization` (target countries, permits, form wording), `followups` (per-status windows, marker, history window, draft-only), `tracker` (stages, default new status, closed and in-progress roles), `style` (banned phrases, per-channel extras, length limits, tone, languages), `cv`, `letter`, `referral`, `security`, `privacy`.
- `Profile` helpers: `banned_phrases(channel)`, `limit()`, `followup_days(status)`, `followup_marker()`, `default_new_status`, `stage_columns`, `status_role()`.
- Cross-field validation: default status, per-status follow-up keys, stage columns, marker placeholder, depth-risk range, referral path.
- `init_workspace.py` takes scoring defaults from the schema instead of its own copy.
- `docs/parity.md`: where every kind of personal rule lives. Scripts and skills start reading the new fields in 0.7.0.

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
