"""Profile loader (jobprofile, not "profile": that name would shadow the stdlib module): the single place scripts learn who the user is and where the workspace lives.

Resolution order for the workspace root:
  1. explicit argument (--workspace)
  2. env JOBSEARCH_WORKSPACE
  3. nearest parent of the current directory that contains profile.yaml

The plugin root (where schema and presets live) is the parent of scripts/, or CLAUDE_PLUGIN_ROOT if set.
"""
from __future__ import annotations

import copy
import json
import os
import re
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

PLUGIN_ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT") or Path(__file__).resolve().parent.parent)
SCHEMA_PATH = PLUGIN_ROOT / "config" / "profile.schema.json"
PROFILE_NAME = "profile.yaml"

# Generic tracker defaults (override in profile.tracker). Order = sort priority, most actionable first.
DEFAULT_STATUSES = [
    {"name": "OFFER", "color": "#70AD47", "text_color": "#FFFFFF"},
    {"name": "INTERVIEW", "color": "#C6EFCE", "text_color": "#375623"},
    {"name": "SCREENING", "color": "#FFEB9C", "text_color": "#9C6500"},
    {"name": "APPLYING", "color": "#FCE4D6", "text_color": "#C55A11"},
    {"name": "REFERRAL", "color": "#E2CFEC", "text_color": "#7030A0"},
    {"name": "APPLIED", "color": "#FCE4D6", "text_color": "#C55A11"},
    {"name": "CV SENT", "color": "#FCE4D6", "text_color": "#C55A11"},
    {"name": "ANALYZING", "color": "#BDD7EE", "text_color": "#1F4E79"},
    {"name": "To Apply", "color": "#EEEEEE", "text_color": "#1A1A1A"},
    {"name": "BACKLOG", "color": "#EEEEEE", "text_color": "#555555"},
    {"name": "SKIP", "color": "#FCE4E4", "text_color": "#C00000", "dimmed": True},
    {"name": "REJECTED", "color": "#FCE4E4", "text_color": "#C00000", "dimmed": True},
    {"name": "WITHDRAWN", "color": "#EDEDED", "text_color": "#888888", "dimmed": True},
]


class ProfileError(Exception):
    pass


def deep_merge(base: dict, over: dict) -> dict:
    """over wins; dicts merge recursively; everything else (incl. lists) is replaced."""
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def _fill_defaults(schema: dict, data):
    """Fill `default` values from the schema into data (objects only)."""
    if schema.get("type") == "object" and isinstance(data, dict):
        for key, sub in schema.get("properties", {}).items():
            if key not in data:
                if "default" in sub:
                    data[key] = copy.deepcopy(sub["default"])
                elif sub.get("type") == "object" and any("default" in s for s in sub.get("properties", {}).values()):
                    data[key] = {}
            if key in data:
                _fill_defaults(sub, data[key])
    return data


def find_workspace(explicit: str | os.PathLike | None = None) -> Path:
    cand = explicit or os.environ.get("JOBSEARCH_WORKSPACE")
    if cand:
        p = Path(cand).expanduser().resolve()
        if not (p / PROFILE_NAME).exists():
            raise ProfileError(f"No {PROFILE_NAME} in workspace {p}")
        return p
    cur = Path.cwd().resolve()
    for d in [cur, *cur.parents]:
        if (d / PROFILE_NAME).exists():
            return d
    raise ProfileError(f"No {PROFILE_NAME} found from {cur} upwards; pass --workspace or set JOBSEARCH_WORKSPACE")


def _load_preset(kind: str, name: str) -> dict:
    p = PLUGIN_ROOT / "presets" / kind / f"{name}.yaml"
    if not p.exists():
        raise ProfileError(f"Unknown {kind[:-1]} preset '{name}' (expected {p})")
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def validate(data: dict) -> list[str]:
    """Schema validation plus the cross-field rules JSON Schema cannot express. Returns error strings."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errs = [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
            for e in Draft202012Validator(schema).iter_errors(data)]
    w = data.get("scoring", {}).get("weights", {})
    if w and abs(sum(w.values()) - 1.0) > 1e-6:
        errs.append(f"scoring/weights: must sum to 1.0 (got {sum(w.values()):.4f})")
    t = data.get("scoring", {}).get("thresholds", {})
    seq = [t.get(k) for k in ("strong", "good", "moderate", "weak")]
    if all(isinstance(x, int) for x in seq) and not all(a > b for a, b in zip(seq, seq[1:])):
        errs.append("scoring/thresholds: must be strictly descending strong > good > moderate > weak")
    for key in ("base_cv", "knowledge_base", "tracker", "docs_dir", "backup_dir"):
        v = data.get("paths", {}).get(key)
        if v and (os.path.isabs(v) or ".." in Path(v).parts):
            errs.append(f"paths/{key}: must be workspace-relative, no '..' (got {v!r})")
    return errs


class Profile:
    def __init__(self, data: dict, workspace: Path):
        self.data = data
        self.workspace = workspace

    def __getitem__(self, k):
        return self.data[k]

    def get(self, k, default=None):
        return self.data.get(k, default)

    # ---- paths -------------------------------------------------------------
    def path(self, key: str) -> Path:
        return self.workspace / self.data["paths"][key]

    # ---- tracker -----------------------------------------------------------
    @property
    def currency(self) -> str:
        return self.data["compensation"]["currency"]

    @property
    def salary_column(self) -> str:
        return self.data["tracker"].get("salary_column") or f"Salary ({self.currency} gross)"

    @property
    def tracker_columns(self) -> list[str]:
        return self.data["tracker"].get("columns") or [
            "#", "Company", "Role", "Source", "Status", "Match %", self.salary_column, "Applied", "Intro Call",
            "Assignment", "Tech Interview", "Final Interview", "Offer / Rejected", "Next Action", "Folder", "Updated",
        ]

    @property
    def statuses(self) -> list[dict]:
        return self.data["tracker"].get("statuses") or DEFAULT_STATUSES

    # ---- scoring bands -----------------------------------------------------
    @property
    def band_edges(self) -> tuple[int, int, int]:
        t = self.data["scoring"]["thresholds"]
        return t["moderate"], t["good"], t["strong"]

    # ---- output names ------------------------------------------------------
    def output_stem(self, company_slug: str, kind: str) -> str:
        parts = self.data["identity"]["full_name"].split()
        first, last = (parts[0], parts[-1]) if parts else ("", "")
        slug = lambda s: re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")
        return self.data["identity"].get("output_name_pattern", "{first}-{last}-{company_slug}-{kind}").format(
            first=slug(first), last=slug(last), company_slug=company_slug, kind=kind)


def load_profile(workspace: str | os.PathLike | None = None) -> Profile:
    ws = find_workspace(workspace)
    user = yaml.safe_load((ws / PROFILE_NAME).read_text(encoding="utf-8")) or {}
    merged: dict = {}
    presets = user.get("presets", {})
    for kind, key in (("markets", "market"), ("roles", "role")):
        if presets.get(key):
            merged = deep_merge(merged, _load_preset(kind, presets[key]))
    merged = deep_merge(merged, user)
    errs = validate(merged)
    if errs:
        raise ProfileError("Invalid profile.yaml:\n  " + "\n  ".join(errs))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return Profile(_fill_defaults(schema, merged), ws)


def add_workspace_arg(ap):
    ap.add_argument("--workspace", help=f"workspace root containing {PROFILE_NAME} (default: $JOBSEARCH_WORKSPACE or nearest parent of cwd)")


if __name__ == "__main__":
    import argparse
    import sys
    ap = argparse.ArgumentParser(description="Validate and print the merged profile.")
    add_workspace_arg(ap)
    a = ap.parse_args()
    try:
        p = load_profile(a.workspace)
    except ProfileError as e:
        sys.exit(str(e))
    print(f"OK: {p.workspace / PROFILE_NAME} valid ({p.currency}, salary column: {p.salary_column!r})")
