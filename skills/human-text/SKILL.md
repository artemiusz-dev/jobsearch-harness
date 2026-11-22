---
name: human-text
description: "Rewrites or reviews any text so it reads like it was written by a real human expert, not an AI model. Use whenever the user says text sounds AI-generated, robotic or templated, or asks to 'humanize', 'make it sound natural', 'rewrite this more naturally' or 'make it feel handwritten'. Also trigger proactively when generating long-form content (articles, emails, analyses, cover letters, essays) where the user has given no explicit format instructions. Works for any language the user writes in."
---

# Human Text

Rewrites or self-reviews generated text so it reads like a knowledgeable human wrote it in one sitting: not generated, not templated, not SEO-optimized.

Two modes:
- **Review mode** - the user pastes existing text; rewrite it to sound human.
- **Generation mode** - applied proactively to your own output before delivering it.

The workspace's `docs/humanize-rule.md` holds the project-specific banned-phrase list and house voice; if it exists, it extends and overrides this skill.

---

## Core Principle

The goal is not randomness or artificial imperfection. It is **the texture of genuine thought**: a person who knows the topic, writes without overthinking structure, and does not pad.

---

## Rules

### Voice & Tone
- Write with authority, not hedging. Skip "it's worth noting", "it's important to understand", "one might argue".
- No marketing tone: "cutting-edge", "seamless", "robust", "powerful solution", "game-changing".
- No academic closing: do not wrap every section with a tidy conclusion.
- Avoid over-politeness. A human expert does not thank you for asking.

### Structure
- Do not make every paragraph the same length. Mix short and long.
- Do not list everything. Use prose when a list is not genuinely clearer.
- Avoid the formula intro -> 3 points -> conclusion. Break the pattern.
- Do not force smooth transitions between every paragraph. Humans jump topics.
- Incomplete rhetorical constructions are fine if they sound natural.

### Sentences
- Mix short and long sentences in the same paragraph.
- Sometimes start with "And", "But", "Which is".
- Vary sentence openings; never four in a row the same way.
- A one-sentence paragraph is fine.

### Forbidden Phrases (English)
- "in today's world", "it's important to note", "it's worth mentioning"
- "key aspect", "at the end of the day", "needless to say"
- "in conclusion", "to summarize", "as we can see"
- "leverage", "utilize", "streamline", "holistic approach"
- "I am passionate about" / "I have a passion for", "I am excited to" / "I am thrilled to"
- "results-driven", "team player", "detail-oriented", "go-getter", "proven track record"
- "I would be a great fit for this role", "I look forward to the opportunity to"
- "I am confident that my experience...", "I am eager to bring my skills to..."
- "cutting-edge", "dynamic team", "fast-paced environment", "synergy", "synergize"

For other languages, apply the same idea: drop the stock filler openers, bureaucratic connectives ("in the framework of this topic") and empty intensifiers that a native writer of that language would flag as template text. Add language-specific entries to `docs/humanize-rule.md`.

### Specificity
- Replace vague claims with concrete observations, numbers or cause and effect.
- Add nuance: what is true in general but not always? Say so.
- Subjective observations are allowed: "this rarely works in practice".
- Do not prove everything. Humans assert what they know.

### What Human Text Looks Like
- Uneven rhythm; not every thought gets a full paragraph.
- Occasional backtracking: "Actually, the bigger issue is...".
- Mid-thought qualification: "...which works, as long as you're not dealing with X".
- The ending need not feel finished; it can stop when the point is made.

---

## Language Notes

### English
- Contractions are natural ("it's", "you're", "don't") outside formal registers.
- Sentence fragments are fine occasionally: "Which is the whole point."
- Avoid the passive voice unless it genuinely fits.
- Vary register slightly; do not hold one formality level throughout.

### Any other language
- Prefer living syntax over bureaucratic phrasing; sentences need not be symmetrical.
- Prefer verbs over stacked verbal nouns ("decide" over "carry out the making of a decision").
- Watch for calques from English.

---

## Nativeness Check

After applying the rules, run a last pass for naturalness. The core question: **would a native speaker actually say this, or does it only look correct on paper?**

- **Calques and translation smell** - a phrase that could be word-for-word from another language probably is. Rephrase from the meaning, not the words.
- **Non-idiomatic prepositions** (English: "discuss about", "comprised of").
- **Overly literal phrasing** - "make a decision" -> "decide", "conduct an analysis" -> "analyze", "provide assistance" -> "help".
- **Article and determiner errors** - invisible to non-natives, obvious to natives.
- **Register mismatch** - formal vocabulary on casual syntax or the reverse; pick a lane per paragraph.
- **Read-aloud test** - read mentally at speaking pace; anything stiff or rehearsed needs a rewrite.

When a phrase fails, rewrite it; do not patch it. Awkward constructions rarely improve with small edits.

---

## Self-Review Checklist (before delivering)

- [ ] Any forbidden phrases present?
- [ ] All paragraphs the same length?
- [ ] Every paragraph opening the same way?
- [ ] More than 2 consecutive bullet lists?
- [ ] Does the ending feel like a "conclusion" template?
- [ ] A sentence starting with "It's important to..."?
- [ ] At least one short sentence (under 8 words)?
- [ ] At least one concrete detail, not just abstract claims?

If any answer is wrong, fix it before delivering.

---

## Exceptions - contexts where these rules do NOT apply

Some text types require formal or structured language. Before applying the rules, check the category; if it is an exception, ask the user which option to use:

**Option A - Full rewrite** (default). All rules. For editorial, opinion, analytical and conversational content.
**Option B - Partial humanization.** Remove forbidden phrases and equalize paragraph length, but keep formal register and structure. For professional emails, reports, internal docs.
**Option C - No changes.** For when the formal style is a hard requirement.

If the content is ambiguous, proceed with Option C; the user will invoke the skill explicitly when they want it applied.

Exception categories (ask first):
- Legal documents, contracts, terms of service
- Official letters, formal complaints, notarial texts
- Medical or clinical summaries for institutions
- Academic abstracts and papers
- Job descriptions written for ATS systems
- Code comments and inline documentation

### Special case: technical docs (specs, API docs, changelogs)
Not an exception: apply the rules with these constraints.
- One idea per sentence; no stacked compound clauses.
- No cross-references, footnotes or "see also" chains unless necessary.
- Write as if explaining to a colleague.
- Narrative over instruction: "This endpoint returns the user object", not "Returns: UserObject (see schema §3.2)".
- More than 4 list items: consider prose.
- Changelogs: one plain sentence per change, no preamble.

---

## Output Instructions

**Review mode:**
1. Deliver the rewritten text first.
2. Below it, a compact **"What changed"** block, one line per issue, format `- [issue]: [brief note]`:

```
- Forbidden phrase: "it's important to note" -> removed
- Paragraph length: all 4 paragraphs were ~80 words -> varied
- Sentence openings: 3 consecutive sentences started with "This" -> rewritten
- Specificity: vague claim "technology evolves" -> replaced with a concrete observation
- Nativeness: "conduct an analysis" -> "analyze"
```

**Generation mode:** apply all rules silently before delivering. Do not announce the skill. Exception detection still applies: pause and ask if an exception category is detected.
