"""A stub job-board adapter that returns fixed, fictional results and enforces the contract in docs/adapters.md.

Use it to exercise the whole pipeline without network access:
    from stub_adapter import search, get_details
"""
from __future__ import annotations

import json
from pathlib import Path

JOBS_DIR = Path(__file__).resolve().parent / "jobs"

REQUIRED_RESULT_FIELDS = {"id", "title", "company", "url"}
OPTIONAL_RESULT_FIELDS = {"location", "work_mode", "salary", "posted_at", "source"}
DETAIL_ONLY_FIELDS = {"description", "requirements", "benefits", "expires_at", "applicants", "poster"}
WORK_MODES = {"remote", "hybrid", "onsite"}


def _load() -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(JOBS_DIR.glob("job-*.json"))]


def check_contract(job: dict, detail: bool = False) -> None:
    missing = REQUIRED_RESULT_FIELDS - job.keys()
    if missing:
        raise ValueError(f"adapter result missing required fields: {sorted(missing)}")
    allowed = REQUIRED_RESULT_FIELDS | OPTIONAL_RESULT_FIELDS | (DETAIL_ONLY_FIELDS if detail else set())
    extra = set(job) - allowed
    if extra:
        raise ValueError(f"adapter result has fields outside the contract: {sorted(extra)}")
    if "work_mode" in job and job["work_mode"] not in WORK_MODES:
        raise ValueError(f"bad work_mode: {job['work_mode']}")
    sal = job.get("salary")
    if sal is not None and not {"currency"} <= sal.keys():
        raise ValueError("salary needs a currency")


def search(query: str | None = None, keywords: str | None = None, limit: int = 50, **filters) -> list[dict]:
    """Search tool: returns result objects (no description)."""
    text = f"{query or ''} {keywords or ''}".lower().split()
    out = []
    for job in _load():
        hay = f"{job['title']} {job['description']}".lower()
        if text and not any(t in hay for t in text):
            continue
        r = {k: v for k, v in job.items() if k not in DETAIL_ONLY_FIELDS}
        check_contract(r)
        out.append(r)
    return out[:limit]


def get_details(id: str) -> dict:
    """Get-details tool: returns the result fields plus the verbatim description."""
    for job in _load():
        if job["id"] == id:
            check_contract(job, detail=True)
            return job
    raise KeyError(f"unknown job id: {id}")
