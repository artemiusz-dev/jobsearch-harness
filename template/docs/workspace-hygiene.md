# Workspace Hygiene

## Naming convention for company folders

All company folders follow `paths.output_dir_pattern` from `profile.yaml` (default `{company_slug}-{role_slug}-{date}`, for example `acme-senior-backend-2026-03-28`).

- **Lowercase kebab-case only.** No PascalCase, UPPERCASE or camelCase.
- **Date suffix is mandatory** (`YYYY-MM-DD`, the date of JD analysis or first contact).
- **The company slug is consistent** across folders of the same company (`link-group-*`, not sometimes `linkgroup-*`).
- **No spaces, underscores or special characters.**

## Temp files: what gets cleaned

`cleanup.py` (dry-run by default) targets only:

**Recursive (all subdirectories, except the backup dir, `node_modules`, `.git`, `.venv`):**
- `.DS_Store` (macOS metadata)
- `.~lock.*` (LibreOffice stale lock files)
- `*.tmp`
- `unpacked/` directories that contain `[Content_Types].xml` (the signature of an unpacked Office document). Any other directory with that name is left alone, and symlinks are never followed or deleted.

It never deletes files by extension-less name or by guesswork. To remove anything else, do it yourself on purpose.

## When to run cleanup

- After every CV or letter build that involves PDF conversion (LibreOffice leaves lock files).
- Periodically when the workspace feels cluttered: `cleanup.py --workspace .` (dry run) first, then `--execute`.
- Do not clean by hand; use the script to avoid deleting real files.

## Files that stay at the workspace root

- `profile.yaml`, `CLAUDE.md`, `pipeline.md`, `knowledge-base.md`: project context
- `interview-kb-hard-skills.md`, `interview-kb-soft-skills.md`: interview KBs
- the tracker (`applications-tracker.xlsx`)
- `_template.md`: analysis template
- `application-forms.md`: rules for free-text portal fields
- `cv_base/`: the base CV (never overwritten)
- `docs/`: rules moved out of `CLAUDE.md`
- `company_research/`: research cache (30-day TTL, created on first use)
- `upskill/`: upskill reports
- the backup directory (`paths.backup_dir`)

## What must never be committed to a public repository

The workspace holds personal data. If you version it, keep that repository private, and keep `profile.yaml`, `cv_base/`, the tracker, the knowledge base, interview KBs, company folders and backups out of any public one. The plugin repository itself must contain none of it.
