---
name: followup-tracker
description: "Scans the applications tracker for overdue follow-ups and drafts follow-up messages. Use whenever the user says things like 'what needs follow-up', 'any overdue applications', 'check my pipeline', 'what's stale', 'pipeline review', 'morning check' or 'what needs attention today'. Also trigger when the user asks about application status, next actions or pipeline health, and suggest it proactively when the user mentions waiting to hear back from a company."
---

# Follow-Up Tracker

Reads the applications tracker, identifies applications that need follow-up based on time rules, and drafts ready-to-send messages for LinkedIn or email. `$P` means a field of the workspace's `profile.yaml`. Read it merged with the role and market presets, not as the raw file: run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/jobprofile.py --workspace . --json` once and use that output (preset values such as `avoid_company_types` and `scoring.depth_risk_keywords` are not in the raw `profile.yaml`).

## Context

The tracker is `$P.paths.tracker`, sheet `$P.tracker.sheet`. Timing limits come from `$P.followups`: `first_after_days`, `second_after_days`, `max_followups`, `stale_after_days`, `referral_first`. The thresholds below are the defaults for those fields; if the profile changes them, use the profile's values and scale the per-status windows proportionally.

For a quick mechanical pass, run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/tracker_query.py --workspace . quiet`; it lists APPLIED / CV SENT rows quiet for `first_after_days` with fewer than `max_followups` logged follow-ups (counted from the marker `followed up YYYY-MM-DD` in Next Action) plus stale-sweep candidates. Then apply the full rules below.

## When Triggered

1. Read the tracker for the current pipeline state.
2. Compute days since last activity for each active application.
3. Classify each by urgency.
4. Draft follow-ups for overdue items.
5. Present a pipeline health summary.

## Step 1: Read the Tracker

Extract all rows: Company, Role, Status, all stage date columns (Applied, Intro Call, Assignment, Tech Interview, Final Interview, Offer / Rejected), Next Action, Updated.

Filter to **active applications only**. Skip `BACKLOG`, `To Apply`, `ANALYZING`, `SKIP`, `REJECTED`, `WITHDRAWN`, `OFFER`. Active statuses to monitor: `APPLIED`, `CV SENT`, `SCREENING`, `INTERVIEW`, `APPLYING`, `REFERRAL` (use the profile's status names if `tracker.statuses` overrides them).

## Step 2: Calculate Staleness

`last activity` = the most recent non-empty date across stage columns, or `Updated` if none. `days_since_activity = today - last activity`.

## Step 3: Classify by Urgency

### APPLIED / CV SENT
- Under `first_after_days` (default 7): on track.
- `first_after_days` to just under `second_after_days`: follow-up due; draft a first follow-up.
- `second_after_days` up to `stale_after_days`: overdue; draft a stronger second attempt.
- Beyond that: likely dead. Flag for the user: one last follow-up or mark withdrawn (propose only; the user confirms any status change).

### SCREENING
- 0-3 days: on track. 4-6: follow-up due, nudge to keep momentum. 7+: overdue, they may have moved on; draft a check-in.

### INTERVIEW
- 0-2 days: on track (processing time). 3-5: follow-up due; thank-you or check-in if not already sent. 6+: overdue; draft a status inquiry.

### APPLYING / REFERRAL
- 0-3 days: on track (preparing materials). 4-7: stalling; this is a reminder to finish or submit the referral, not a message to send. 8+: at risk of missing the window; urgent self-action.

## Step 4: Draft Follow-Up Messages

For each application "due" or "overdue", draft a ready-to-send message.

### Message Principles
- **Short:** 3-5 sentences. Recruiters skim.
- **Specific:** reference the role, a detail from a conversation, or the application date.
- **Interest without desperation:** "still very interested" is fine; "please respond" is not.
- **Soft time element** ("I'm moving forward with a few other opportunities") only if true.
- Never guilt-trip or complain about silence.
- **Match the channel:** LinkedIn shorter and more casual than email.
- **Referral first:** where `$P.followups.referral_first` is true and a warm contact exists at the company, route the nudge through that contact before a cold recruiter message.

### Avoid
"Just checking in" / "Just following up", "I hope this finds you well", "Per my previous message", "I haven't heard back", "Any update?" as the entire message.

### First Follow-Up (adapt, do not copy verbatim)
1. Reference the specific role and when you applied or spoke.
2. Restate interest with a specific reason (something about the role or company).
3. Mention your timeline naturally.
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
  APPLIED/CV SENT: X (Y need follow-up)
  SCREENING: X
  INTERVIEW: X
  APPLYING/REFERRAL: X (Y stalling)

Urgent (action today):
  - [Company] - [Role] - [Status] - [days] days - [action needed]

Follow-Up Due (this week):
  - [Company] - [Role] - [Status] - [days] days - [action type]

On Track:
  - [Company] - [Role] - [Status] - [days] days

Stalling (your action needed):
  - [Company] - [Role] - APPLYING - [days] days - finish and submit

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

- If a follow-up gets a response, suggest updating the tracker status and date (back up first, per the immutability rule), and record sent follow-ups as `followed up YYYY-MM-DD` in Next Action so `tracker_query.py quiet` counts them.
- Change the tracker only with `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/tracker_add.py --workspace . add|update ...` (backup, status and date validation, duplicate check and restyle in one step; exit code 2 means ask the user); never edit the xlsx directly.

## Important Principles

- **Never fabricate application history.** Only reference what is in the tracker.
- **Respect the user's urgency and circumstances** as recorded in the knowledge base or `CLAUDE.md`; do not assume any.
- **Do not spam.** Once an application has `$P.followups.max_followups` follow-ups with no response, recommend marking it withdrawn.
- **Personalize** from the company folder's `analysis.md` when it exists.
- Follow the dash rule (`$P.style.forbid_em_dash`): short dash `-`, never an em dash.
