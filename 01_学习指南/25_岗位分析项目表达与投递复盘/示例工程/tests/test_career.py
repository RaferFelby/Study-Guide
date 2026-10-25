import json
from copy import deepcopy
from pathlib import Path

import pytest

from career import (
    audit_evidence,
    describe_evidence,
    summarize_applications,
    validate_jobs,
)

ROOT = Path(__file__).parents[1]


def read(name):
    return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))


def test_five_jobs_have_dates_and_no_learner_fit_inference():
    jobs = validate_jobs(read("jobs.json"))
    assert len(jobs) == 5 and all(job["learner_fit"] == "not_assessed" for job in jobs)


@pytest.mark.parametrize(
    "mutation", ["count", "duplicate", "source", "date", "tasks", "fit"]
)
def test_inconsistent_job_snapshot_rejected(mutation):
    jobs = read("jobs.json")
    if mutation == "count":
        jobs = jobs[:4]
    elif mutation == "duplicate":
        jobs[1]["id"] = jobs[0]["id"]
    elif mutation == "source":
        jobs[0]["url"] = "http://untrusted.invalid"
    elif mutation == "date":
        jobs[0]["checked"] = "unknown"
    elif mutation == "tasks":
        jobs[0]["tasks"] = []
    else:
        jobs[0]["learner_fit"] = "qualified"
    with pytest.raises(ValueError):
        validate_jobs(jobs)


def test_evidence_checks_structure_not_semantics_or_authorship():
    evidence = read("evidence.json")
    result = audit_evidence(evidence, ROOT)
    assert result["before"] == "3/8" and result["after"] == "8/8"
    assert result["artifact_exists"] and not result["semantic_claim_verified"]
    assert "个人贡献与独立复现未验证" in describe_evidence(evidence)


@pytest.mark.parametrize(
    "field,value",
    [
        ("after_successes", 9),
        ("n", 0),
        ("n", True),
        ("limits", ""),
        ("artifact", "missing.py"),
        ("authorship", "learner_verified"),
    ],
)
def test_invalid_evidence_and_missing_context_rejected(field, value):
    evidence = read("evidence.json")
    evidence[field] = value
    with pytest.raises(ValueError):
        audit_evidence(evidence, ROOT)


def test_simulated_snapshot_counts_pending_age_and_two_priorities():
    result = summarize_applications(read("applications.json"), "2026-10-11")
    assert result["n"] == 5 and result["stages"]["technical"] == 2
    assert result["priorities"] == ["coding", "project_explanation"]
    assert result["pending_days"] == {"A04": 7}
    assert result["status"].startswith("simulated")


def test_empty_applications_have_no_rates():
    result = summarize_applications([], "2026-10-11")
    assert result["status"] == "no_data" and result["priorities"] == []


@pytest.mark.parametrize(
    "mutation",
    ["duplicate", "unknown_stage", "real_origin", "future_date", "unknown_feedback"],
)
def test_bad_application_records_rejected(mutation):
    rows = deepcopy(read("applications.json"))
    if mutation == "duplicate":
        rows[1]["id"] = rows[0]["id"]
    elif mutation == "unknown_stage":
        rows[0]["stage"] = "hired_unknown"
    elif mutation == "real_origin":
        rows[0]["origin"] = "real"
    elif mutation == "future_date":
        rows[0]["sent"] = "2026-11-01"
    else:
        rows[0]["feedback"] = ["invented"]
    with pytest.raises(ValueError):
        summarize_applications(rows, "2026-10-11")
