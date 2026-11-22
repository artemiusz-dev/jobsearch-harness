# Salary Comparison Rules (generic market pack)

This is the generic version of the market pack's salary document. A country pack (for example `presets/markets/poland.md`) replaces it with local contract types, tax rules and net formulas. `init-workspace` copies the right one here.

Always compare offers in **net (take-home)** terms, not gross. Different employment structures give very different net at the same gross.

## Floor and ask (from `profile.yaml`)
- **Floor (internal, never quote):** `compensation.floor_gross` AND `compensation.floor_net`, in `compensation.currency` per `compensation.period`.
- **Outward ask / anchor:** `compensation.ask_gross`. This is the only figure you ever say to a recruiter or enter in a form.
- Record your last compensation and any benchmark in the knowledge base §1, with the date it was stated.

## Net calculation (generic)

`net_rule: generic_flat`: estimate `net = gross x (1 - effective_deduction_rate)`, where the rate bundles income tax and mandatory social contributions for the structure. Ask the user for their rate (or look it up with a national calculator) and record it below. This is a rough estimate; replace it with your country's rules for anything binding.

| Structure | Effective deduction rate | Notes |
|---|---|---|
| Employee | _fill in_ | include employer-paid benefits separately |
| Contractor / self-employed | _fill in_ | add your own social contributions and accounting costs |
| Via an intermediary employer | _fill in_ | add the intermediary's fee |

## Default assumptions
- **Ranges with several possible structures:** compute net for each structure the employer offers and show the highest as primary and the others as fallbacks. Flag anything that needs the employer's confirmation.
- **Benefits:** list them separately; do not fold them into net unless the user asks.
- **Currency:** convert at the rate on the day of analysis and say which.

## When analyzing JDs and salary ranges
1. Identify the employment structure from the JD.
2. Convert the range to estimated net using the table above.
3. Compare against the floor and note the delta ("+X / -X vs the floor").
4. Flag anything unconfirmed that could change net materially.
5. If the top of the net range does not clear the floor, flag it as a concern (the employment-type gate applies).
6. If salary is missing, note it as a red flag and ask for it.

## When talking to recruiters
- Net calculations are for internal assessment only; never quote them.
- Ask structure-specific tax or benefit questions only after the employment type is confirmed, never in the first reply. Country packs list the standard questions.
- If a figure is low after conversion, say so in the assessment and consider asking about alternative structures.

## In the JD analyzer and recruiter responder
Both skills read this file for net conversion and for the structure alternatives and follow-up questions your market uses. Keep it current; if the floor changes, update `profile.yaml` first, then the summary in `CLAUDE.md`.

## Disclaimer
Estimates only. Verify binding numbers with the employer, a calculator for your country and a qualified adviser.
