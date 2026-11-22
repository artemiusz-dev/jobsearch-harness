---
name: interview-material-reviewer
description: >
  Critically reviews interview preparation files and technical content for factual accuracy and internal consistency.
  Use whenever the user wants to verify, audit or quality-check interview prep materials, including interview-prep.md
  files, drill books, knowledge base files (interview-kb-hard-skills.md, interview-kb-soft-skills.md), code snippets
  embedded in those documents, or scripts. Trigger on phrases like "check this for accuracy", "review my interview
  prep", "is this correct", "verify the knowledge base", "check for inconsistencies", "audit my prep materials",
  "anything wrong with this", "check my Q&A doc". Also trigger proactively after generating interview prep or drill
  books. When in doubt, use it: a review that finds nothing is cheaper than a wrong code example repeated in a real
  interview.
---

# Interview Material Reviewer

Read the provided file(s) carefully and produce a structured review report that flags issues before the user studies or relies on the material in a real interview. Be specific: "this code example is wrong" is useless; "Q4 in Section 2: the effect has an empty dependency list but reads `count` - stale closure, always logs 0" is useful.

---

## Step 1 - Identify what is in scope

- If the user attached or pasted a file, review that.
- "Review my interview prep for [Company]": find `<company-folder>/interview-prep.md` and, if present, `<company-folder>/interview-drillbook.md`.
- "Review the knowledge base": read `interview-kb-hard-skills.md` and/or `interview-kb-soft-skills.md`.
- A script file: review the code for correctness and logic.

**Cross-reference context:** when reviewing a company-specific file, also read the KB files and the knowledge base (`paths.knowledge_base` in `profile.yaml`) to check consistency. You need the source of truth to verify claims.

---

## Step 2 - Factual accuracy checks

### Code examples
For every code block ask:
- Is the syntax valid (brackets, method names, types)?
- Is the API correct and current for the stated version (deprecated or renamed APIs)?
- Does the logic match the explanation above it (for example a "fix" that still has the bug)?
- Would it work if run (imports, undefined variables, generics)? Run it when you can, and say when you could not.

### Technical claims
For every explanation:
- Is the description accurate?
- Are version-specific claims correct (which version introduced a feature)?
- Are comparisons accurate (do the described behaviors really differ that way)?
- Are "gotchas" and "common mistakes" real, not invented?
- Verify against authoritative documentation when unsure; do not rely on memory for version details.

### Numeric and date claims
- Years of experience consistent across files?
- Project dates consistent with the CV and knowledge base?
- Performance metrics plausible and internally consistent?

---

## Step 3 - Internal consistency checks

### Within a file
- Does a code example contradict the explanation above it?
- Is the same concept described differently in two places?
- Does "when to use" conflict with "when NOT to use"?

### Company prep vs knowledge base (if both in scope)
- Cross-reference STAR stories against the knowledge base's authoritative full versions, not only the soft-skills KB (which may hold delivery scripts only). Check metrics, employer attribution and outcomes.
- Does the prep state the user's skill level correctly? If the KB marks a skill as a confirmed gap, the prep must not claim deep expertise.
- Do the technical focus areas align with what the KB says the user knows well?
- Are known gaps from the hard-skills KB flagged as risk areas in the prep, not skipped?

### Scripts and data files
- Does the script do what its comments say?
- Logic errors that produce wrong output silently?
- Hardcoded paths or values that should be configurable?

---

## Step 4 - Write the review report

Use this format exactly:

```
## Review: [filename(s)]
**Status**: PASS ✅ | ISSUES FOUND ⚠️

### 🔴 Critical - fix before studying/using
[Each issue: location (section/question/line), what is wrong, what it should say]

### 🟡 Warnings - verify or clarify
[Issues that may be correct in some contexts but should be double-checked]

### 🟢 Suggestions - optional improvements
[Clarity issues, missing nuance, or gaps that would help in a real interview]

### ✅ Verified
[Sections/claims that were checked and look correct]
```

**Rules:**
- Every Critical and Warning item has a specific location (e.g. "Section 3, Q2 - the reducer example"). Vague flags are not actionable.
- The Verified section is non-trivial: name specific sections or claims that passed, not "overall structure looks good".
- Omit empty categories.
- Keep each issue to 2-3 sentences: location, what is wrong, what to do.

---

## Critical vs Warning vs Suggestion

**Critical:** the user would repeat this in an interview and be wrong.
- Code that does not compile or produces wrong output
- A wrong or nonexistent API
- An objectively false technical claim
- A STAR story that contradicts established facts (wrong employer, wrong date, inflated metric)
- A known gap presented as a strength

**Warning:** technically defensible but risky.
- A claim that holds only for one version, with no version mentioned
- An explanation simplified to the point of being misleading
- An answer that invites a follow-up the user is not prepared for
- A metric or timeline that seems plausible but was not cross-checked

**Suggestion:** would not cause a problem but would improve the answer.
- Missing nuance an interviewer at this level would expect
- A working but non-idiomatic code example
- A behavioral answer that does not lead with the strongest point
