"""人工经验卡的范围检查与迁移试跑；无模型、自动学习或持久经验库。"""

import argparse
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from contrast_lab import (
    BudgetConfig,
    Expense,
    evaluate_budget,
    execute_budget,
    save_report,
)


@dataclass(frozen=True)
class UnitExperience:
    source_task_id: str
    available_after: int
    rule_version: str
    status: str = "active"


@dataclass(frozen=True)
class TaskContext:
    task_id: str
    task_order: int
    rule_version: str


def review_experience(
    experience: UnitExperience, context: TaskContext, expenses: list[Expense]
) -> list[str]:
    """空列表表示允许作为候选试跑，不表示任务已通过。"""
    for position in (experience.available_after, context.task_order):
        if type(position) is not int or position < 1:
            raise ValueError("任务顺序必须是正整数")
    for value in (
        experience.source_task_id,
        experience.rule_version,
        context.task_id,
        context.rule_version,
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("任务编号与规则版本必须是非空字符串")
    if experience.status not in ("active", "revoked"):
        raise ValueError("经验状态只支持 active 或 revoked")
    if not expenses:
        raise ValueError("待处理费用不能为空")

    reasons = []
    if experience.source_task_id == context.task_id:
        reasons.append("same_task")
    if experience.available_after >= context.task_order:
        reasons.append("not_available_yet")
    if experience.status != "active":
        reasons.append("inactive")
    if experience.rule_version != context.rule_version:
        reasons.append("rule_mismatch")
    for expense in expenses:
        if expense.unit not in ("yuan", "fen"):
            reasons.append("unsupported_unit")
            break
    return reasons


def propose_unit_config(
    experience: UnitExperience,
    context: TaskContext,
    expenses: list[Expense],
    base_config: BudgetConfig,
) -> BudgetConfig:
    reasons = review_experience(experience, context, expenses)
    if reasons:
        raise ValueError("不能复用经验：" + ", ".join(reasons))
    # 只改变单位处理，保留当前任务的条目数预算。
    return replace(base_config, normalize_units=True)


def run_transfer(
    experience: UnitExperience,
    context: TaskContext,
    expenses: list[Expense],
    base_config: BudgetConfig,
    expected_fen: int,
) -> dict:
    reasons = review_experience(experience, context, expenses)
    report = {
        "experience": asdict(experience),
        "context": asdict(context),
        "input_snapshot": [asdict(expense) for expense in expenses],
        "base_config": asdict(base_config),
        "skip_reasons": reasons,
        "evaluation_target": None,
        "runs": {},
    }
    if reasons:
        return report
    candidate = propose_unit_config(experience, context, expenses, base_config)
    expected_ids = [expense.item_id for expense in expenses]
    report["evaluation_target"] = {
        "expected_ids": expected_ids,
        "expected_fen": expected_fen,
    }
    for name, config in (("base", base_config), ("candidate", candidate)):
        result = execute_budget(expenses, config)
        # 已知答案只在候选确定并执行后用于教学评价。
        report["runs"][name] = {
            "execution": result,
            "evaluation": evaluate_budget(result, expected_ids, expected_fen),
        }
    return report


def run_examples() -> dict:
    # 人工准备的教学卡：来自上一节的单位核对经验，不保存旧任务答案。
    experience = UnitExperience("task-a", 1, "cny-fen-v1")
    context = TaskContext("task-b", 2, "cny-fen-v1")
    expenses = [Expense("room", 600, "yuan"), Expense("meal", 25000, "fen")]
    base_config = BudgetConfig(2, False)
    cases = [
        ("new_task", experience, context, expenses, 85000),
        (
            "over_budget",
            experience,
            context,
            expenses + [Expense("bus", 50, "yuan")],
            90000,
        ),
        ("future", replace(experience, available_after=3), context, expenses, 85000),
        (
            "same_task",
            replace(experience, source_task_id="task-b", available_after=2),
            context,
            expenses,
            85000,
        ),
        ("revoked", replace(experience, status="revoked"), context, expenses, 85000),
        (
            "changed_rule",
            experience,
            replace(context, rule_version="cny-fen-v2"),
            expenses,
            85000,
        ),
        ("unknown_unit", experience, context, [Expense("room", 10, "dollar")], 0),
    ]
    reports = {}
    for name, entry, task, rows, expected_fen in cases:
        reports[name] = run_transfer(entry, task, rows, base_config, expected_fen)
    return {
        "scope": "人工卡片与确定性规则；七个独立情景，不是真实连续任务流",
        "cases": reports,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="保存新报告，拒绝覆盖")
    args = parser.parse_args()
    report = run_examples()
    if args.output is not None:
        save_report(report, args.output)
    for name, case in report["cases"].items():
        if case["skip_reasons"]:
            print(f"{name}: skip={','.join(case['skip_reasons'])}")
            continue
        result = case["runs"]["candidate"]
        execution = result["execution"]
        print(
            f"{name}: total_fen={execution['total_fen']} "
            f"accepted={result['evaluation']['accepted']} "
            f"max_items={execution['config']['max_items']}"
        )
    if args.output is not None:
        print(f"报告：{args.output}")


if __name__ == "__main__":
    main()
