"""Calibration helpers: does a higher Match % actually bring more replies? (standard library only)"""
from __future__ import annotations

import math

MIN_N = 30                      # per-band sample below which no conclusion is drawn (matches the rubric's guidance)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for k successes in n trials (as fractions)."""
    if n == 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, centre - half), min(1.0, centre + half)


def band_stats(rows, band_of, roles, today, mature_days, to_score, to_date):
    """Per band: n, replied, interview, offer; plus how many rows were skipped as too recent.
    A row counts when it has a Match % and an Applied date at least `mature_days` ago."""
    stats: dict[str, dict[str, int]] = {}
    too_recent = 0
    for r in rows:
        s = to_score(r.get("Match %"))
        applied = to_date(r.get("Applied"))
        if s is None or applied is None:
            continue
        if (today - applied).days < mature_days:
            too_recent += 1
            continue
        b = stats.setdefault(band_of(s), dict(n=0, replied=0, interview=0, offer=0))
        b["n"] += 1
        if r.get("Intro Call") or r.get("Status") in roles["replied"]:
            b["replied"] += 1
        if r.get("Tech Interview") or r.get("Final Interview") or r.get("Status") in roles["interview"]:
            b["interview"] += 1
        if r.get("Status") in roles["offer"]:
            b["offer"] += 1
    return stats, too_recent


def verdict(labels, stats):
    """Plain-language conclusion about whether the bands separate. Returns a list of lines."""
    present = [(k, stats[k]) for k in labels if k in stats]
    total_n = sum(v["n"] for _, v in present)
    lines = []
    small = [k for k, v in present if v["n"] < MIN_N]
    if total_n < MIN_N:
        return [f"Only {total_n} matured applications: too few to say anything. Keep the default thresholds."]
    if small:
        lines.append(f"Bands with fewer than {MIN_N} applications ({', '.join(small)}) are marked * and are not used for conclusions.")
    usable = [(k, v) for k, v in present if v["n"] >= MIN_N]
    separated = False
    for (lo_k, lo), (hi_k, hi) in zip(usable, usable[1:]):
        lo_hi = wilson(lo["replied"], lo["n"])[1]
        hi_lo = wilson(hi["replied"], hi["n"])[0]
        if hi_lo > lo_hi:
            separated = True
            lines.append(f"Band {hi_k} replies more often than {lo_k} with confidence ({hi['replied']}/{hi['n']} vs {lo['replied']}/{lo['n']}).")
    if len(usable) < 2:
        lines.append("Fewer than two bands have enough data to compare.")
    elif separated:
        lines.append("Higher scores do bring more replies: the thresholds are doing work. Consider moving "
                     "apply_this_week_from to the lowest band edge that separates.")
    else:
        lines.append("No band replies significantly more often than another: the score does not yet predict replies "
                     "(the confidence intervals overlap). Keep the thresholds; do not tune them on this data.")
    return lines


def fmt_rate(k: int, n: int) -> str:
    if n == 0:
        return "-"
    lo, hi = wilson(k, n)
    return f"{100 * k / n:4.1f}% ({100 * lo:.0f}-{100 * hi:.0f}%)"
