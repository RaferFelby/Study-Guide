"""手工指定候选的确定性对照实验；不是 Harness² 或模型模拟器。"""

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Expense:
    item_id: str
    amount: int
    unit: str


@dataclass(frozen=True)
class BudgetConfig:
    max_items: int | None
    normalize_units: bool


def execute_budget(expenses: list[Expense], config: BudgetConfig) -> dict:
    """按配置逐项计算；金额统一以整数分记录，保留处理轨迹。"""
    if config.max_items is not None and (
        type(config.max_items) is not int or config.max_items < 1
    ):
        raise ValueError("max_items 必须是正整数或 None")
    if type(config.normalize_units) is not bool:
        raise ValueError("normalize_units 必须是布尔值")
    if not expenses:
        raise ValueError("费用列表不能为空")
    seen_ids = set()
    for expense in expenses:
        if not expense.item_id or expense.item_id in seen_ids:
            raise ValueError("费用编号必须非空且唯一")
        seen_ids.add(expense.item_id)
        if type(expense.amount) is not int or expense.amount < 0:
            raise ValueError("金额必须是非负整数")
        if expense.unit not in ("yuan", "fen"):
            raise ValueError(f"不支持的单位：{expense.unit}")

    total_fen = 0
    trace = []
    for expense in expenses:
        if config.max_items is not None and len(trace) >= config.max_items:
            break
        # 关闭归一化是故意保留的错误：把分也当作元。
        if config.normalize_units and expense.unit == "fen":
            contribution_fen = expense.amount
        else:
            contribution_fen = expense.amount * 100
        total_fen += contribution_fen
        trace.append(
            {
                "item_id": expense.item_id,
                "source_amount": expense.amount,
                "source_unit": expense.unit,
                "contribution_fen": contribution_fen,
            }
        )
    return {"config": asdict(config), "total_fen": total_fen, "trace": trace}


def evaluate_budget(result: dict, expected_ids: list[str], expected_fen: int) -> dict:
    """仅供教学的已知答案检查；独立核对处理覆盖与总额。"""
    processed_ids = []
    for step in result["trace"]:
        processed_ids.append(step["item_id"])
    coverage_ok = sorted(processed_ids) == sorted(expected_ids)
    total_ok = result["total_fen"] == expected_fen
    return {
        "coverage_ok": coverage_ok,
        "total_ok": total_ok,
        "accepted": coverage_ok and total_ok,
    }


def run_comparison() -> dict:
    expenses = [
        Expense("venue", 1200, "yuan"),
        Expense("food", 80000, "fen"),
        Expense("travel", 300, "yuan"),
    ]
    # 四套配置由教材作者指定；程序没有自动提出或学习修改。
    configs = {
        "reference": BudgetConfig(2, False),
        "process": BudgetConfig(None, False),
        "domain": BudgetConfig(2, True),
        "composed": BudgetConfig(None, True),
    }
    runs = {}
    for name, config in configs.items():
        result = execute_budget(expenses, config)
        evaluation = evaluate_budget(result, ["venue", "food", "travel"], 230000)
        runs[name] = {"execution": result, "evaluation": evaluation}
    return {
        "scope": "确定性教学实验；手工候选；已知答案；无模型或自动经验库",
        "input_snapshot": [asdict(expense) for expense in expenses],
        "runs": runs,
    }


def save_report(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # x 模式在文件已存在时失败，保护之前的学习记录。
    with path.open("x", encoding="utf-8") as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
        output.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="可选报告路径，拒绝覆盖已有文件")
    args = parser.parse_args()
    report = run_comparison()
    if args.output is not None:
        save_report(report, args.output)
    for name, run in report["runs"].items():
        result = run["execution"]
        evaluation = run["evaluation"]
        print(
            f"{name}: items={len(result['trace'])} total_fen={result['total_fen']} "
            f"coverage={evaluation['coverage_ok']} total={evaluation['total_ok']} "
            f"accepted={evaluation['accepted']}"
        )
    if args.output is not None:
        print(f"报告：{args.output}")


if __name__ == "__main__":
    main()
