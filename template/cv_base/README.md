# cv_base/

Put your base CV here (default name `base_cv.docx`; the path is `paths.base_cv` in `profile.yaml`). It is the one document every tailored CV starts from. The builder never overwrites it.

## Required structure

A single-column Word document (no tables, text boxes or columns) laid out like this:

1. **Name** (first non-empty paragraph)
2. **Title line** (second)
3. **Contact line** (third; must contain the email from `profile.yaml`)
4. A **summary heading** (default text contains "PROFESSIONAL SUMMARY"), then the summary paragraph
5. A **skills heading** (contains "SKILLS"), then one paragraph per skills line, formatted `Label: values` (ideally two runs, a bold label and plain values; a single run also works)
6. An **experience heading** (contains "PROFESSIONAL EXPERIENCE"), then your roles and bullets

The sections may come in any order. The skills block ends at the next section heading, so give every other section heading (education, certifications, ...) short UPPERCASE text, or it will be read as a skills line.

If your headings differ, set `cv_map.summary_heading`, `skills_heading` and `experience_heading` in `profile.yaml`, or give explicit indices in `cv_map.indices`. Check what the builder sees with:

```
python3 <plugin>/scripts/lib/cvbuild.py --map --workspace .
```

## Rules
- Dates use full months and an ASCII hyphen: `March 2021 - June 2023`.
- Every fact must also be in `knowledge-base.md`.
- This folder is private data. It is git-ignored by the template's `.gitignore`; keep it out of any public repository.
