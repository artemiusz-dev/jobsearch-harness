---
name: interview-drillbook
description: "Generates a comprehensive Q&A technical drill book for a specific interview, with code examples and full behavioral answers. Use whenever the user says things like 'make a cheatsheet for my interview', 'prepare Q&A for the interview', 'write a study guide', 'I need something to study before the interview', 'technical Q&A for [company]', 'make me a drill book' or any request to produce a study or reference document ahead of a specific interview. Also trigger after the interview-prep skill when the user asks 'what do I study' or 'what do I review'. Complementary to interview-prep: prep = strategy, drillbook = what you actually study."
---

# Interview Drillbook

Generates a dense, self-contained Q&A study document for a specific interview: the document the user opens the night before. Not strategy but execution: real questions with full answers and code examples.

This skill builds on the `interview-prep` output. If `interview-prep` has not run for this company, run it first (or read the JD analysis to infer the relevant areas). `$P` means a field of the workspace's `profile.yaml`. Read it merged with the role and market presets, not as the raw file: run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/jobprofile.py --workspace . --json` once and use that output (preset values such as `avoid_company_types` and `scoring.depth_risk_keywords` are not in the raw `profile.yaml`).

## Context

Read before generating:
- `interview-kb-hard-skills.md`: the technical KB with Q&A and code examples
- `interview-kb-soft-skills.md`: all STAR stories and behavioral answers
- `<company-folder>/interview-prep.md`: company-specific focus areas, gap analysis, story mapping (if it exists)
- `<company-folder>/analysis.md`: JD requirements and match/gap assessment

Skeletons for the two KB files are in the plugin's `template/` directory.

## Step 1: Identify Target and Load Prep

Determine company and role from the message. Check the tracker (`$P.paths.tracker`) for the company folder.

Read in order (skip if missing):
1. `interview-prep.md`: technical assessment format (live coding / system design / knowledge Q&A), focus areas and gaps, the STAR story mapping table, any company-specific questions from research
2. `analysis.md`: must-have requirements and tech stack
3. `interview-kb-hard-skills.md`: the technical Q&A bank
4. `interview-kb-soft-skills.md`: the behavioral Q&A bank

If `interview-prep.md` does not exist, say so, proceed from the JD analysis alone, and ask whether to run `interview-prep` first.

## Step 2: Select and Filter Content

The KB files are comprehensive; the drillbook should be focused.

### Technical section selection
From `interview-kb-hard-skills.md`:
- **Always include** sections tied to required skills in the JD.
- **Include** relevant secondary sections if the JD lists them as nice-to-have or the user has gaps there.
- **Exclude** sections with no relevance to this role.
- **Always include** the fundamentals sections that come up universally for the discipline (for example the core language's internals).

For each selected section keep all Q&A entries, all code examples, and any "Real-world use" context lines (these connect answers to actual experience).

### Behavioral section selection
From `interview-kb-soft-skills.md`:
- Include all standard HR questions (tell me about yourself, why leaving, why this company).
- Include every STAR story, annotated with the requirements it maps to (from the `interview-prep.md` mapping table if available).
- Include the salary/logistics section. Compensation answers use `$P.compensation.ask_gross`, never the internal floor.

### Company-specific questions
If `interview-prep.md` has predicted questions based on research (not merely inferred from the JD), put them in a dedicated section at the top.

## Step 3: Generate the Drillbook

A Markdown file organized for scanning, not reading top to bottom: clear `##` and `###` headers, every question bolded, fenced code blocks with language tags.

```
# Interview Drillbook: [Company] - [Role]
Generated: [date]
Focus areas: [comma-separated main technical topics]

---

## HOW TO USE THIS DOCUMENT
[2-3 lines: scan the focus areas, go deep on flagged sections, review STAR stories the night before]

---

## PART 1: COMPANY-SPECIFIC PREP
[Only if interview-prep.md had researched company-specific questions]
### Predicted questions based on [sources]
**Q: [question]**
A: [key points to hit, not a full script]

---

## PART 2: TECHNICAL Q&A

### [Section name from the KB]
> Relevance: [one line on why this matters for this role]

**Q: [question from the KB]**

[Full answer from the KB, verbatim]

```<language>
// Code example from the KB, verbatim
```

⚡ **To mention in interview:** [1-2 sentence real-world hook from the user's experience, from the KB "Real-world use" lines or the knowledge base achievements]

---

## PART 3: BEHAVIORAL Q&A

### Standard HR Questions
**Q: [question]**
[Full scripted answer from the soft-skills KB]
**Adapt for [Company]:** [one sentence on what to emphasize or change]

### STAR Stories
**Story: [name]**
Maps to: [requirements from this JD]
**Full version:** [STAR from the KB]
**30-second version:** [2-3 sentences]
**What to emphasize for [Company]:** [specific angle]

---

## PART 4: GAP SCRIPTS
**Gap: [technology/skill]**
**If they ask about it:** "[ready-to-use sentence from interview-prep.md]"
**Adjacent experience to mention:** [what to pivot to]

---

## PART 5: QUESTIONS TO ASK THEM
[5-7 questions from interview-prep.md or the soft-skills KB, as a simple list]

---

## QUICK REFERENCE CARD
[Condensed cheat sheet of the most likely questions with one-line answer hooks: memory triggers for a 10-minute review right before the call.]

| Topic | Key point to remember |
|---|---|
| ... | ... |
```

### Quality rules
- **Preserve code examples exactly.** Copy from the KB verbatim; do not paraphrase or "simplify". The user may need exact syntax.
- **Annotate with real experience.** Every technical section has at least one "⚡ To mention in interview" line tied to the user's actual work history. Use only facts from the knowledge base.
- **Do not pad.** Include every Q&A the KB has on a topic, and add no generic filler questions that are not in the KB. The KB is the source of truth.
- **Behavioral answers are complete.** Full scripted answers, not summaries; the user internalizes phrasing from them.
- **STAR stories: both versions.** Full for deep practice, 30-second for quick recall. If the KB has no compressed version, write one from the full version without adding facts.
- **Gap scripts are phrased.** Write the actual sentence the user can say, not "explain that you do not know X but...". Example shape: "I haven't worked with X directly, but I've done extensive work with Y - the model is very similar and I'd expect a quick ramp-up."
- **Quick Reference Card is last,** scannable: one row per topic, one phrase per row.

## Step 4: Save and Update

1. Save as `<company-folder>/interview-drillbook.md`.
2. No tracker status change is needed: the drillbook is prep support.
3. Run the `interview-material-reviewer` checks yourself on the saved drill book before presenting it (read-only; save the report next to it). Drill books copy answers from the interview knowledge bases, and those can contain claims the knowledge base does not support, so list the critical findings in your summary instead of leaving the review to the user.
4. Tell the user the file and the review report are saved, highlight the top 2-3 sections most critical for this role, and name the critical review findings.

## Important Principles

- **A study document, not a strategy document.** No "consider reading about X". Include the actual content; the user should not need to go anywhere else.
- **Code examples are non-negotiable** wherever the KB has code.
- **The 30-second story versions matter.** Interviews move fast.
- **Flag gaps prominently** with a `⚠️ GAP:` prefix.
- Follow the dash rule (`$P.style.forbid_em_dash`): short dash `-`, never an em dash.
