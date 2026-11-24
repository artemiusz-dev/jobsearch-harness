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
import string
import sys
import unicodedata
from pathlib import Path

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import _deps  # noqa: E402

_deps.ensure()

import yaml  # noqa: E402
from jsonschema import Draft202012Validator, FormatChecker  # noqa: E402

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
    """Fill `default` values from the schema into data (objects, and the items of arrays of objects)."""
    if schema.get("type") == "object" and isinstance(data, dict):
        for key, sub in schema.get("properties", {}).items():
            if key not in data:
                if "default" in sub:
                    data[key] = copy.deepcopy(sub["default"])
                elif sub.get("type") == "object" and any("default" in s for s in sub.get("properties", {}).values()):
                    data[key] = {}
            if key in data:
                _fill_defaults(sub, data[key])
    elif schema.get("type") == "array" and isinstance(data, list) and isinstance(schema.get("items"), dict):
        for item in data:
            _fill_defaults(schema["items"], item)
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


PRESET_NAME = re.compile(r"^[a-z0-9-]+$")
OUTPUT_FIELDS = {"first", "last", "company_slug", "kind"}
DIR_FIELDS = {"company_slug", "role_slug", "date"}


def _load_preset(kind: str, name: str) -> dict:
    if not isinstance(name, str) or not PRESET_NAME.match(name):
        raise ProfileError(f"Invalid {kind[:-1]} preset name {name!r}: use lowercase letters, digits and '-'")
    p = PLUGIN_ROOT / "presets" / kind / f"{name}.yaml"
    if not p.exists():
        raise ProfileError(f"Unknown {kind[:-1]} preset '{name}' (expected {p})")
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def validate(data: dict) -> list[str]:
    """Schema validation plus the cross-field rules JSON Schema cannot express. Returns error strings."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errs = [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
            for e in Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(data)]
    w = data.get("scoring", {}).get("weights", {})
    if w and abs(sum(w.values()) - 1.0) > 1e-6:
        errs.append(f"scoring/weights: must sum to 1.0 (got {sum(w.values()):.4f})")
    t = data.get("scoring", {}).get("thresholds", {})
    seq = [t.get(k) for k in ("strong", "good", "moderate", "weak")]
    if all(isinstance(x, int) for x in seq) and not all(a > b for a, b in zip(seq, seq[1:])):
        errs.append("scoring/thresholds: must be strictly descending strong > good > moderate > weak")
    def unsafe(v) -> bool:
        return isinstance(v, str) and (os.path.isabs(v) or ".." in Path(v.replace("\\", "/")).parts)

    for key in ("base_cv", "knowledge_base", "tracker", "docs_dir", "backup_dir", "output_dir_pattern"):
        v = data.get("paths", {}).get(key)
        if v and unsafe(v):
            errs.append(f"paths/{key}: must be workspace-relative, no '..' (got {v!r})")
    for v in data.get("tracker", {}).get("archives", []) or []:
        if unsafe(v):
            errs.append(f"tracker/archives: must be workspace-relative, no '..' (got {v!r})")
    errs += _status_role_errors(data.get("tracker", {}))
    errs += _pattern_errors("identity/output_name_pattern", data.get("identity", {}).get("output_name_pattern"), OUTPUT_FIELDS)
    errs += _pattern_errors("paths/output_dir_pattern", data.get("paths", {}).get("output_dir_pattern"), DIR_FIELDS)
    return errs


DEFAULT_STATUS_ROLES = {"open_for_followup": ["APPLIED", "CV SENT"], "replied": ["SCREENING", "INTERVIEW", "OFFER"],
                        "interview": ["INTERVIEW", "OFFER"], "offer": ["OFFER"]}


def _status_role_errors(tracker: dict) -> list[str]:
    """Status names used by the scripts (follow-ups, conversion bands) must exist in a customised pipeline."""
    statuses = tracker.get("statuses")
    if not statuses:
        return []
    names = {s.get("name") for s in statuses if isinstance(s, dict)}
    roles = tracker.get("status_roles")
    if roles is None:
        roles = DEFAULT_STATUS_ROLES                      # what the scripts fall back to
        hint = " (set tracker.status_roles to map your own names)"
    else:
        hint = ""
    errs = []
    for role, wanted in roles.items():
        missing = sorted(n for n in wanted if n not in names)
        if missing:
            errs.append(f"tracker/status_roles/{role}: status(es) {missing} are not in tracker.statuses{hint}")
    return errs


def _pattern_errors(label: str, pattern, allowed: set[str]) -> list[str]:
    if not isinstance(pattern, str):
        return []
    try:
        fields = {f for _, f, _, _ in string.Formatter().parse(pattern) if f}
    except ValueError as exc:
        return [f"{label}: invalid pattern ({exc})"]
    bad = sorted(fields - allowed)
    return [f"{label}: unsupported placeholder(s) {bad}; allowed: {sorted(allowed)}"] if bad else []


def _slug(text: str) -> str:
    """File-name-safe slug that keeps letters from any script (accents folded where Unicode allows)."""
    folded = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    return re.sub(r"[^\w]+", "-", folded).strip("-_")


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
        """File-name stem for a generated document. `kind` is always part of the name, so a CV and a
        letter for the same company can never collide."""
        parts = self.data["identity"]["full_name"].split()
        first, last = ((parts[0], parts[-1]) if len(parts) > 1 else (parts[0], "")) if parts else ("candidate", "")
        pattern = self.data["identity"].get("output_name_pattern") or "{first}-{last}-{company_slug}-{kind}"
        if "{kind}" not in pattern:
            pattern += "-{kind}"
        stem = pattern.format(first=_slug(first), last=_slug(last), company_slug=company_slug, kind=kind)
        return re.sub(r"-{2,}", "-", stem).strip("-")


def load_profile(workspace: str | os.PathLike | None = None) -> Profile:
    ws = find_workspace(workspace)
    user = yaml.safe_load((ws / PROFILE_NAME).read_text(encoding="utf-8")) or {}
    if not isinstance(user, dict):
        raise ProfileError(f"{PROFILE_NAME} must be a YAML mapping")
    merged: dict = {}
    presets = user.get("presets") or {}
    if not isinstance(presets, dict):
        raise ProfileError("presets must be a mapping with optional 'role' and 'market'")
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
    ap.add_argument("--json", action="store_true", help="print the merged profile (presets + profile.yaml + defaults) as JSON")
    add_workspace_arg(ap)
    a = ap.parse_args()
    try:
        p = load_profile(a.workspace)
    except ProfileError as e:
        sys.exit(str(e))
    if a.json:
        print(json.dumps(p.data, indent=2, ensure_ascii=False))
        sys.exit(0)
    print(f"OK: {p.workspace / PROFILE_NAME} valid ({p.currency}, salary column: {p.salary_column!r})")
