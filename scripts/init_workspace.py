#!/usr/bin/env python3
"""Create a private job-search workspace from the plugin's template.

Usage:
    python3 scripts/init_workspace.py --target DIR --answers answers.json [--cv base.docx] [--market NAME] [--role NAME]

answers.json (all values are the user's own; nothing is invented):
{
  "full_name": "...", "email": "...", "phone": "(optional)",
  "roles": ["..."],                      # optional if the role preset supplies them
  "seniority": ["senior"],               # optional if the preset supplies them
  "locations": [{"place": "remote", "modes": ["remote"]}],
  "currency": "EUR",                     # optional when the market preset sets it
  "period": "month",                     # month | year | day
  "floor_gross": 20000, "floor_net": 14000, "ask_gross": 22000,   # floor_net / ask_gross optional
  "languages": [{"language": "English", "level": "C1"}],
  "authorized_in": ["..."],              # optional
  "effective_deduction_rate": 0.3        # only for the generic market
}

Never overwrites: the target must not exist or must be empty. Writes only inside the target.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobprofile as jp  # noqa: E402

PLUGIN = jp.PLUGIN_ROOT.resolve()
TEMPLATE = PLUGIN / "template"

DEFAULT_WEIGHTS = {"technical": 0.30, "experience": 0.20, "culture": 0.10, "career": 0.25, "compensation": 0.15}
DEFAULT_THRESHOLDS = {"strong": 75, "good": 60, "moderate": 45, "weak": 30, "apply_this_week_from": 68}


class InitError(Exception):
    pass


def preset(kind: str, name: str) -> dict:
    if not jp.PRESET_NAME.match(name or ""):
        raise InitError(f"Invalid {kind[:-1]} name {name!r}: use lowercase letters, digits and '-'")
    p = PLUGIN / "presets" / kind / f"{name}.yaml"
    if not p.exists():
        avail = ", ".join(sorted(x.stem for x in (PLUGIN / "presets" / kind).glob("*.yaml")))
        raise InitError(f"Unknown {kind[:-1]} '{name}'. Available: {avail}")
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def build_profile(a: dict, role: str, market: str) -> dict:
    mkt = preset("markets", market)
    currency = a.get("currency") or mkt.get("compensation", {}).get("currency")
    if not currency:
        raise InitError("currency is required for this market (add 'currency' to the answers)")
    for k in ("full_name", "email", "floor_gross", "languages", "locations"):
        if a.get(k) in (None, "", [], {}):
            raise InitError(f"missing answer: {k}")
    comp = {"currency": currency, "floor_gross": a["floor_gross"]}
    for k in ("period", "floor_net", "ask_gross"):
        if a.get(k) is not None:
            comp[k] = a[k]
    prof: dict = {
        "schema_version": 1,
        "presets": {"role": role, "market": market},
        "identity": {"full_name": a["full_name"], "email": a["email"]},
        "targets": {},
        "locations": {"accepted": a["locations"]},
        "compensation": comp,
        "languages": {"spoken": a["languages"]},
        "scoring": {"weights": DEFAULT_WEIGHTS, "thresholds": DEFAULT_THRESHOLDS},
        "tracker": {"sheet": "Pipeline"},
    }
    if a.get("phone"):
        prof["identity"]["phone"] = a["phone"]
    if a.get("roles"):
        prof["targets"]["roles"] = a["roles"]
    if a.get("seniority"):
        prof["targets"]["seniority"] = a["seniority"]
    if a.get("authorized_in"):
        prof["work_authorization"] = {"authorized_in": a["authorized_in"]}
    if a.get("effective_deduction_rate") is not None:
        prof["market_params"] = {"generic_flat": {"effective_deduction_rate": a["effective_deduction_rate"]}}
    return prof


def copy_template(target: Path, market: str):
    for src in TEMPLATE.rglob("*"):
        if src.is_dir():
            continue
        rel = src.relative_to(TEMPLATE)
        name = rel.name
        if name.endswith(".skeleton.md"):
            rel = rel.with_name(name.replace(".skeleton.md", ".md"))
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    shutil.copy2(PLUGIN / "presets" / "markets" / f"{market}.md", target / "docs" / "salary-rules.md")


def create_tracker(target: Path, prof: jp.Profile):
    """Header row only (names from tracker.columns or the defaults); restyle_tracker.py applies styling."""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = prof["tracker"]["sheet"]
    ws.append(prof.tracker_columns)
    wb.save(target / "applications-tracker.xlsx")


def _cleanup(target: Path, created: bool):
    """Remove only what this run wrote: the whole directory if we created it, else its contents."""
    if created:
        shutil.rmtree(target, ignore_errors=True)
        return
    for child in target.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child, ignore_errors=True)
        else:
            child.unlink(missing_ok=True)


def init(target: Path, answers: dict, cv: Path | None, market: str, role: str) -> list[str]:
    if target == PLUGIN or PLUGIN in target.parents:
        raise InitError("The workspace holds personal data and must live outside the plugin repository")
    if target.exists() and not target.is_dir():
        raise InitError(f"Target {target} exists and is not a directory")
    if target.exists() and any(target.iterdir()):
        raise InitError(f"Target {target} exists and is not empty; refusing to overwrite")
    if cv is not None and (not cv.is_file() or cv.suffix.lower() != ".docx"):
        raise InitError(f"--cv must be an existing .docx file (got {cv})")
    prof_data = build_profile(answers, role, market)      # validates answers and preset names before anything is written
    created = not target.exists()
    target.mkdir(parents=True, exist_ok=True)
    notes: list[str] = []
    try:
        (target / "profile.yaml").write_text(yaml.safe_dump(prof_data, sort_keys=False, allow_unicode=True), encoding="utf-8")
        try:
            merged = jp.load_profile(target)   # validates schema + cross-field rules, merges presets
        except jp.ProfileError as e:
            raise InitError(str(e)) from None
        copy_template(target, market)
        create_tracker(target, merged)
        if cv:
            dest = target / merged["paths"]["base_cv"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(cv, dest)
            notes.append(f"Base CV copied to {dest.relative_to(target)}")
            try:
                import docx
                from lib import cvbuild
                m = cvbuild.cv_map(merged, docx.Document(str(dest)).paragraphs)
                notes.append(f"CV structure OK: summary p{m['summary']}, {len(m['skills'])} skills lines")
            except SystemExit as e:
                notes.append(f"WARNING CV structure: {e}")
            except Exception as e:  # noqa: BLE001 - report, do not fail the whole init
                notes.append(f"WARNING could not read the CV: {e}")
        else:
            notes.append("No CV given: put your base CV in cv_base/ (see cv_base/README.md)")
    except BaseException:
        _cleanup(target, created)
        raise
    if shutil.which("soffice") is None:
        notes.append("WARNING LibreOffice (soffice) not found: PDF builds will fail until it is installed")
    return notes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", required=True, help="new workspace directory (must not exist or be empty)")
    ap.add_argument("--answers", required=True, help="JSON file with the user's answers")
    ap.add_argument("--cv", help="path to the user's base CV (.docx)")
    ap.add_argument("--market", default="generic")
    ap.add_argument("--role", default="generic")
    a = ap.parse_args()
    try:
        answers = json.loads(Path(a.answers).read_text(encoding="utf-8"))
        notes = init(Path(a.target).expanduser().resolve(), answers, Path(a.cv).expanduser() if a.cv else None, a.market, a.role)
    except (InitError, OSError, json.JSONDecodeError) as e:
        sys.exit(f"init_workspace: {e}")
    print(f"Workspace created: {Path(a.target).expanduser().resolve()}")
    for n in notes:
        print(f"  - {n}")
    print(f"Next: fill knowledge-base.md, then run: python3 {Path(__file__).resolve().parent / 'jobprofile.py'} --workspace {Path(a.target).expanduser().resolve()}")


if __name__ == "__main__":
    main()
