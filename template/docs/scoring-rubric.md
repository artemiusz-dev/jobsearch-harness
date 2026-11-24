# JD Fit Scoring Rubric

**Authority:** this rubric is the single source of truth for Match %, the compensation floor, employment-type rules, location rules, eligibility and language gates. It overrides the `jd-analyzer`, `job-scanner` and `cv-tailor` skills wherever they conflict. All numbers marked `$P.` come from `profile.yaml` (the schema defaults are shown).

A reproducible weighted score. Use it whenever `jd-analyzer` runs (or any JD is analyzed manually). The Overall Score is the value written to the tracker's `Match %` column and must appear in `analysis.md` as `**Overall Score: NN** - <Verdict>` with a `Rubric: <version>` line.

## Step 0 - Liveness gate (before any scoring)

Check the posting is open: not closed, filled or expired; "not accepting applications" absent; apply link works. If closed: do NOT write a full analysis. Add or update the tracker row as `SKIP` with Next Action "Posting closed (date); re-check if reposted", and stop. A repost is a new check, not a reason to reuse an old score.

## Weighted dimensions (sum = 100%)

| Dimension | Weight (`$P.scoring.weights`) | 80-100 | 60-79 | 40-59 | 0-39 |
|---|---|---|---|---|---|
| Technical Skills Match | 0.30 | Core requirements are the profile's primary stacks (`targets.stacks.primary`); secondary stacks count where the role preset says so | Most requirements match, 1-2 learnable gaps | Partial match, real upskilling needed | Fundamental mismatch |
| Experience Match | 0.20 | Domain and seniority/scope match (ownership, mentoring, similar product or domain). Judge scope and domain only; the stack is scored above | Related domain or scope, transferable | Adjacent, the case must be made | Unrelated |
| Behavioral/Culture Fit | 0.10 | Product ownership, low risk of an excluded company type, sane pace | Mostly compatible, minor friction | Some friction (see the knowledge base's notes on culture fit) | Significant mismatch |
| Career Alignment | 0.25 | Matches `targets.roles` and `seniority`, clear growth | Good role, partially aligned | Does not build toward goals | Backwards step |
| Compensation | 0.15 | Top of range at or above the outward ask and best net comfortably above `floor_net` | Clears the floor with margin | At the floor, or salary not listed (score `unlisted_salary_score`, default 50, and flag it) | Below the floor (also fails the gate) |

Role presets (`presets/roles/<role>.yaml`) supply role-specific wording for these rows through `rubric_hints` in the merged profile (`technical`, `experience`, `culture`, `career`); show the hint next to the 80-100 band when scoring. The profile's own `rubric_hints` override the preset.

`Overall Score = Σ weight × dimension score`

**Technical depth-risk adjustment:** the Technical score measures stack match, but past tech-stage rejections may come from depth gaps. If the JD or the known process stresses topics listed in `$P.scoring.depth_risk_keywords` (record yours from rejection feedback), subtract 5-10 from Technical and state it in the row note. This is a prep-fixable risk: it lowers the score but is not a gate.

## Pass/fail gates (not weighted, override the score)

Each gate can be switched off in `$P.scoring.gates`.

- **Employment type:** compute net for every offered structure (see `docs/salary-rules.md`). PASS if any structure in `$P.compensation.employment_types` (empty = all) is offered and the best achievable net is at or above `floor_net` and gross at or above `floor_gross`. FAIL otherwise.
- **Location:** PASS if the role matches an entry of `$P.locations.accepted` (place and mode). Elsewhere onsite or hybrid: FAIL unless the entry allows relocation and a package is stated or not required.
- **Technical floor:** Technical below `$P.scoring.technical_floor` (default 45) caps the verdict at **Moderate Fit** (discuss with the user).
- **Eligibility (run before scoring):** read the posting's work-rights wording verbatim. A requirement matching `$P.work_authorization.hard_stop_phrases` (citizenship, permanent residency, security clearance) that the user cannot meet is a **hard stop FAIL**: do not score or draft; quote the exact line to the user (they may know something the profile does not). A posting that names work permits or international candidates as welcome passes. Silent on citizenship: proceed but mark "eligibility unverified" and check the employer's careers or FAQ page before drafting if the sector is regulated (defence, government, banking, telecom, critical infrastructure). A company-wide "we welcome international applicants" is not role-level permission. Ambiguous wording ("EU work permission required", "valid work permit", "right to work in <country>") is never a quiet PASS: write `Eligibility: FLAG, user decides`, quote the line and name the question to ask the recruiter. A residence permit in one country does not by itself give work rights in another: flag the work-rights question to the user (verify per country, do not assume).
- **Language (run before scoring):** compare the language the role needs as a job condition (not the language the ad is written in) with `$P.languages.spoken`. A required language not on the list: **FAIL**, quote the line. A listed language required above the stated level ("fluent", "C1/C2", "native", "business level"): **FLAG, not fail**; score and draft normally, state both the posting's bar and the stated level, and let the user decide. Never claim a higher level than the profile states.

If a gate fails, cap the verdict at **Skip** (technical floor: Moderate) regardless of the numeric score, and say so explicitly ("Score would be X, capped to Skip - [gate] fails").

## Thresholds (`$P.scoring.thresholds`, defaults shown)

| Score | Verdict |
|---|---|
| 75+ | Strong Fit - apply, tailor everything |
| 60-74 | Good Fit - apply, address gaps in the cover letter if one is requested. At or above `apply_this_week_from` (68): apply this week; below: apply only if the pipeline is thin or there is a warm path |
| 45-59 | Moderate Fit - discuss with the user before proceeding (never auto-add to the backlog) |
| 30-44 | Weak Fit - skip unless a strategic reason applies (referral, name brand, direct network contact) |
| <30 | Poor Fit - skip |

## Output

Present the dimension table (with a brief note per row), the arithmetic line (`Overall = 0.30 x T + ... = NN.N`), the gates line, then `**Overall Score: NN** - <Verdict>`, in addition to the must-have/nice-to-have and red-flag sections. Log the Overall Score as `Match %` in the tracker. Mark analyses with `Rubric: <version>`.

## Versions and calibration

- Keep a short changelog here when you change weights or thresholds (date, what changed, why). Old scores are NOT recomputed; compare scores across rubric versions with care.
- Record the outcome per application by filling the tracker stage columns (Intro Call, Assignment, Tech Interview, Final Interview, Offer / Rejected) as events happen. After about 30 applications with outcomes, compare conversion by score band and re-tune weights and thresholds. `python3 <plugin>/scripts/tracker_query.py --workspace . bands` prints the funnel by Match % band (live and archives are reported separately and must not be compared directly across rubric versions).

## Calibrating the thresholds

The default weights and thresholds are not calibrated to your market. Two scripts show whether they should change:
- `python3 <plugin>/scripts/tracker_query.py --workspace . calibrate` counts, per Match % band, the applications old enough to have had a reply (`--mature-days`, default 14) and how many got one, with a 95% interval. It ends with a plain verdict: bands with fewer than 30 applications are marked `*` and ignored, and thresholds are worth moving only when a higher band replies significantly more often than a lower one (intervals do not overlap). With overlapping intervals the score does not yet predict replies: keep the thresholds.
- `python3 <plugin>/scripts/score_compare.py [--reference old-analysis.md] run1.md run2.md run3.md` summarizes several analyses of the same posting (overall and the five dimensions: mean, range, difference to a reference). One run is noisy by a few points; compare means before blaming the rubric or the profile.

Record any change to weights or thresholds in the changelog above with the date and the numbers that justified it.
