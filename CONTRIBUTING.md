# Contributing

Thanks for helping. This project has one hard rule: **no personal data in this repository, ever.** Everything here must be generic or clearly fictional.

## Ground rules

- **Fictional data only.** Test fixtures use invented people and companies (`example.com`, "Alex Example"). Never paste a real CV, posting, tracker row, recruiter message or company folder, even "anonymized".
- **No scrapers, no credentials.** Board integrations belong in separate repositories that implement `docs/adapters.md`. Never commit tokens, session files or MCP configuration.
- **Skills read the profile.** A skill that hardcodes a role, stack, country, currency, language or name is a bug. Put facts in `profile.yaml` or a preset.
- **Keep market packs informational.** Tax and salary content states its source year and says "verify".

## Setup

One command per clone (creates `.venv`, installs the dependencies and ruff, and enables the git hooks for this clone only):

```bash
python3 scripts/dev_setup.py          # --check reports the state without changing anything
```

The hooks in `.githooks` are fail-closed:

- `pre-commit`: privacy audit of what is staged (plus your private denylist if you keep one at `~/.config/jobsearch-private/denylist.txt` or `$JOBSEARCH_DENYLIST`; optional), noreply author email, `ruff` on the staged Python files.
- `commit-msg`: subject must be `type(scope): subject` (types `feat fix docs test chore refactor perf build ci revert`, scope required, `!` marks a breaking change; Merge, Revert, fixup! and squash! are exempt), at most 72 characters; no home paths, real emails, phone numbers or denylist terms in the message.
- `pre-push`: `ruff`, the full test suite and the full-history privacy audit, the same gates as CI; pushing `main` is blocked unless the `plugin.json` version has a `v<version>` tag.

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check scripts tests
```

LibreOffice is optional; PDF-building tests are skipped without it.

## Commits and releases

Commit subjects read `type(scope): subject`. Common scopes: `build`, `hooks`, `skills`, `presets`, `profile`, `tracker`, `cv`, `dm`, `docs`, `ci`, `deps`, `release`. Example: `fix(build): keep the DOCX when soffice is missing`.

Every released version is tagged. Write the `## X.Y.Z - YYYY-MM-DD` section in `CHANGELOG.md` with the work, commit it, then run:

```bash
python3 scripts/release.py --bump patch      # or minor / major, or an explicit X.Y.Z
git push origin main && git push origin vX.Y.Z   # or add --push
```

`release.py` checks the tree, branch and changelog, runs the gates, writes the version into `.claude-plugin/plugin.json`, commits `chore(release): vX.Y.Z` and creates the annotated tag. CI verifies that a pushed tag matches `plugin.json` and the changelog.

## Before you open a PR

1. Tests and lint pass: `.venv/bin/python -m pytest` and `.venv/bin/ruff check scripts tests` (the `pre-push` hook runs both).
2. Privacy audit passes: `.venv/bin/python scripts/privacy_audit.py`. If you keep a personal denylist, run it with `--denylist <file outside the repo>`; never add that file here.
3. New behavior has a test; new profile fields are in `config/profile.schema.json` with a default where one makes sense, and described in the README or the relevant doc.
4. Use a short dash `-` in generated-text rules and docs, not an em dash.
5. Commits use a noreply email. Check with `git log --format='%an <%ae>'`.

## Adding a role or market preset

- Role: copy `presets/roles/generic.yaml`, add stacks, keywords and `rubric_hints`. It must load with every market in `tests/test_presets.py`.
- Market: add `presets/markets/<name>.yaml` (parameters, boards) and `<name>.md` (the salary document copied to `docs/salary-rules.md`). Put numbers in `market_params`, cite the year, and add a test for any formula.

## Reporting a privacy problem

If you spot personal data anywhere in the repository or its history, open an issue that describes where (not the data itself) or contact the maintainers privately.
