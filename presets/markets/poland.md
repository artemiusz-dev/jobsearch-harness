# Salary Comparison Rules - Poland market pack

Informational reference, not tax or legal advice. Figures are 2026 reference values; verify them against official sources and a qualified adviser, and update them yearly. The numbers live in `presets/markets/poland.yaml` (`market_params.poland`); `netcalc.py` uses them. `init-workspace` copies this file to `docs/salary-rules.md` in your workspace.

Always compare offers in **net (take-home)** terms. Different employment structures give very different net at the same gross. Your floor and outward ask are in `profile.yaml` (`compensation`): the floor is internal and never quoted; the ask is the only figure you say to recruiters.

## Structures

### Employment contract (UoP)
Ask whether the employer applies **50% author's costs (KUP, autorskie koszty uzyskania przychodu)** to engineering roles. When available, net is noticeably higher than the standard 20% case. Use an official salary calculator for a binding figure. Reference points from the pack parameters (monthly, before PPK and benefits):
- 19,000 gross with 50% KUP is about 14,000 net
- 22,000 gross with 50% KUP is about 16,200 net
- 22,000 gross without KUP is about 15,100 net
UoP includes paid leave, sick pay and social insurance. The 50% KUP has an annual cap (see `annual_cap_50pct_kup`) shared across all employers in the year.

### Own business (JDG, B2B) with 12% lump-sum tax
`net = revenue - ZUS - health - rate x (revenue - ZUS - share x health) - accounting`, with the contribution amounts and the health tier (by annual revenue) from `jdg_ryczalt`. Example from the reference parameters: 22,000 monthly revenue gives about 16,580 net. Own JDG needs no employer confirmation. No paid leave or sick pay unless you build them in.

### Employer-of-record via a foundation (umowa o dzieło structure)
Typical mechanism:
1. The client pays the gross amount to the provider.
2. A service fee (`service_fee`) is deducted, plus a bank transfer fee (`transfer_fee`).
3. If the work qualifies as copyright work (typical for software), `copyright_pit_rate` PIT is withheld at source.
4. No sick pay or paid leave under this contract type. Social insurance can sometimes be arranged separately through a parallel contract with the provider.
5. For EUR invoices, the PLN conversion uses the provider's bank rate at the moment of conversion.

`net = (gross - service_fee - transfer_fee) x (1 - copyright_pit_rate)`. Example: 22,000 gross gives about 20,256 net. **Caveat:** the flat PIT rate ignores the annual cap on 50% author's costs, so net at high income is lower than this estimate; the cap is shared with any KUP used elsewhere in the same year. Confirm terms with the provider and a tax adviser. EOR is not equivalent to UoP in employment protections.

## Default assumptions
- **B2B-only ranges:** calculate both own-JDG and EOR net, show the higher as primary and the other as fallback. EOR needs employer confirmation; own JDG does not.
- **UoP ranges:** assume KUP is available unless stated otherwise; show the KUP-based net as primary and "without KUP: ~X" as fallback; flag KUP as unconfirmed if the JD does not state it.
- Run `python3 <plugin>/scripts/netcalc.py --workspace . <gross> --structure jdg|eor|uop` for the formula-based structures and the UoP reference points.

## When analyzing JDs and salary ranges
1. Identify the structure (UoP, B2B, EOR) from the JD.
2. Convert the range to estimated net with the assumptions above.
3. Compare against `compensation.floor_net` and `floor_gross` and note the delta.
4. UoP: flag whether KUP availability is confirmed. B2B: show the EOR net and say the arrangement needs employer confirmation.
5. If the top of the net range does not meaningfully beat the floor, flag it as a concern (the employment-type gate applies). Missing salary is a red flag.

## When talking to recruiters
- Never quote net calculations; they are for internal assessment only.
- The first reply asks only for the job description, the salary range and the employment type.
- Once UoP is confirmed, ask whether the company applies 50% KUP to engineering roles. Do not ask this in the initial outreach.
- For B2B-only offers, ask whether cooperation through an employer-of-record is possible before declining; compare nets first, since either route can win depending on the offer.
- If the recruiter's figure is low after conversion, say so in the assessment and consider asking about the alternative structures.

## Job boards commonly used in Poland
justjoin.it, nofluffjobs.com, bulldogjob.pl, pracuj.pl, plus LinkedIn. Enable them through adapters (see `docs/adapters.md`); all are third-party sites, so respect their terms of service.
