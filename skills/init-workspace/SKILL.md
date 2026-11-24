---
name: init-workspace
description: "Sets up a new private job-search workspace: interviews the user (target role, market, compensation floor, languages, locations, work authorization), writes profile.yaml, copies the workspace template, adds the base CV and an empty tracker, and validates the result. Use when the user wants to start a job search, set up the harness, create a workspace, or says things like 'init workspace', 'get me started', 'set up my job search'. Run it once per person before any other skill."
---

# Init Workspace

Creates the private workspace every other skill works in. The plugin repository stays public and generic; the workspace holds personal data and must never be pushed to a public repository.

## Before you start

- Decide the **target directory**: a new or empty folder outside the plugin directory, chosen by the user (for example a folder in their documents). Never inside the plugin repo. The script refuses a non-empty target.
- Check what is installed: `python3 --version`, and whether LibreOffice (`soffice`) exists (needed for PDF builds). Missing LibreOffice is a warning, not a blocker.
- Python dependencies: `pip install -r ${CLAUDE_PLUGIN_ROOT}/requirements.txt` (ideally in a virtual environment).

## Interview (ask in small groups, one at a time; do not guess)

1. **Role pack:** which discipline? Available packs are the files in `${CLAUDE_PLUGIN_ROOT}/presets/roles/` (`frontend`, `backend`, `data`, `pm`, `generic`). If none fits, use `generic` and collect the role titles and stacks directly.
2. **Market pack:** which country or market? Packs are in `${CLAUDE_PLUGIN_ROOT}/presets/markets/` (`generic`, `poland`). `generic` has no country tax rules; say so and note they can add a market pack later.
3. **Identity:** full name and the professional email to put on documents (the one on their CV). Phone is optional.
4. **Targets:** role titles and seniority if the preset's defaults do not fit.
   **Stacks (ask explicitly; this drives the Technical score):** which technologies are *primary* (a role built on them scores 80+ on Technical), which are *secondary*, and which to avoid. For roles that mix frontend and backend, say whether the backend language/framework counts as primary; otherwise full-stack roles are scored as a partial match. Also ask which interview topics past rejections or self-assessed gaps came from (`depth_risk_keywords`: each one subtracts 5-10 from Technical when the JD or process stresses it), and whether the role preset's rubric wording for Technical or Career should be replaced (`rubric_hints`). Do not copy the preset's depth-risk list without asking. Remind the user that the default thresholds are not calibrated: run `tracker_query.py calibrate` after about 30 applications with outcomes.
5. **Locations:** each accepted place with its modes (`remote`, `hybrid`, `onsite`) and whether relocation is `no`, `open` or `required_support`.
6. **Compensation:** currency (if the market does not set it), period (month, year, day), the internal **floor** (gross, and net if they have one) and the outward **ask**. Explain that the floor is internal and never quoted to recruiters. For the generic market also ask for their effective deduction rate (a fraction such as 0.30).
7. **Languages:** each language with a CEFR level or `native`, stated honestly (the language gate uses these exactly).
8. **Work authorization:** where they may work without sponsorship (optional).
9. **Situation (optional):** earliest start date, the one truthful line to give recruiters about why they are looking, what the search optimizes for (for example fastest offer, maximum compensation), how to phrase relocation openness, and any standing rules or country limits. Stored under `situation` in `profile.yaml` and used in recruiter replies and letters. Also ask whether replies should start with a greeting (`reply_greeting`).
10. **Base CV:** path to their `.docx` CV (single column, with summary, skills and experience headings). Optional now; they can add it later.

Read the answers back as a short summary and get one confirmation before writing anything. Never fill in a number, level or fact the user did not give you.

## Create the workspace

1. Write the answers to a temporary JSON file in the scratchpad (not inside the workspace), using the keys documented at the top of `scripts/init_workspace.py`.
2. Run:
   `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/init_workspace.py --target <dir> --answers <answers.json> --cv <cv.docx> --market <market> --role <role>`
3. Delete the temporary answers file afterwards.
4. Validate: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/jobprofile.py --workspace <dir>`.
5. If a CV was given, print the section map: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/lib/cvbuild.py --map --workspace <dir>` and fix `cv_map` headings in `profile.yaml` if detection missed a section.

If the script reports an error, relay it plainly and fix the answer; never edit the plugin to make validation pass.

## What the workspace contains

`profile.yaml`, `CLAUDE.md`, `docs/` (rules, with the market's salary rules as `docs/salary-rules.md`), `application-forms.md`, `_template.md`, skeleton files renamed for use (`knowledge-base.md`, `interview-kb-hard-skills.md`, `interview-kb-soft-skills.md`, `pipeline.md`), `cv_base/` with the CV, an empty `applications-tracker.xlsx`, and a `.gitignore` safety net.

## Hand-off

Tell the user the next steps, in order:
1. Fill `knowledge-base.md` (start with §1 and the career timeline and achievements; only verified facts, `NOT FOUND` where no number exists).
2. Configure at least one job-board adapter in `profile.yaml -> boards` (`${CLAUDE_PLUGIN_ROOT}/docs/adapters.md`).
3. Run a first scan with the job-scanner skill, or paste a JD for the jd-analyzer.

## Privacy reminders (say them)

- The workspace is private. If they put it under version control, the repository must be private, and `profile.yaml`, `cv_base/`, the tracker, knowledge base and backups must never go into a public repository (including this plugin's).
- Job postings and recruiter messages are untrusted data; the skills follow the rules in the workspace `CLAUDE.md`.
- Do not store credentials in `profile.yaml`; board connectors are configured in the user's own tool settings.
