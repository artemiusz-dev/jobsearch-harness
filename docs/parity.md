# Rule parity matrix

Every kind of personal rule a job search needs, and the one place it lives. If a rule is not in this table it has no
supported home, which is a bug in the harness. Values are never written here: they live in the user's `profile.yaml`
(layer 1) or in the workspace `docs/` (layer 2). Skills and scripts (layer 3) only read them.

Status: **profile** = enforced by schema, **doc** = prose rule in a workspace doc, **logic** = behaviour in a skill that reads the profile.

| Rule category | Layer | Where | Status |
|---|---|---|---|
| Target roles, seniority, stacks (primary, secondary, avoid, known gaps) | profile | `targets.*` | profile |
| Search tracks (for example frontend and a full-stack wave, tags, countries) | profile | `targets.search_tracks` | profile (0.6.0) |
| Company blacklist, whitelist, watch list, never-contact | profile | `targets.companies` | profile (0.6.0) |
| Excluded industries, consulting or agency handling | profile | `targets.excluded_industries`, `targets.avoid_company_types` | profile |
| Salary floor, ask, currency, employment types, floors per type | profile | `compensation.*` | profile |
| Net formulas and market constants | profile + preset | `compensation.net_rule`, `market_params.*`, `netcalc.py` | profile |
| Compare in net, never quote net, form-field policy | profile | `compensation.compare_in`, `never_quote_net`, `ask_answer_policy` | profile (0.6.0) |
| Accepted locations, relocation openness, target countries | profile | `locations.*`, `work_authorization.target_countries` | profile |
| Permits, sponsorship, form wording for work rights | profile | `work_authorization.*` | profile |
| Spoken languages and language gate | profile | `languages.*` | profile |
| Score weights, thresholds, technical floor, gates | profile | `scoring.*` | profile |
| Custom gates and score modifiers | profile | `scoring.gates.custom`, `scoring.modifiers` | profile (0.6.0) |
| Depth-risk topics and penalty | profile | `scoring.depth_risk_keywords`, `depth_risk_penalty` | profile |
| Posting health (age, applicants, layoffs, recruiter activity) | profile | `scoring.posting_health` | profile (0.6.0) |
| Skill signal lists (strong, partial, gap) | profile | `scoring.signal_stacks` | profile (0.6.0) |
| Job boards, per-board filters, keywords, freshness | profile | `boards[]` | profile |
| Follow-up cadence, per-status windows, marker, max count, history window | profile | `followups.*` | profile (0.6.0) |
| Referral and warm-path policy | profile | `referral.*`, `followups.referral_first` | profile (0.6.0) |
| Tracker columns, stages, statuses, status roles, default new status | profile | `tracker.*` | profile (scripts read it from 0.7.0) |
| Backup before every tracker change, never overwrite a backup | doc + script | `tracker_add.py`, `docs/tracker-schema.md` | fixed rule |
| Banned phrases (global and per channel) | profile | `style.banned_phrases`, `style.channel_banned_phrases` | profile (0.6.0) |
| Length limits (letter, DM, replies, follow-ups, form fields) | profile | `style.limits` | profile (0.6.0) |
| Tone, languages of outputs, address the reader directly | profile | `style.*` | profile (0.6.0) |
| Em dash ban, reply greeting | profile | `style.forbid_em_dash`, `style.reply_greeting` | profile |
| CV format (paper, pages, date format), frozen facts, research cache | profile | `cv.*` | profile (0.6.0) |
| Letter salutation, closing, only-on-request | profile | `letter.*` | profile (0.6.0) |
| Contact-address guard, confidential employers, never-mention topics | profile | `identity.*`, `privacy.*` | profile (0.6.0) |
| Trusted ATS domains, untrusted-input policy | profile | `security.*` | profile (0.6.0) |
| Reason for leaving, availability, relocation wording, side-work policy | profile | `situation.*` | profile |
| Scoring rubric prose, salary rules, workflows, humanize rule | doc | workspace `docs/` | doc (numbers in these docs come from the profile) |
| Knowledge-base cascade, rejection handling, interview conventions | doc | workspace `docs/kb-update-rules.md`, `workflows.md` | doc |
| Prior-application check within the history window | logic | `job-scanner`, `jd-analyzer`, `cv-tailor`, `recruiter-responder` | logic (0.7.0) |
| Draft review pass, grounding audit, keyword coverage | doc | `docs/cv-letter-quality.md` | doc |

## Precedence
Market preset, then role preset, then `profile.yaml`. Dicts merge key by key. **Lists are replaced, not appended**: a
list in `profile.yaml` (for example `style.banned_phrases` or `security.trusted_ats_domains`) replaces the preset or
schema default. Add channel-specific extras through `style.channel_banned_phrases`, which is always appended.

## Defaults
A default exists in exactly one place, `config/profile.schema.json`. `init_workspace.py` copies defaults from it; docs
that quote a default are checked against it by the tests.
