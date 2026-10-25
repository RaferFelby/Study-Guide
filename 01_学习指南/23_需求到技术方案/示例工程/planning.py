"""技术方案结构/预算一致性检查；不能替代真实需求访谈或性能实验。"""

import math
from decimal import Decimal


def finite_number(value, name, minimum=0):
    if type(value) not in (int, float) or not math.isfinite(value) or value < minimum:
        raise ValueError(f"{name}需为至少{minimum}的有限数")


def validate_plan(plan):
    if plan.get("scenario_origin") != "simulated":
        raise ValueError("本示例方案必须明确标记模拟来源")
    problems = plan["technical_problems"]
    if len(problems) < 5 or len({problem["id"] for problem in problems}) != len(
        problems
    ):
        raise ValueError("至少五个唯一技术子问题")
    for problem in problems:
        options = problem["options"]
        if len(options) < 2 or len({option["id"] for option in options}) != len(
            options
        ):
            raise ValueError("每个问题至少两个唯一方案")
        if (
            problem["selected"] not in {option["id"] for option in options}
            or not problem["reason"].strip()
        ):
            raise ValueError("选项与取舍理由必须明确")
        if any(not option["tradeoff"].strip() for option in options):
            raise ValueError("选项必须说明代价")
    constraints = plan["constraints"]
    for name in (
        "person_hours",
        "max_hours_per_day",
        "monthly_cost_budget_units",
        "estimated_monthly_cost_units",
        "memory_gb",
        "gpu_count",
    ):
        finite_number(constraints[name], name)
    if (
        constraints["estimated_monthly_cost_units"]
        > constraints["monthly_cost_budget_units"]
    ):
        raise ValueError("估算费用超过给定预算")
    milestones = plan["milestones"]
    ids = [milestone["id"] for milestone in milestones]
    if len(ids) != 10 or len(set(ids)) != 10:
        raise ValueError("两周计划需十个唯一工作日记录")
    available = set()
    total_hours = 0
    for milestone in milestones:
        finite_number(milestone["hours"], "milestone.hours")
        if milestone["hours"] > constraints["max_hours_per_day"]:
            raise ValueError("单日计划超可用时间")
        if not set(milestone["depends_on"]).issubset(available):
            raise ValueError("依赖必须指向此前已安排步骤，不能循环或倒置")
        if not milestone["deliverable"].strip() or not milestone["acceptance"].strip():
            raise ValueError("里程碑需有产物和完成判断")
        available.add(milestone["id"])
        total_hours += milestone["hours"]
    if total_hours > constraints["person_hours"]:
        raise ValueError("总人时超可用范围")
    if not plan["metrics"]:
        raise ValueError("至少需要一项业务指标与测量计划")
    for metric in plan["metrics"]:
        if not all(
            metric[field].strip()
            for field in (
                "business_goal",
                "technical_metric",
                "measurement",
                "acceptance",
            )
        ):
            raise ValueError("指标需映射业务目标、测量与验收")
    if not plan["mvp_in_scope"] or not plan["mvp_out_of_scope"]:
        raise ValueError("MVP范围与排除项必须明确")
    if not plan["risks"]:
        raise ValueError("至少需要一项风险与停止条件")
    if any(not risk["stop_condition"].strip() for risk in plan["risks"]):
        raise ValueError("关键风险必须有停止条件")
    return {
        "technical_problems": len(problems),
        "workdays": len(milestones),
        "planned_hours": total_hours,
        "budget_units": constraints["monthly_cost_budget_units"],
        "estimated_units": constraints["estimated_monthly_cost_units"],
        "evidence_status": "structural_check_only_not_business_validation",
    }


def projected_value(
    monthly_tasks,
    eligible_fraction,
    success_fraction,
    before_seconds,
    after_seconds,
    value_units_per_hour,
    maintenance_hours,
    running_units,
):
    counts = {
        "monthly_tasks": monthly_tasks,
        "eligible_fraction": eligible_fraction,
        "success_fraction": success_fraction,
        "before_seconds": before_seconds,
        "after_seconds": after_seconds,
        "value_units_per_hour": value_units_per_hour,
        "maintenance_hours": maintenance_hours,
        "running_units": running_units,
    }
    for name, value in counts.items():
        finite_number(value, name)
    if eligible_fraction > 1 or success_fraction > 1 or after_seconds > before_seconds:
        raise ValueError("比例不超过1，节省时间计算要求after不大于before")
    numbers = {name: Decimal(str(value)) for name, value in counts.items()}
    hours = (
        numbers["monthly_tasks"]
        * numbers["eligible_fraction"]
        * numbers["success_fraction"]
        * (numbers["before_seconds"] - numbers["after_seconds"])
        / Decimal(3600)
    )
    benefit = hours * numbers["value_units_per_hour"]
    cost = (
        numbers["maintenance_hours"] * numbers["value_units_per_hour"]
        + numbers["running_units"]
    )
    net = benefit - cost
    return {
        "saved_hours_projected": str(hours),
        "benefit_units": str(benefit),
        "cost_units": str(cost),
        "net_units": str(net),
        "roi_ratio": str(net / cost) if cost else None,
        "status": "hypothetical_not_real_roi",
    }
