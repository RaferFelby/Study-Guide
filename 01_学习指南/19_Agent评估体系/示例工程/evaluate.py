import argparse
import hashlib
import json
from pathlib import Path

from agents import run_agent
from dataset import load_cases
from metrics import aggregate, paired_group_bootstrap, score_case


def evaluate(cases, variant):
    return [score_case(case, run_agent(case["input"], variant)) for case in cases]


def build_report(dataset_path: Path, split="test"):
    if split not in {"dev", "test"}:
        raise ValueError("split必须是dev或test")
    cases = [case for case in load_cases(dataset_path) if case["split"] == split]
    before = evaluate(cases, "baseline")
    after = evaluate(cases, "guarded")
    summary_before, summary_after = aggregate(before), aggregate(after)
    paired = [
        {
            "case_id": left["case_id"],
            "before": left["task_success"],
            "after": right["task_success"],
        }
        for left, right in zip(before, after)
    ]
    regressions = [
        row["case_id"] for row in paired if row["before"] and not row["after"]
    ]
    breakdown = {
        scenario: aggregate([row for row in after if row["scenario"] == scenario])
        for scenario in sorted({row["scenario"] for row in after})
    }
    return {
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "split": split,
        "systems": {"baseline": summary_before, "guarded": summary_after},
        "guarded_by_scenario": breakdown,
        "paired_success": paired,
        "bootstrap_delta": paired_group_bootstrap(before, after),
        "regressions": regressions,
        "cost_delta_units": summary_after["cost_units_total"]
        - summary_before["cost_units_total"],
        "gate": {
            "passed": not regressions and all(row["safe"] for row in after),
            "rule": "no task regression and no unsafe write",
        },
        "rows": {"baseline": before, "guarded": after},
        "limitations": [
            "synthetic rules and data",
            "five test groups only",
            "no real LLM judge or human labels",
            "cost is modeled units",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="离线Agent评估与配对回归报告")
    parser.add_argument("--split", choices=("dev", "test"), default="test")
    parser.add_argument("--output", type=Path)
    options = parser.parse_args()
    path = Path(__file__).parent / "fixtures" / "cases.json"
    report = build_report(path, options.split)
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "rows"},
            ensure_ascii=False,
            indent=2,
        )
    )
    if options.output:
        if options.output.exists():
            raise FileExistsError("报告已存在，请使用新文件名保留旧版")
        options.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
