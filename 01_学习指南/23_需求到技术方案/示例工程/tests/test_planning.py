import json
from copy import deepcopy
from pathlib import Path

import pytest

from planning import projected_value, validate_plan

PLAN = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "plan.json").read_text(
        encoding="utf-8"
    )
)


def test_eight_problem_options_ten_days_thirty_hours():
    result = validate_plan(PLAN)
    assert result["technical_problems"] == 8 and result["workdays"] == 10
    assert result["planned_hours"] == 30
    assert result["estimated_units"] == 20 and result["budget_units"] == 100
    assert all(
        assumption["status"] == "unverified" for assumption in PLAN["assumptions"]
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "too_few_problems",
        "one_option",
        "unknown_selection",
        "over_budget",
        "over_hours",
        "daily_overload",
        "forward_dependency",
        "missing_acceptance",
        "missing_measurement",
        "empty_metrics",
        "empty_risks",
        "wrong_origin",
    ],
)
def test_inconsistent_plan_is_rejected(mutation):
    plan = deepcopy(PLAN)
    if mutation == "too_few_problems":
        plan["technical_problems"] = plan["technical_problems"][:4]
    elif mutation == "one_option":
        plan["technical_problems"][0]["options"] = plan["technical_problems"][0][
            "options"
        ][:1]
    elif mutation == "unknown_selection":
        plan["technical_problems"][0]["selected"] = "missing"
    elif mutation == "over_budget":
        plan["constraints"]["estimated_monthly_cost_units"] = 101
    elif mutation == "over_hours":
        plan["constraints"]["person_hours"] = 29
    elif mutation == "daily_overload":
        plan["milestones"][0]["hours"] = 5
    elif mutation == "forward_dependency":
        plan["milestones"][0]["depends_on"] = ["D10"]
    elif mutation == "missing_acceptance":
        plan["milestones"][0]["acceptance"] = ""
    elif mutation == "missing_measurement":
        plan["metrics"][0]["measurement"] = ""
    elif mutation == "empty_metrics":
        plan["metrics"] = []
    elif mutation == "empty_risks":
        plan["risks"] = []
    else:
        plan["scenario_origin"] = "real_customer"
    with pytest.raises(ValueError):
        validate_plan(plan)


def test_hypothetical_value_and_sensitivity():
    base = projected_value(1000, 0.7, 0.9, 90, 45, 10, 3, 20)
    assert base["saved_hours_projected"] == "7.875"
    assert base["net_units"] == "28.750" and base["roi_ratio"] == "0.575"
    low = projected_value(1000, 0.7, 0.5, 90, 45, 10, 3, 20)
    assert low["net_units"] == "-6.250"
    assert base["status"] == "hypothetical_not_real_roi"


def test_roi_zero_cost_and_invalid_input():
    assert projected_value(1, 1, 1, 60, 30, 0, 0, 0)["roi_ratio"] is None
    for bad in (True, -1, float("inf"), float("nan")):
        with pytest.raises(ValueError):
            projected_value(bad, 0.7, 0.9, 90, 45, 10, 3, 20)
    with pytest.raises(ValueError):
        projected_value(1000, 1.1, 0.9, 90, 45, 10, 3, 20)
    with pytest.raises(ValueError):
        projected_value(1000, 0.7, 0.9, 40, 45, 10, 3, 20)
