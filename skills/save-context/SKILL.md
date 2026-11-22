---
name: save-context
description: "Extracts useful information from the current conversation and persists it to the right place: memory files, CLAUDE.md and docs/, the knowledge base, or the interview KB files. Use when the user says \"save context\" or at the end of substantive conversations."
---

# Save Context

Extract valuable information from the current conversation and persist it so future conversations start with better context. Without this, every conversation starts from scratch. `$P` means a field of the workspace's `profile.yaml`.

## What to extract

Extract only what is actually present; not every conversation has every category.

### 1. Feedback on Claude's behavior
Corrections, preferences, things that worked, things that annoyed the user. **Destination:** memory file (type `feedback`).

### 2. Operational rule changes
New workflow rules, policy changes, formatting preferences, tracker schema changes. **Destination:** the file that holds the rule. `CLAUDE.md` is a slim file (always-needed rules and short summaries); the full text of larger rules lives in `docs/` (see the docs index at the bottom of `CLAUDE.md`). Update the `docs/` file first, then update the matching `CLAUDE.md` summary only if the change affects something the summary states (a floor figure, a weight, a threshold, a status name).

### 3. Career facts and achievements
New biographical info, project outcomes, metrics, STAR stories, skill updates. **Destination:** the knowledge base (`$P.paths.knowledge_base`), in the right section.

### 4. Technical gaps confirmed
Gaps revealed by interviews, rejections or self-assessment. **Destination:** the knowledge base's gaps section plus a row in the Known Gaps table of `interview-kb-hard-skills.md`.

### 5. New interview Q&A
Questions encountered in real interviews. **Destination:** `interview-kb-hard-skills.md` (technical) or `interview-kb-soft-skills.md` (behavioral).

### 6. External resource pointers
URLs, tools, services, contacts that could be useful later. **Destination:** memory file (type `reference`).

### 7. Project status and decisions
Decisions made, deadlines, strategic choices, market signals. **Destination:** memory file (type `project`); convert relative dates to absolute.

### 8. User profile updates
Changes to personal info, availability, preferences, location, employment status. **Destination:** memory file (type `user`); cascade to `profile.yaml` (and the `CLAUDE.md` profile section, if the workspace keeps one) when it is an operational fact such as the compensation floor, accepted locations or languages.

### 9. Application form answers
Answers written for form questions ("Why do you want to work here?", salary expectations, motivation text). Similar questions recur across applications, so good answers are reusable.
**Destination:**
1. The company's `analysis.md`: append (or extend) an `## Application Form Answers` section with the Q&A pairs. This keeps each answer tied to the company and JD context.
2. The knowledge base's common-questions section, when the answer contains a reusable pattern (a well-phrased salary justification, a work-authorization explanation, a motivation narrative). Company-specific "why this company" answers do NOT go in the KB.
For CV and letter text that was actually submitted, the company folder's `spec.json` is the record; do not copy it elsewhere.

### 10. Session digest
A 2-3 line "what changed" summary: decisions made, applications processed, problems solved. Not a transcript. **Save only after substantive conversations** (JD analyses, interview prep, CV tailoring, rejection processing, strategy or workflow changes), not after trivial exchanges.
**Destination:** memory file (type `project`) named `session-digest-YYYY-MM-DD.md`; on the same day, append to the existing digest. Keep only the last 10 digests in the `MEMORY.md` index (under a `## Session Digests` section); the older files can stay on disk.

## What NOT to extract

- Things already documented (check first)
- Ephemeral task details ("open file X", "run the script")
- Code snippets without broader significance
- Things derivable from files (git history, file structure)
- Conversation-specific context that will not matter next time

## Routing table

| Information type | Primary destination | Also update |
|---|---|---|
| Claude behavior feedback | Memory (`feedback`) | - |
| Workflow/operational rule | The matching `docs/` file (`workflows.md`, `cv-letter-quality.md`, `humanize-rule.md`, `tracker-schema.md`, `upskill-expand.md`, `workspace-hygiene.md`); small always-needed rules go in `CLAUDE.md` | `CLAUDE.md` summary if it states the changed fact |
| Scoring rubric / gate change | `docs/scoring-rubric.md` | `profile.yaml` scoring block and the `CLAUDE.md` rubric summary |
| Salary/policy rule | `docs/salary-rules.md` | `CLAUDE.md` salary summary; `profile.yaml` compensation if the floor changed |
| CV/letter build tooling change | `docs/build-application.md` | - |
| Career fact/achievement | Knowledge base | - |
| New STAR story | Knowledge base STAR section | `interview-kb-soft-skills.md` (delivery script only) |
| Technical gap confirmed | Knowledge base gaps section | `interview-kb-hard-skills.md` Known Gaps |
| Behavioral Q&A from interview | `interview-kb-soft-skills.md` | - |
| Technical Q&A from interview | `interview-kb-hard-skills.md` | - |
| External resource | Memory (`reference`) | - |
| Project decision/status | Memory (`project`) | pipeline notes if pipeline-related |
| User profile change | Memory (`user`) | `profile.yaml` if operational |
| Application form answer (company-specific) | `<company-folder>/analysis.md` -> `## Application Form Answers` | - |
| Application form answer (reusable pattern) | Knowledge base common-questions section | `<company-folder>/analysis.md` |
| Session digest | Memory (`project`) as `session-digest-YYYY-MM-DD.md` | - |

This table aligns with the knowledge-base update rules in `docs/kb-update-rules.md` (summary in `CLAUDE.md`). When in doubt, those rules are authoritative.

## Execution steps

### Step 1: Scan and classify
For each extractable item: identify the category, draft the content, note the destination.

### Step 2: Dedup, staleness and integrity check
Every write must pass three gates: no duplicates, no stale data left behind, no broken references.

**2a. Dedup**
1. **Memory:** read the `MEMORY.md` index. If an existing memory covers the topic (judge by topic, not title), UPDATE it instead of creating a new file.
2. **CLAUDE.md and docs/:** read the relevant section, and for rules that live in `docs/` the matching file. If the info is present and unchanged, skip. If it contradicts or supersedes, update in place. Keep the `CLAUDE.md` summary and the full `docs/` text consistent; a summary that disagrees with its docs file is a bug.
3. **Knowledge base:** read the target section; check by meaning, not wording ("led a team of 8" and "managed 8 engineers" are one fact).
4. **Interview KBs:** search for the topic or question keyword; update a similar entry if the new answer is better rather than adding a second.
5. **analysis.md:** if the `## Application Form Answers` section exists, append to it.

**2b. Staleness** - replace outdated info, do not layer on top. Update or delete the old entry; two entries that disagree on one topic are worse than none. Examples: a changed salary expectation or availability replaces the old line. If a memory is fully superseded, update its content and description; if the topic shifted enough to need a new file, delete the old one and its index entry. Remove entries tied to dates that have passed and no longer matter.

**2c. Reference integrity** - after all writes verify:
1. Every `MEMORY.md` entry points to an existing file.
2. `[[name]]` links in memory files resolve; remove ones that will not be created.
3. Cross-references from `analysis.md` to knowledge-base sections still exist.
4. A company folder you wrote to matches the tracker's `Folder` column.
5. If you renamed or removed a `docs/` file, update the docs index and every stub in `CLAUDE.md` that points to it.

### Step 3: Save
Follow each destination's format conventions.

**Memory files** use frontmatter:
```markdown
---
name: short-kebab-case-slug
description: one-line summary used for relevance matching
metadata:
  type: feedback|project|reference|user
---

Content. For feedback/project types: rule or fact, then **Why:** and **How to apply:** lines.
Link related memories with [[name]].
```
Then add a pointer line to the `MEMORY.md` index.

**CLAUDE.md and docs/** - edit in place, preserving structure and style. Back up `CLAUDE.md` to `$P.paths.backup_dir` before a structural change (immutability rule). Keep `CLAUDE.md` slim: long rule text belongs in `docs/`.

**Knowledge base** - edit in place in the right section. **Interview KB files** - append to the relevant section in the existing Q&A format.

### Step 4: Report

```
## Saved context

| # | What | Where | Action |
|---|------|-------|--------|
| 1 | Cover letters should use a casual tone | Memory (feedback) | Created `feedback_cover-letter-tone.md` |
| 2 | Compensation floor updated | profile.yaml -> compensation | Updated existing value |
| 3 | System design gap from an interview | Knowledge base gaps section | Added new gap entry |
| 4 | Old availability statement | Knowledge base logistics | Replaced (was stale) |
```

If nothing is worth saving: "Nothing new to persist from this conversation." The Action column says `Created`, `Updated`, `Replaced`, `Removed` or `Skipped (already exists)`.

### Step 5: Context health report

```
## Context health

| Metric | Status |
|--------|--------|
| Memory files | N active, 0 deprecated |
| MEMORY.md index | N/200 lines |
| Session digests | N indexed (max 10) |
| Knowledge base | N lines, last updated YYYY-MM-DD |
| CLAUDE.md | N KB (target: under ~25 KB; move long rules to docs/) |
| Stale entries | None found |
| Broken references | None found |
```

Check for: deprecated memories to delete; orphaned memory files not in the index; index capacity (warn from ~150 lines); stale date references; common-question categories still holding placeholder text; `CLAUDE.md` size and summaries that disagree with their docs file. If everything is clean, one line: "Context health: OK (N memories, M/200 index lines, no issues)". If not, list issues and offer to fix them now.

## Proactive triggering

When triggered proactively (not by command) apply a higher bar: only extract things with clear future value, prefer fewer high-quality saves, and if you find only 1-2 minor items say "Nothing significant to persist".

## Important constraints

1. **Never save sensitive personal info** (government IDs, bank details, medical specifics) unless explicitly asked.
2. **Never contradict authoritative sources.** `CLAUDE.md`, its `docs/` files, `profile.yaml` and the knowledge base are sources of truth; flag a conflict instead of overwriting.
3. **Always read before writing.**
4. **Respect the cascade rules** in `docs/kb-update-rules.md`.
5. **Convert relative dates** ("next Thursday") to absolute dates (YYYY-MM-DD).
6. **Keep memory files focused:** one topic per file.
7. Never copy private workspace content into the public plugin repository.
