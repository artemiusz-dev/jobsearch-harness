# Application Form Fields (free-text boxes in ATS portals)

A third artifact next to the CV and the cover letter. Many portals (Workday, Greenhouse, Lever, SmartRecruiters, company forms) ask for text typed into a box with a limit and no formatting. Adapted from the "application forms" idea in github.com/MadsLorentzen/ai-job-search (MIT; see THIRD_PARTY_LICENSES.md), rewritten for this workspace.

Applies the **Humanize Output Rule** (`docs/humanize-rule.md`) and the human-text skill. Short dash `-` only. Cover letters are NOT written unless asked, but form fields the portal requires are always answered.

## When to use

Any time the posting or portal asks for: a self-introduction ("tell us about yourself"), structured project entries (name, role, dates, description), a short pitch under a character limit, a motivation question ("why us"), a competency question under a word cap, a salary expectation, notice period or availability, work authorization.

## Governing rule

Every claim must trace to the knowledge base or the base CV (`cv_base/`). A form field selects and arranges true facts for the question asked. It never adds claims, inflates scope or fills space, and must not contradict the CV submitted for the same role. If the user supplies a new fact while drafting, write it to the knowledge base in the same turn (see "Grounding and fact write-back" in `docs/cv-letter-quality.md`).

## Field types

**Self-introduction (100-200 words, one paragraph, no formatting).**
1. Current status in one clause.
2. The strongest single piece of evidence with its number (only numbers present in the knowledge base; "NOT FOUND" means no number, never invent one).
3. One line of trajectory only if it is genuinely relevant.
4. What the user wants next, tied to this employer's actual product or stack in the last sentence.
Lead with strongest evidence, not chronology. Write one version per role type if the profile targets several, and label which goes where. State the word count and name the first sentence to cut if the portal truncates.

**Project entries (name, role, start, end, description).**
- Name: a descriptive project name, not the employer name.
- Role: the role on that project, never upgraded above the CV title.
- Dates: the dates the user worked on that project (not automatically the employment dates). Never invent a boundary.
- Description: 100-150 words (what it did and who used it, the hardest technical problem and how it was solved, the outcome with a number) plus a ~60-word short version.
- Scope discipline: where the user contributed rather than owned, say so. Respect confidentiality: use only facts tagged `[PUBLIC-SAFE]` in the knowledge base; `[INTERNAL-ONLY]` stays out of forms.

**Hard character limits ("stand out in 140 characters").**
Pick the single most distinctive true thing (a number, an unusual combination, a problem shape that maps onto the employer's). Draft 4-6 candidates at different angles. **Count characters with code, never estimate:**
`python3 -c "import sys; [print(len(l.rstrip('\n')), l.rstrip('\n')) for l in sys.stdin]" < candidates.txt`
Present all candidates with counts and recommend one.

**Motivation and competency questions under a word cap.** Answer exactly what is asked. Use a STAR story from the knowledge base §7 (authoritative), trimmed to the cap. Count words with code. "Why us" uses only verified company facts (the company research cache).

**Salary expectation field.** The internal floor is never quoted. Use the outward ask (`profile.yaml` -> `compensation.ask_gross`; state the contract type if the field asks). If the field is numeric-only, enter the outward ask, not the floor. Record any figure given in the tracker's salary column.

**Availability / notice period.** From the knowledge base §1 (available from the date stated there). Give a reason for leaving only if asked, and keep it truthful and brief.

**Work authorization.** From `profile.yaml` -> `work_authorization` and the knowledge base. Answer exactly the question asked: some forms ask about the right to work in one country, others in a region. Do not generalize beyond what the user's status covers; if the field concerns a place `authorized_in` does not list, flag it to the user instead of answering.

**Language fields.** Declare levels exactly as in `profile.yaml` -> `languages.spoken`. Never round up.

## Output

Save one plain `.txt` per employer next to the application: `<company-folder>/application-fields.txt`. Include a header (employer, role), each field labelled with its word or character count, short variants, and clearly marked `NOTE TO SELF` blocks (scope reminders, prepared answers to questions the text invites). `NOTE TO SELF` is never pasted into the form. Add a dates quick-reference so date fields stay consistent across fields.

## Verify before handing over

- [ ] Every claim traces to the knowledge base or the base CV
- [ ] No contradiction with the CV submitted for the same role
- [ ] Ownership scoped correctly on contributory work; no `[INTERNAL-ONLY]` facts
- [ ] Word and character counts measured with code
- [ ] Banned-phrase scan from the Humanize Output Rule done; short dashes only
