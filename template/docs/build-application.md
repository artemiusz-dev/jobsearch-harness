# Build CV / cover letter from a spec (`build_application.py`)

One spec per application, one builder. No per-company scripts.

```
python3 <plugin>/scripts/build_application.py <company-folder> [--cv] [--letter] [--verify] [--spec FILE] [--out-dir DIR] [--force] [--workspace DIR]
```

- Reads `<company-folder>/spec.json`. Builds the sections present (`cv`, `letter`) unless `--cv` / `--letter` narrows it.
- Starts from the untouched base CV (`paths.base_cv`) and converts with LibreOffice (`soffice`, must be installed); prints the paragraphs it cut.
- `--spec spec-<role>.json` builds a second role at the same company; set a distinct `file_name` in that spec so outputs do not clash.
- `--verify` runs `verify_pdf.py` (pages, ATS text layer, ASCII date hyphens, the profile email, `must_contain`), `verify_layout.py`, and a keyword coverage list.
- **Never overwrites existing output** (submitted materials are immutable): use `--out-dir DIR` for a test rebuild; `--force` only on purpose.
- Exit code 1 if the page count or layout fails.
- Wording edits = edit `spec.json` and rebuild. Do not clone scripts.
- Find your base CV's paragraph indices with `python3 <plugin>/scripts/lib/cvbuild.py --map --workspace .`.

## Workflow (spec first, build once)
1. Draft `spec.json` from the JD analysis and the knowledge base (the Factual Grounding Audit applies).
2. Show the user the grey-zone or stretch bullets (keep / soften / drop) and the `drop` order; get one approval.
3. Build once with `--verify`; run the Draft Review Pass; apply fixes by editing the spec; rebuild with `--out-dir` and replace, or delete the draft output first (`--force` only for unsubmitted drafts).
4. The spec stays in the folder as the record of exactly what was submitted (the Follow-up Rules need it: no new claims).

## spec.json
```json
{
  "cv": {
    "title": "Header job title line",
    "summary": "Professional summary paragraph",
    "skills": [["Label", "comma, separated, values"]],
    "edits": [
      {"p": 21, "text": "replace whole base paragraph 21"},
      {"p": 25, "replace": ["old substring", "new substring"]},
      {"p": 44, "append": " text appended"}
    ],
    "drop": [34, 54, 56],
    "keep_with_next": [20, 31],
    "keep_together": [32],
    "max_pages": 2,
    "must_contain": ["critical keyword"],
    "keywords": ["coverage list"],
    "file_name": "optional override of identity.output_name_pattern"
  },
  "letter": {
    "headline": "defaults to cv.title",
    "date": "27 October 2026",
    "re": "Re: Role - Company",
    "salutation": "Dear Team,",
    "paragraphs": ["...", "..."],
    "closing": "Best regards,",
    "max_chars": 1000,
    "file_name": "optional override"
  }
}
```

- **Section detection:** the builder finds the title, summary, skills block and experience by the headings configured in `cv_map` (defaults: "PROFESSIONAL SUMMARY", "SKILLS", "PROFESSIONAL EXPERIENCE"; a heading is a short paragraph containing the keyword). Override with `cv_map.*_heading` or explicit `cv_map.indices`. A missing heading stops the build with a clear message.
- `skills`: as many lines as the base CV's skills block has; unused lines are removed.
- `p` indices refer to base-CV paragraphs (print them with `--map`). The builder asserts that `replace` strings exist.
- `drop`: paragraph indices in priority order (lowest value first, per the CV Trimming Rule). The builder removes them one at a time until the CV fits `max_pages` with a clean layout.
- `keep_with_next`: defaults to every paragraph starting with a prefix in `cv_map.keep_with_next_prefixes` (empty by default).
- The letter's name and contact line come from the base CV; the signature uses `identity.full_name`; em dashes are rejected when `style.forbid_em_dash` is on.
- An ASCII hyphen in date ranges is enforced by `--verify`.
