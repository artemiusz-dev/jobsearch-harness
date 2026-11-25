"""One source of truth: defaults live in the schema, docs quote them, skills and scripts hold no personal values."""
import json
import re
import sys
from pathlib import Path

import jobprofile as jp
import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "config" / "profile.schema.json").read_text(encoding="utf-8"))
SKILLS = sorted((ROOT / "skills").glob("*/SKILL.md"))
sys.path.insert(0, str(ROOT / "scripts"))


def defaults(*path):
    node = SCHEMA["properties"]
    for p in path[:-1]:
        node = node[p]["properties"]
    return node[path[-1]]


# ---------------------------------------------------------------- defaults are stated once
def test_example_profile_and_init_use_the_schema_defaults():
    ex = yaml.safe_load((ROOT / "config" / "profile.example.yaml").read_text(encoding="utf-8"))
    weights = {k: v["default"] for k, v in defaults("scoring", "weights")["properties"].items()}
    thresholds = {k: v["default"] for k, v in defaults("scoring", "thresholds")["properties"].items()}
    assert ex["scoring"]["weights"] == weights and ex["scoring"]["thresholds"] == thresholds
    import init_workspace
    assert init_workspace.DEFAULT_WEIGHTS == weights and init_workspace.DEFAULT_THRESHOLDS == thresholds


def test_rubric_doc_quotes_the_schema_defaults():
    doc = (ROOT / "template" / "docs" / "scoring-rubric.md").read_text(encoding="utf-8")
    for dim, spec in defaults("scoring", "weights")["properties"].items():
        row = next(ln for ln in doc.splitlines() if ln.startswith("|") and any(k in ln for k in {
            "technical": ["Technical Skills"], "experience": ["Experience Match"], "culture": ["Culture"],
            "career": ["Career Alignment"], "compensation": ["| Compensation"]}[dim]))
        assert f"{spec['default']:.2f}" in row, (dim, row)
    t = {k: v["default"] for k, v in defaults("scoring", "thresholds")["properties"].items()}
    for needle in (f"| {t['strong']}+ |", f"| {t['good']}-{t['strong'] - 1} |", f"| {t['moderate']}-{t['good'] - 1} |",
                   f"| {t['weak']}-{t['moderate'] - 1} |", f"| <{t['weak']} |", f"({t['apply_this_week_from']})"):
        assert needle in doc or needle.replace("| ", "").replace(" |", "") in doc, needle
    assert f"(default {defaults('scoring', 'technical_floor')['default']})" in doc


def test_tracker_schema_doc_matches_the_default_pipeline():
    doc = (ROOT / "template" / "docs" / "tracker-schema.md").read_text(encoding="utf-8")
    listed = re.findall(r"^\| `([^`]+)` \|", doc.split("## Valid status values")[1].split("## Status roles")[0], re.M)
    assert listed and set(listed) == {s["name"] for s in jp.DEFAULT_STATUSES}
    order = re.search(r"default\):\n(`.+)", doc).group(1)
    assert re.findall(r"`([^`]+)`", order) == [s["name"] for s in jp.DEFAULT_STATUSES]
    cols_line = doc.split("## Columns (in order)\n")[1].splitlines()[0]
    doc_cols = re.findall(r"`([^`]+)`", cols_line)
    fields = {k: v["default"] for k, v in SCHEMA["properties"]["tracker"]["properties"]["fields"]["properties"].items()}
    stages = [s["column"] for s in SCHEMA["properties"]["tracker"]["properties"]["stages"]["default"]]
    want = [fields[k] for k in ("number", "company", "role", "source", "status", "match")] + ["Salary (<currency> gross)", fields["applied"]] \
        + stages + [fields[k] for k in ("outcome", "next_action", "folder", "updated")]
    assert doc_cols == want


def test_default_status_roles_name_real_default_statuses():
    names = {s["name"] for s in jp.DEFAULT_STATUSES}
    roles = SCHEMA["properties"]["tracker"]["properties"]["status_roles"]["properties"]
    for role, spec in roles.items():
        assert set(spec["default"]) <= names, role


def test_banned_phrase_default_is_not_copied_into_scripts_or_workspace_docs():
    banned = SCHEMA["properties"]["style"]["properties"]["banned_phrases"]["default"]
    for f in [*(ROOT / "scripts").rglob("*.py"), ROOT / "template" / "CLAUDE.md", *(ROOT / "template" / "docs").glob("*.md")]:
        text = f.read_text(encoding="utf-8").lower()
        hits = [b for b in banned if b in text]
        # humanize-rule.md may describe shapes, scripts must not embed the list
        assert not hits or f.name in {"humanize-rule.md", "CLAUDE.md"}, (f.name, hits)
    ats = SCHEMA["properties"]["security"]["properties"]["trusted_ats_domains"]["default"]
    assert not [a for a in ats if a in (ROOT / "template" / "CLAUDE.md").read_text(encoding="utf-8")]


def test_marketplace_never_disagrees_with_plugin_version():
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    for entry in market["plugins"]:
        assert entry.get("version", plugin["version"]) == plugin["version"]


# ---------------------------------------------------------------- skills hold no personal values
STATUS_LITERAL = re.compile(r"`(" + "|".join(re.escape(s["name"]) for s in jp.DEFAULT_STATUSES) + r")`")
NUMBER_LIMIT = re.compile(r"\b\d+(?:-\d+)?\+? ?(?:days?|words|characters|chars)\b|\b\d[\d,]* (?:words|characters)\b")
# a skill may describe a procedure in numbers when it is not a personal limit (none today); list exceptions explicitly
LITERAL_EXCEPTIONS = {"human-text", "interview-material-reviewer", "interview-drillbook"}


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.parent.name)
def test_skills_have_no_status_names_or_numeric_limits(path):
    if path.parent.name in LITERAL_EXCEPTIONS:
        pytest.skip("generic writing or review guidance, no profile-owned limits")
    body = path.read_text(encoding="utf-8").split("---", 2)[2]
    assert not STATUS_LITERAL.findall(body), f"status literal in {path.parent.name}: {STATUS_LITERAL.findall(body)}"
    assert not NUMBER_LIMIT.findall(body), f"numeric limit in {path.parent.name}: {NUMBER_LIMIT.findall(body)}"


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.parent.name)
def test_skill_frontmatter(path):
    head = path.read_text(encoding="utf-8").split("---", 2)[1]
    meta = yaml.safe_load(head)
    assert meta["name"] == path.parent.name and len(meta["description"]) > 40


# ---------------------------------------------------------------- every $P.<field> reference exists in the schema
def schema_has(path: list[str]) -> bool:
    node = SCHEMA
    for part in path:
        for _ in range(2):
            if node.get("type") == "array" and isinstance(node.get("items"), dict):
                node = node["items"]
        props = node.get("properties", {})
        if part in props:
            node = props[part]
        elif isinstance(node.get("additionalProperties"), dict):
            node = node["additionalProperties"]
        elif node.get("additionalProperties") is True:
            return True
        else:
            return False
    return True


REF = re.compile(r"\$P\.([a-z_]+(?:\.[a-z_]+)*)")


def test_every_profile_reference_in_skills_and_templates_exists_in_the_schema():
    files = [*SKILLS, ROOT / "template" / "CLAUDE.md", *(ROOT / "template" / "docs").glob("*.md")]
    bad = []
    for f in files:
        for ref in REF.findall(f.read_text(encoding="utf-8")):
            if not schema_has(ref.split(".")):
                bad.append((f.relative_to(ROOT).as_posix(), ref))
    assert not bad, bad


def test_backticked_profile_paths_in_the_workspace_template_exist():
    text = (ROOT / "template" / "CLAUDE.md").read_text(encoding="utf-8")
    sections = set(SCHEMA["properties"])
    bad = []
    for ref in re.findall(r"`((?:style|followups|tracker|scoring|compensation|work_authorization|security|targets|cv|letter)\.[a-z_.]+)`", text):
        if ref.split(".")[0] in sections and not schema_has(ref.split(".")):
            bad.append(ref)
    assert not bad, bad
