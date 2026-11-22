# Knowledge Base Update Rules

`knowledge-base.md` is the single source of truth. When it changes, cascade updates to dependent files as follows. (Section numbers follow `knowledge-base.skeleton.md`.)

**Event: gap confirmed (rejection feedback received)**
1. Knowledge base §5a: add a narrative entry (source company, date, gap description, action plan).
2. `interview-kb-hard-skills.md` Known Gaps table: add or update the row (Priority + Status + concise Action only; no narrative duplication).
3. Nothing else.

**Event: new STAR story**
1. Knowledge base §7: add the full version with "Use for" tags (authoritative).
2. `interview-kb-soft-skills.md`: add the delivery script only (2-3 sentence spoken version + the question it answers).
3. Never copy the full story verbatim into the soft-skills KB.

**Event: employment or availability change**
1. Knowledge base §1: update the availability line.
2. `profile.yaml`: update any field that encodes it (for example work authorization, accepted locations).
3. Memory files are not the authority for always-in-context operational facts; `profile.yaml` and `CLAUDE.md` are.

**Event: new tailoring pattern proven**
1. Knowledge base §8 only.

**Event: salary or policy rule change**
1. `docs/salary-rules.md` and `profile.yaml` (`compensation`), then the `CLAUDE.md` summary if it states the changed fact.

**Event: gap closed (practice completed, skill confirmed)**
1. `interview-kb-hard-skills.md` Known Gaps table: update Status ("Practiced YYYY-MM").
2. Knowledge base §5a: update the Action note if relevant.

**What does NOT belong in the knowledge base:**
- Technical Q&A answers (those go in `interview-kb-hard-skills.md`)
- Scripted spoken delivery of STAR stories (those go in `interview-kb-soft-skills.md`)
- Salary calculation rules (those stay in `docs/salary-rules.md`)
- Operational workflow rules (those stay in `CLAUDE.md` and `docs/`)
