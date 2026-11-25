---
name: followup-tracker
description: "Scans the applications tracker for overdue follow-ups and drafts follow-up messages. Use whenever the user says things like 'what needs follow-up', 'any overdue applications', 'check my pipeline', 'what's stale', 'pipeline review', 'morning check' or 'what needs attention today'. Also trigger when the user asks about application status, next actions or pipeline health, and suggest it proactively when the user mentions waiting to hear back from a company."
---

# Follow-Up Tracker

Reads the applications tracker, identifies applications that need follow-up based on time rules, and drafts ready-to-send messages for LinkedIn or email. `$P` means a field of the workspace's `profile.yaml`. Read it merged with the role and market presets, not as the raw file: run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/jobprofile.py --workspace . --json` once and use that output (preset values such as `avoid_company_types` and `scoring.depth_risk_keywords` are not in the raw `profile.yaml`).

## Context

The tracker is `$P.paths.tracker`, sheet `$P.tracker.sheet`. Column headers come from `$P.tracker.fields` and `$P.tracker.stages`. Timing comes only from `$P.followups`: `first_after_days` and `second_after_days` (a status listed in `by_status` overrides them), `max_followups`, `stale_after_days`, `marker`, `history_window_days`, `referral_first`, `draft_only`. This skill states no day counts of its own; if a number below seems missing, it is in the profile.

For a quick mechanical pass, run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/tracker_query.py --workspace . quiet`; it lists rows whose status is in `$P.tracker.status_roles.open_for_followup`, quiet for their first-follow-up window, with fewer than `max_followups` logged follow-ups (counted from `$P.followups.marker` in the next-action column) plus stale-sweep candidates. Then apply the full rules below.

## When Triggered

1. Read the tracker for the current pipeline state with `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/tracker_query.py --workspace . summary` (rows per status, stage counts, age of open applications) and `... quiet` for the candidates. Never read the xlsx with your own `openpyxl` snippet: the system Python usually lacks it and the plugin scripts install what they need.
2. Compute days since last activity for each active application.
3. Classify each by urgency.
4. Draft follow-ups for overdue items.
5. Present a pipeline health summary.

## Step 1: Read the Tracker

Extract all rows with the columns named in `$P.tracker.fields` and `$P.tracker.stages`.

Filter to **active applications only**. Skip statuses in `$P.tracker.status_roles.closed` and the offer status. Monitor the statuses in `open_for_followup`, `replied` (except offer) and `in_progress`. Always use the profile's status names, never literals from this document.

## Step 2: Calculate Staleness

`last activity` = the most recent non-empty date across the stage columns, the applied column and any `$P.followups.marker` date, or the updated column if none. `days_since_activity = today - last activity`.

## Step 3: Classify by Urgency

Per status, take `(first, second)` from `$P.followups.by_status[<status>]`, falling back to `first_after_days` and `second_after_days`.

### Statuses in `open_for_followup` (applied, CV sent)
- Under `first`: on track.
- `first` to just under `second`: follow-up due; draft a first follow-up.
- `second` up to `stale_after_days`: overdue; draft a stronger second attempt, only if fewer than `max_followups` follow-ups are logged.
- Beyond that, or `max_followups` reached: likely dead. Flag for the user: one last follow-up or mark withdrawn (propose only; the user confirms any status change).

### Statuses in `replied` (screening, interview)
Same logic with the windows from `by_status` for that status. A reply stage with no `by_status` entry uses the global windows; say so in the summary instead of inventing shorter ones. After an interview, a thank-you or status inquiry is the follow-up.

### Statuses in `in_progress` (applying, referral, analysing)
Not messages: reminders for the user to finish, submit or ask the referrer. Flag when the row has sat longer than `first_after_days`.

## Step 4: Draft Follow-Up Messages

For each application "due" or "overdue", draft a ready-to-send message.

### Message Principles
- **Short:** within `$P.style.limits.followup_words` (min-max words). Recruiters skim.
- **Specific:** reference the role, a detail from a conversation, or the application date.
- **Interest without desperation:** "still very interested" is fine; "please respond" is not.
- **No new claims.** Reference only what was submitted or said; no pressure lines about other offers or timelines the user has not stated.
- Never guilt-trip or complain about silence.
- **Match the channel:** LinkedIn shorter and more casual than email.
- **Referral first:** where `$P.followups.referral_first` is true and a warm contact exists at the company, route the nudge through that contact before a cold recruiter message.

### Avoid
"Just checking in" / "Just following up", "I hope this finds you well", "Per my previous message", "I haven't heard back", "Any update?" as the entire message.

### First Follow-Up (adapt, do not copy verbatim)
1. Reference the specific role and when you applied or spoke.
2. Restate interest with a specific reason (something about the role or company).
3. Mention availability only if `$P.situation.available_from` is set.
4. Close with an easy question or next step.

### Second Follow-Up (stronger)
1. Even shorter than the first.
2. Acknowledge you reached out before without sounding needy.
3. Offer a clear exit: "If the timeline has changed or the role has been filled, no worries - just let me know so I can plan accordingly."
4. This gives the recruiter an easy way to answer, even with bad news.

### Self-Action Items (APPLYING / REFERRAL)
Reminders for the user, not messages: "You've been in APPLYING for X days for [Company]. Ready to submit?" / "Referral for [Company] pending since [date]. Has it been submitted?"

## Step 5: Pipeline Health Summary

```
Pipeline Health - [today's date]

Active Applications: X
  <open_for_followup statuses>: X (Y need follow-up)
  <replied statuses>: X
  <in_progress statuses>: X (Y stalling)

Urgent (action today):
  - [Company] - [Role] - [Status] - [days] days - [action needed]

Follow-Up Due (this week):
  - [Company] - [Role] - [Status] - [days] days - [action type]

On Track:
  - [Company] - [Role] - [Status] - [days] days

Stalling (your action needed):
  - [Company] - [Role] - [in_progress status] - [days] days - finish and submit

Likely Dead:
  - [Company] - [Role] - [days] days - recommend: withdraw or final follow-up
```

Then each drafted follow-up under its own heading: company, channel (LinkedIn/email), copy-paste-ready text.

## Output Format

1. **Pipeline Health Summary**
2. **Follow-Up Messages** (one section per company needing action)
3. **Self-Action Reminders** (stalling APPLYING/REFERRAL items)
4. **Recommendations** (strategic observations, e.g. "heavy on APPLIED with few in SCREENING - spend this week on follow-ups rather than new applications")

## Post-Completion Workflow

- If a follow-up gets a response, suggest updating the tracker status and date (back up first, per the immutability rule), and record sent follow-ups with the text from `$P.followups.marker` (`{date}` = YYYY-MM-DD) in the next-action column so `tracker_query.py quiet` counts them. Skills only draft: `$P.followups.draft_only` is true, nothing is sent.
- Change the tracker only with `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/tracker_add.py --workspace . add|update ...` (backup, status and date validation, duplicate check and restyle in one step; exit code 2 means ask the user); never edit the xlsx directly.

## Important Principles

- **Never fabricate application history.** Only reference what is in the tracker.
- **Respect the user's urgency and circumstances** as recorded in the knowledge base or `CLAUDE.md`; do not assume any.
- **Do not spam.** Once an application has `$P.followups.max_followups` follow-ups with no response, recommend marking it withdrawn.
- **Personalize** from the company folder's `analysis.md` when it exists.
- Follow the dash rule (`$P.style.forbid_em_dash`): short dash `-`, never an em dash.
