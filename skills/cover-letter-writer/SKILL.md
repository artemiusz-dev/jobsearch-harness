---
name: cover-letter-writer
description: "Writes targeted cover letters (motivation letters) for specific job applications, optimized for human readers and AI screening tools. Use when the user asks to write, draft or create a cover letter or motivation letter."
---

# Cover Letter Writer

Writes a concise, targeted cover letter for a specific application. Every sentence earns its place: no filler, no generic phrasing, no corporate cliches. The letter works for three audiences: the hiring manager skimming in 30 seconds, the AI screening tool scanning for keywords, and the recruiter deciding whether to forward it. `$P` means a field of the workspace's `profile.yaml`.

## Context

The base CV is `$P.paths.base_cv`. A job description should already be available. The workspace `CLAUDE.md` docs index points to the rules this skill depends on. Read `docs/humanize-rule.md` (banned phrases, voice) and `docs/cv-letter-quality.md` (Draft Review Pass, Factual Grounding) before drafting, and `docs/build-application.md` before building the file. Write a letter only when the user explicitly asks; never offer it proactively after a JD analysis or CV tailoring.

## Prerequisites Check

1. **CV exists** at `$P.paths.base_cv`. If a tailored CV exists in the company folder, read it so the letter complements it.
2. **Knowledge base** (`$P.paths.knowledge_base`): STAR stories, cover letter angles, tailoring patterns, quantifiable achievements. This is the primary source for specificity. Every date, employer, title and number in the letter must trace to it or to the base CV.
3. **Job description** is available; use JD analyzer output if it exists.
4. **Tone preference** - if not established, ask first (Step 1).

## Step 1: Determine Tone

If the user has not specified a tone, ask before drafting:

- **Direct & Technical** - leads with technical impact and architecture-level thinking. For engineering-led companies and JDs stressing depth.
- **Balanced Professional** - technical substance plus leadership, collaboration, product thinking. For product companies and cross-functional roles. Default when signals are mixed.
- **Narrative-Driven** - connects experiences through a story arc. For culture-heavy companies where "why you want to work here" matters as much as qualifications.

Recommend a tone from JD signals; default to Balanced Professional.

## Step 2: Research & Context Gathering

**The company** - what they build, tech blog or open-source presence, market position. If the JD gives too little, ask: "What specifically interests you about [Company]? I want something genuine, not generic." Company-specific claims need a page from the company's own domain (or consistent independent reporting); a search snippet is a lead, not a source. Check `company_research/<company-slug>.json` (30-day cache, if the workspace uses one) first and update it after fresh research.

**The role** - core challenge, team context, what makes it different from a generic posting.

**The CV** - the 2-3 achievements that most directly address the key requirements. Prefer quantifiable impact. If the JD analyzer ran, start from its "Experiences to Emphasize".

Do not write until you have material for specificity. A generic letter is worse than no letter.

## Step 2b: Short Mode

If the user says "short", "brief", "concise version" or similar, activate **Short Mode**: the **body text** (between greeting and sign-off) is **under 1,000 characters** including spaces. Greeting, sign-off and header block (name, contact, date, "Re:" line) do not count.

- **2 paragraphs only.** First: opening hook + why this company (merged). Second: strongest single achievement tied to the role + brief forward-looking close.
- No editorial notes unless asked.
- Cut any sentence that does not directly connect the candidate to the role. Same quality bar: no filler, no cliches, "you/your" address.

Skip the four-paragraph structure in Step 3 and set `"max_chars": 1000` in the letter spec; the builder fails if the body is over, and reports the final count. Report that count.

## Step 3: Write the Letter

**Standard mode:** four paragraphs, under 400 words. Every sentence must pass: "Does this tell the reader something they would not know from the CV alone?" **Short mode:** see Step 2b.

Write as if explaining to a smart friend why this role caught your eye and why you fit. Confident and conversational, not performative.

### Personal Address Rule

Use "you" / "your team" / "your company" for the recipient, not the company name in third person. A letter is a conversation, not a report. The company name may appear once or twice (the "Re:" line, a specific factual reference), but the body defaults to "you" and "your".

**Avoid:** "Acme values AI-augmented workflows as a core engineering practice."
**Write:** "You value AI-augmented workflows as a core engineering practice."

### Paragraph 1: Opening Hook

The first sentence decides whether the reader continues.
- Never open with "I am writing to express my interest in..." or "I am excited to apply for..." or any variation.
- Lead with one of: a specific observation about the company's engineering challenge that connects to your experience; a concise statement of what you would bring to their situation; a reference to something in the JD that resonated and why.
- 2-3 sentences. Vary sentence rhythm: a short punchy sentence then a longer one; three equal-length sentences feel robotic.

### Paragraph 2: Why This Company

Specificity separates a good letter from a generic one.
- Reference something concrete: their product, a technical decision, their market position, an unusual aspect of the role.
- Connect through alignment, not flattery: "your approach to X matches how I think about Y".
- No corporate-speak ("I'm drawn to your mission", "I admire your commitment to innovation").
- If you cannot articulate genuine interest, be brief and honest. Two real sentences beat five fake ones.
- Adapt to the market: for a company in the user's home market, local familiarity can help; for a foreign company hiring remotely, signal comfort with distributed, international teams.

### Paragraph 3: Why Me

The paragraph the hiring manager remembers.
- Lead with the strongest match: the CV achievement that addresses the role's primary requirement.
- 1-2 supporting achievements, each tied to a different JD requirement. 2-3 achievements max.
- Micro-stories (situation, action, change), not prose bullet points.
- Natural language for metrics ("cut load times nearly in half across 12 surfaces", not "47.3%"). Precision is for the CV.
- Frame as outcomes, not activities.
- Address a stated JD requirement the user does not meet honestly ("I've used X rather than owned it") instead of omitting it.

### Paragraph 4: Call to Action

Short, forward-looking, confident without presumption.
- End like a human, not "I look forward to discussing this opportunity further".
- No groveling ("I would be honored", "dream job").
- 1-2 sentences. Address logistics the posting raises (start date, work model, requisition ID) here or in a short logistics line.

## Step 4: Keyword Integration

Check the letter against the JD's critical keywords: key technologies appear naturally inside achievements, not as a list; role terminology is echoed where it fits; integration is invisible. Do not force a keyword that does not fit; the CV carries comprehensive keywords, the letter carries narrative and fit.

## Step 5: Build and Review

The letter is built from the `letter` section of the company folder's spec, not from a per-company script. Do not create `gen_cover_letter_*` scripts.

1. Add or update the `letter` section in `<company-folder>/spec.json`: `paragraphs` (one string each), `re` ("Re: Role - Company"), `salutation`, `date`, `closing`, optional `max_chars`. Set `headline` to the title line of the submitted CV when the spec has no `cv` section. Format: `docs/build-application.md`. Name and contact come from the base CV, so the email stays correct.
2. Build and verify: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/build_application.py <folder> --letter --verify --workspace .`. It produces .docx and PDF (LibreOffice required), checks the PDF is one page and runs the layout check. In Short Mode the build fails if the body exceeds `max_chars`.
3. Run the Draft Review Pass from `docs/cv-letter-quality.md` (fresh-context reviewer, one revision), then fix by editing the spec and rebuilding with `--force` (drafts only, never submitted files).
4. If the portal has free-text fields (self-introduction, project entries, a pitch under a character limit, a motivation question), offer to draft them per `application-forms.md`. Required fields are drafted even when no cover letter was requested.

**The Cover Letter** - clean and copy-ready: no markdown inside the letter, proper paragraph spacing, professional sign-off.

**Editorial Notes** (standard mode only) - 3-5 bullets: why this hook, which CV achievements and why, key JD keywords woven in, trade-offs, what the user might adjust.

## Post-Completion Workflow

1. Outputs are in the company folder, named by `$P.identity.output_name_pattern` with kind `Cover-Letter` (`.docx` and `.pdf`).
2. If a tracker row exists, no status change is needed (the letter is part of the APPLYING phase).
3. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cleanup.py --workspace .` (dry run first) if LibreOffice left lock or temp files.

## Important Principles

- **Every sentence must add value.** If you can delete it without losing impact, delete it.
- **Specificity over generality.**
- **Standard mode: 400 words max. Short mode: 1,000 characters max (body only).** Brevity signals confidence.
- **CV and letter have different jobs.** The CV proves qualifications; the letter explains motivation and fit. Interpret, do not repeat.
- **No fabricated enthusiasm.** Focus on the role and the challenge.
- **Adapt formality to the company** (large enterprise vs startup vs remote company abroad).
- **Relocation or work-model logistics** belong in the closing or a logistics line, not the opening, and only when the locations in `$P.locations` make them relevant.
- **Coordinate with prior outputs.** Complement, do not duplicate, the tailored CV.
- **Read it aloud mentally.** Podium speech = rewrite. Coffee with a hiring manager = right. Contractions are fine. One moment of personality goes further than perfect structure.
- **Avoid "passion" language entirely.** Show interest through specificity, not adjectives.
- Follow the dash rule (`$P.style.forbid_em_dash`): short dash `-`, never an em dash.
