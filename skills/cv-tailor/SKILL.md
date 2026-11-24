---
name: cv-tailor
description: "Tailors the user's base CV for a specific job description, optimizing for ATS systems, AI screening tools and human reviewers without fabricating anything. Use when the user asks to tailor, adjust or optimize their CV, or says \"let's apply\" after a JD analysis."
---

# CV Tailor

Tailors the user's base CV for a specific job description, optimizing for ATS parsing, AI screening and human reviewers, without fabricating anything. `$P` means a field of the workspace's `profile.yaml`. Read it merged with the role and market presets, not as the raw file: run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/jobprofile.py --workspace . --json` once and use that output (preset values such as `avoid_company_types` and `scoring.depth_risk_keywords` are not in the raw `profile.yaml`).

## Authority

The knowledge base (`$P.paths.knowledge_base`) is the single source of truth for facts, metrics and gaps. The workspace `CLAUDE.md` is the authority for workflow rules, and its docs index points to the files that hold the full text: `docs/cv-letter-quality.md` (Draft Review Pass, Factual Grounding, CV Trimming Rule), `docs/humanize-rule.md`, `docs/workflows.md` (what to do after tailoring) and `docs/build-application.md` (the builder). Read `docs/cv-letter-quality.md` and `docs/build-application.md` before producing a CV. If this skill disagrees with them, they win.

## Context

The base CV is `$P.paths.base_cv`. A job description should already be available (pasted, or from a prior JD analysis). The user's targets (roles, stacks) are in `$P.targets`.

The base CV belongs to the user. Never overwrite it; write tailored output into the company folder.

## Prerequisites Check

1. **Base CV exists** at `$P.paths.base_cv`. If missing, ask the user to provide it (or run `init-workspace`).
2. **Job description is available** in the message, earlier in the conversation, or from a JD analyzer output. If not, ask. If the analyzer ran, reuse its score, keywords and gaps rather than re-analyzing.

## Step 1: Keyword Extraction

Organize JD keywords into two tiers:

**Critical Keywords** - must appear somewhere in the tailored CV: required technologies, frameworks, methodologies, experience thresholds, role-specific competencies. Missing these risks automatic filtering.

**Bonus Keywords** - include if the user has genuine experience: nice-to-haves, preferred qualifications, industry terms.

**Acronym + Full Term Rule** - include both forms for every key technology if either appears in the JD (e.g. "CI/CD" and "Continuous Integration / Continuous Delivery"). AI parsers may match either variant.

Present both lists to the user before changing anything, so they can veto keywords they do not want to claim.

## Step 2: Section-by-Section Changes

For every proposed change show all three pieces:

**Original:** > [exact current text]
**Proposed:** > [revised text]
**Why:** [which keywords are added, which JD requirement this addresses, why the framing is stronger]

Sections to evaluate:

- **Professional Summary / Title** - align positioning with the role. The first words of the summary must name the same role family as the CV title line (a Frontend Engineer title is not followed by a summary that opens "Senior Software Engineer"). Job titles must match real titles. If the JD title differs, consider noting both or adjusting language; truthful adjustments only.
- **Skills / Technologies** (mandatory) - this section must exist and appear right after the header/contact block, before Work Experience; AI parsers map it to scorecard criteria before reading job history. If the base CV lacks one, create it. Front-load the JD's priority technologies, add unlisted skills the user genuinely has (knowledge base skills section), de-emphasize irrelevant ones.
- **Work Experience** - where most tailoring happens. For each relevant role: rewrite bullets to emphasize JD-matching achievements, weave in critical keywords, adjust emphasis, add quantified impact only with numbers that exist in the knowledge base or that the user supplies (if the knowledge base says NOT FOUND, never invent one; respect any internal-only tags). Use complete sentences, not fragments. Dates use explicit full-month format ("March 2021 - June 2023"), not "2021 - 2023".
- **Education / Certifications** - usually minimal; highlight relevant coursework or certs if the JD prefers them.

Preserve the overall structure and formatting, accurate dates/companies/titles, and the user's voice.

## Step 3: ATS & AI Optimization Checks

- **Standard section headings** ("Experience", "Skills"), not creative ones
- **No formatting traps:** tables, multi-column layouts, text boxes, critical info in headers/footers, images
- **Keywords in context**, woven into achievements, not dumped in a block
- **Job title alignment:** if the real title differs from the JD's, suggest the equivalent in parentheses where truthful
- **Chronological clarity** with consistent dates and no accidental gaps
- **Plain-text sanity test:** parse the CV mentally as flat text; anything that collapses will collapse in an ATS too
- **Single-column layout only;** flag a multi-column base CV and recommend restructuring first
- **Consistent title formatting** across CV, LinkedIn and application forms

## Step 4: Truthfulness Verification

Non-negotiable. For every change that adds, strengthens or reframes a claim:

- **Adding a technology:** check the knowledge base first; ask the user only if absent. Add only if confirmed.
- **Strengthening impact:** use a metric only if it exists in the knowledge base or the user supplies it; otherwise a softer truthful framing.
- **Reframing scope:** ask ("I'm positioning your work on X as 'architected Y' - is that accurate?") and use the stronger framing only if confirmed.

If a gap would require fabrication, say so. Recommend skipping the application or addressing the gap in a cover letter (only if the user requests one) instead of inflating the CV.

## Step 5: Build (spec first, build once)

The CV is built from a spec file, not from a per-company script. Per-company scripts cause rework loops that are really wording edits; a spec makes each edit a one-line change and records exactly what was submitted. Do not create `gen_*` or `tailor_*` scripts.

1. After the user approves Steps 1-4, write `<company-folder>/spec.json` (format: `docs/build-application.md`). Put the title, summary, skills lines, bullet `edits` and the `drop` order in it. Order `drop` by the CV Trimming Rule (relevance to this JD, uniqueness in the CV, cover-letter dependency), lowest value first. Put critical keywords in `keywords` (and any that must be present in `must_contain`). To see the base CV's paragraph indices: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/lib/cvbuild.py --map --workspace .`.
2. List grey-zone bullets (posting terminology used for adjacent work, blended academic and industry claims) with "keep, soften, or drop?" before building. Every date, employer, title and number must trace to the knowledge base or the base CV (Factual Grounding Audit in `docs/cv-letter-quality.md`).
3. Build and verify: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/build_application.py <folder> --cv --verify --workspace .`. Exit codes: 0 = built and fully verified, 1 = a check failed, 2 = built as DOCX only because LibreOffice (`soffice`) is missing (page fit, PDF text layer and layout were NOT checked; only email, `must_contain`, em dash and keyword coverage were). On exit 2 still run the Draft Review Pass and report plainly that page fit is unverified; never install software, and tell the user to install LibreOffice and rebuild with `--force` for the full check.
   **Exit 1 (too many pages or a layout problem) is not done:** shorten bullets or add entries to `drop` (least relevant first, long entries before short ones), rebuild with `--force`, and repeat up to three times until the script prints `RESULT: built and verified (exit 0)`. Entry headers are kept with their first bullet automatically (`cv_map.keep_with_next_prefixes` overrides this). Only present a CV that passed, or say exactly which check still fails and why. A keyword reported `MISSING` is a real gap unless it is a wording variant: do not stuff it in; list it as a gap or mention it only if the knowledge base supports it. It edits the untouched base CV, trims to the page limit with a clean layout, converts to PDF (needs LibreOffice), runs `verify_pdf.py` and `verify_layout.py`, and prints keyword coverage and cut paragraphs. A second role at the same company uses `--spec spec-<role>.json` with a different `file_name`.
4. Run the Draft Review Pass from `docs/cv-letter-quality.md` (fresh-context reviewer, one revision). Apply fixes by editing the spec and rebuilding with `--force`. The builder refuses to overwrite output on purpose: use `--force` only on a draft that has not been submitted, and rebuild submitted materials with `--out-dir`.
5. Present one package for approval:
   - **Change Summary** - compact list of changes and key keywords added.
   - **What was cut** - removed paragraphs, one line of reason each.
   - **Keyword Coverage Check** - covered / synonym-only / missing (have it) / missing (gap). If a phrase shows as missing, re-check with `pdftotext -layout -enc UTF-8` before concluding; extractors can split words.
   - The tailored CV text in markdown.

## Post-Tailoring Workflow

1. Outputs land in the company folder named by `$P.identity.output_name_pattern` (`.docx` and `.pdf`; PDF is the preferred submission format). Do not add a year to file names; the dated company folder is enough.
2. Before moving the role to `APPLYING`, do the warm-path check from the referral-first rule in `CLAUDE.md`.
3. Update the tracker row: Status `APPLYING` (`tracker_add.py ... update --company <C> --role <R> --status APPLYING`). Change the tracker only with `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/tracker_add.py --workspace . add|update ...` (backup, status and date validation, duplicate check and restyle in one step; exit code 2 means ask the user); never edit the xlsx directly.
5. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cleanup.py --workspace .` (dry run first) if LibreOffice left lock or temp files.

## Important Principles

- **Never invent experience or skills.** Every word must be defensible in an interview. When in doubt, ask.
- **Ask before strengthening claims** not in the knowledge base. The user knows their experience better than any analysis.
- **When the user states, corrects or confirms a fact not in the knowledge base,** write it there in the same turn; otherwise the next session treats it as unsupported and strips it.
- **Readability beats density.** 80% keyword coverage that reads naturally beats 100% that reads like a dump.
- **Keep it concise.** Tailoring must not lengthen the CV; respect the page limit.
- **Respect the base CV.** Adjust emphasis and language; do not redesign.
- **Coordinate with other skills.** Use JD analyzer output; note which gaps are better addressed in a cover letter (only if requested) than the CV.
- Follow the dash rule (`$P.style.forbid_em_dash`): short dash `-`, never an em dash. The builder rejects em dashes in the spec when the rule is on.
