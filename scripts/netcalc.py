#!/usr/bin/env python3
"""Estimate net pay from gross using the active market pack's parameters (profile market_params).

Usage:
    python3 scripts/netcalc.py [--workspace DIR] GROSS [--structure STRUCT] [--annual-revenue X]

Structures: generic (generic_flat market), jdg, eor, uop (poland market).
Estimates only: verify with an official calculator and a qualified adviser.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jobprofile import ProfileError, add_workspace_arg, load_profile  # noqa: E402


def generic_flat(gross: float, params: dict) -> float:
    rate = params.get("generic_flat", {}).get("effective_deduction_rate")
    if rate is None:
        raise ProfileError("market_params.generic_flat.effective_deduction_rate is not set in profile.yaml")
    return gross * (1 - rate)


def poland_eor(gross: float, p: dict) -> float:
    e = p["eor"]
    return (gross - e["service_fee"] - e["transfer_fee"]) * (1 - e["copyright_pit_rate"])


def poland_jdg(revenue: float, p: dict, annual_revenue: float | None = None) -> float:
    j = p["jdg_ryczalt"]
    annual = annual_revenue if annual_revenue is not None else revenue * 12
    health = next((t["amount"] for t in j["health_monthly"] if t["up_to"] is None or annual <= t["up_to"]), None)
    if health is None:
        raise ProfileError("market_params.poland.jdg_ryczalt.health_monthly needs a last tier with up_to: null")
    zus = j["zus_monthly"]
    tax = j["rate"] * (revenue - zus - j["health_deductible_share"] * health)
    return revenue - zus - health - tax - j["accounting_monthly"]


def poland_uop_reference(gross: float, p: dict) -> str:
    kup = p["uop_reference_points_gross_to_net_with_50pct_kup"]
    nokup = p["uop_reference_points_gross_to_net_without_kup"]
    def fmt(pts):
        return ", ".join(f"{x['gross']:,.0f} -> ~{x['net']:,.0f}" for x in pts)

    return ("UoP net depends on KUP, contributions and the annual tax threshold: use an official calculator.\n"
            f"  reference points with 50% KUP: {fmt(kup)}\n  without KUP: {fmt(nokup)}\n  you asked about gross {gross:,.0f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("gross", type=float, help="monthly gross (revenue for jdg) in the profile currency")
    ap.add_argument("--structure", default=None)
    ap.add_argument("--annual-revenue", type=float, help="override annual revenue for the health tier (jdg)")
    add_workspace_arg(ap)
    a = ap.parse_args()
    try:
        prof = load_profile(a.workspace)
        rule = prof["compensation"].get("net_rule", "generic_flat")
        params = prof.get("market_params", {})
        cur = prof.currency
        if rule == "generic_flat":
            if a.structure:
                print(f"note: --structure {a.structure!r} is ignored by the generic_flat rule", file=sys.stderr)
            print(f"{a.gross:,.0f} {cur} gross -> ~{generic_flat(a.gross, params):,.0f} net (flat estimate)")
        elif rule == "poland":
            if "poland" not in params:
                raise ProfileError("net_rule is 'poland' but market_params.poland is missing (use presets.market: poland)")
            p = params["poland"]
            s = (a.structure or "").lower()
            if s == "eor":
                print(f"EOR: {a.gross:,.0f} -> ~{poland_eor(a.gross, p):,.0f} {cur} net")
            elif s in ("jdg", "b2b"):
                print(f"JDG ryczalt: {a.gross:,.0f} revenue -> ~{poland_jdg(a.gross, p, a.annual_revenue):,.0f} {cur} net")
            elif s == "uop":
                print(poland_uop_reference(a.gross, p))
            else:
                print(f"EOR: ~{poland_eor(a.gross, p):,.0f} | JDG ryczalt: ~{poland_jdg(a.gross, p, a.annual_revenue):,.0f} {cur} net")
                print(poland_uop_reference(a.gross, p))
        else:
            sys.exit(f"Unknown net_rule '{rule}'")
    except ProfileError as e:
        sys.exit(f"netcalc: {e}")
    except KeyError as e:
        sys.exit(f"netcalc: missing parameter {e} in market_params")
    print("Estimate only; verify with an official calculator.")


if __name__ == "__main__":
    main()
