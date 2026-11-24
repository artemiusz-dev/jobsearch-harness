#!/usr/bin/env python3
"""Compare JD analyses of the same posting: repeated runs, or a new system against an old reference.

    python3 scripts/score_compare.py run1/analysis.md run2/analysis.md run3/analysis.md
    python3 scripts/score_compare.py --reference old/analysis.md new1.md new2.md new3.md

Reads `**Overall Score: NN**` and the five dimension rows (Technical, Experience, Behavioral/Culture, Career,
Compensation) from each file and prints per-file values, the mean, spread and, with --reference, the difference
to the reference. Use it before changing weights or thresholds: one run is noisy, a mean of several is not.
Standard library only.
"""
from __future__ import annotations

import argparse
import re
import statistics
import sys
from pathlib import Path

DIMENSIONS = (("technical", "Technical"), ("experience", "Experience"), ("behavioral|culture", "Culture"),
              ("career", "Career"), ("compensation", "Compensation"))
OVERALL = re.compile(r"\*\*Overall Score:\s*(\d+(?:\.\d+)?)\*\*")


def parse(text: str) -> dict[str, float]:
    out: dict[str, float] = {}
    m = OVERALL.search(text)
    if m:
        out["overall"] = float(m.group(1))
    for line in text.splitlines():
        cells = [c.strip().strip("*") for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or not line.lstrip().startswith("|"):
            continue
        name = cells[0].lower()
        for pattern, key in DIMENSIONS:
            if key in out or not re.match(rf"^({pattern})\b", name):
                continue
            nums = [c for c in cells[1:4] if re.fullmatch(r"\d+(\.\d+)?", c)]
            # columns are: weight (0.30 or 30%) then score; the score is the last plain number among the first three
            if nums:
                out[key] = float(nums[-1])
            break
    return out


def summarize(values: list[float]) -> str:
    if not values:
        return "-"
    mean = statistics.fmean(values)
    spread = f"{min(values):g}-{max(values):g}" if len(values) > 1 else f"{values[0]:g}"
    sd = f", sd {statistics.stdev(values):.1f}" if len(values) > 1 else ""
    return f"mean {mean:.1f} (range {spread}{sd})"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--reference", help="analysis to compare against (for example the old system's)")
    a = ap.parse_args(argv)
    runs = []
    for f in a.files:
        try:
            runs.append((f, parse(Path(f).read_text(encoding="utf-8"))))
        except OSError as exc:
            print(f"cannot read {f}: {exc}", file=sys.stderr)
            return 1
    ref = parse(Path(a.reference).read_text(encoding="utf-8")) if a.reference else None
    keys = ["overall"] + [k for _, k in DIMENSIONS]
    for f, d in runs:
        missing = [k for k in keys if k not in d]
        print(f"{Path(f).parent.name + '/' if Path(f).parent.name else ''}{Path(f).name}: overall {d.get('overall', '?')}"
              + (f"  (could not read: {', '.join(missing)})" if missing else ""))
    print()
    print(f"{'':<14} {'runs':<44}" + (f" {'reference':>9} {'delta':>7}" if ref else ""))
    for k in keys:
        vals = [d[k] for _, d in runs if k in d]
        line = f"{k:<14} {summarize(vals):<44}"
        if ref and k in ref and vals:
            line += f" {ref[k]:>9g} {statistics.fmean(vals) - ref[k]:>+7.1f}"
        print(line)
    if len(runs) < 3:
        print("\nNote: fewer than 3 runs; differences under about 5 points are within run-to-run noise.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
