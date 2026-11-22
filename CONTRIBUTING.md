# Contributing

Thanks for helping. This project has one hard rule: **no personal data in this repository, ever.** Everything here must be generic or clearly fictional.

## Ground rules

- **Fictional data only.** Test fixtures use invented people and companies (`example.com`, "Alex Example"). Never paste a real CV, posting, tracker row, recruiter message or company folder, even "anonymized".
- **No scrapers, no credentials.** Board integrations belong in separate repositories that implement `docs/adapters.md`. Never commit tokens, session files or MCP configuration.
- **Skills read the profile.** A skill that hardcodes a role, stack, country, currency, language or name is a bug. Put facts in `profile.yaml` or a preset.
- **Keep market packs informational.** Tax and salary content states its source year and says "verify".

## Setup

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest
```

LibreOffice is optional; PDF-building tests are skipped without it.

## Before you open a PR

1. Tests pass: `.venv/bin/python -m pytest`.
2. Privacy audit passes: `.venv/bin/python scripts/privacy_audit.py`. If you keep a personal denylist, run it with `--denylist <file outside the repo>`; never add that file here.
3. New behavior has a test; new profile fields are in `config/profile.schema.json` with a default and described in the README or the relevant doc.
4. Use a short dash `-` in generated-text rules and docs, not an em dash.
5. Commits use a noreply email. Check with `git log --format='%an <%ae>'`.

## Adding a role or market preset

- Role: copy `presets/roles/generic.yaml`, add stacks, keywords and `rubric_hints`. It must load with every market in `tests/test_presets.py`.
- Market: add `presets/markets/<name>.yaml` (parameters, boards) and `<name>.md` (the salary document copied to `docs/salary-rules.md`). Put numbers in `market_params`, cite the year, and add a test for any formula.

## Reporting a privacy problem

If you spot personal data anywhere in the repository or its history, open an issue that describes where (not the data itself) or contact the maintainers privately.
