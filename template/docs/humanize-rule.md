# Humanize Output Rule

Applies to: cover letters, application form answers (see `application-forms.md`), recruiter messages, and any first-person written communication on the user's behalf.

**Goal:** output must read as written by a real, experienced practitioner, not by an AI. Hiring managers and recruiters increasingly detect AI-generated text by its cadence, word choice and sentence structure, and detected AI text lowers credibility and response rates.

Add your own entries (other languages, patterns you personally never use) at the bottom of each list. The `human-text` skill reads this file and treats it as an extension of its defaults.

## Banned phrases and patterns
**The phrase list lives in one place: `style.banned_phrases` in `profile.yaml`** (global) and `style.channel_banned_phrases` (per channel: dm, recruiter_reply, letter, form_answer). Run `python3 <plugin>/scripts/jobprofile.py --workspace . --json` to see it. Edit the list there, not here; `check_dm.py` and the builders read it from the profile.

The patterns below are about shape, not exact words, so they stay in prose:
- Opening sentences that start with "I" followed by a self-praising adjective or claim
- Triple-stacked superlatives ("highly motivated, results-oriented, detail-focused...")

## Vocabulary rules
- **Plain words.** Short, common words over formal ones: "use" not "utilize", "help" not "facilitate", "show" not "demonstrate", "work on" not "spearhead".
- **No jargon inflation.** One precise term beats three vague ones.
- **Limit tech detail to what the reader needs.** A hiring manager reading a letter does not need versions, operators or pipeline details; mention the impact, not the implementation. Save depth for technical interviews.
- **Natural speaking level.** If you would not say it aloud, do not write it; if a sentence sounds stiff, rewrite it.

## Structural rules
- **Vary sentence length.** Mix short punchy sentences with longer ones.
- **No throat-clearing openers.** Never open with "I am writing to express my interest in..."; start with something concrete: a claim, a fact, a direct statement.
- **First-person yes, self-promotion prose no.** Concrete achievements over adjectives: "I led a migration of a 200k-line codebase" beats "I am experienced in large-scale projects".
- **One idea per sentence.**
- **No sign-off platitudes.** End letters and messages with a direct, specific statement, not "I look forward to hearing from you at your earliest convenience".
- **LinkedIn DMs you start:** at most `style.limits.dm_sentences` sentences, one direct question; the full rules and banned closers are in the `recruiter-responder` skill (Outbound LinkedIn DMs).
- **Recruiter messages:** conversational, short sentences, no corporate tone; sound like a senior professional who knows their worth, not a job seeker performing enthusiasm.

## Tone calibration per document type
- **Cover letter:** direct, confident, specific. A colleague making a case, not a candidate begging for a shot. Professional, with a voice.
- **Application form answers:** concise and factual; answer exactly what is asked; no padding.
- **Recruiter responses:** warm but brief; signal interest without performing eagerness; one or two sentences per point.

## After drafting - self-check
1. Any phrase from `style.banned_phrases` (plus the channel's extras): replace or remove.
2. Any paragraph where every sentence starts with "I": restructure.
3. Any unnecessarily complex word: replace with the simpler one.
4. Any tech detail that serves no purpose for a non-technical reader: remove or summarize as outcome.
5. Any sentence that could have been written by anyone: make it specific to the user's actual experience.
