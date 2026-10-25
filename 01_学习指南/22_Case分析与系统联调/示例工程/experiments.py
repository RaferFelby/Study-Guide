import argparse
import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path

from cases import make_cases
from contracts import Settings
from pipeline import run_pipeline


def evaluate(settings):
    rows = []
    for case in make_cases():
        result = run_pipeline(case["input"], settings)
        result.update(
            {
                "case_id": case["case_id"],
                "passed": result["output"] == case["gold"],
                "annotation": case["annotation"],
            }
        )
        rows.append(result)
    return {
        "settings": asdict(settings),
        "successes": sum(row["passed"] for row in rows),
        "n": len(rows),
        "attempts": sum(row["tool_attempts"] for row in rows),
        "rows": rows,
    }


def compare(before, after):
    previous = {row["case_id"]: row["passed"] for row in before["rows"]}
    current = {row["case_id"]: row["passed"] for row in after["rows"]}
    if previous.keys() != current.keys():
        raise ValueError("对比需相同任务ID")
    return {
        "improved": [key for key in previous if not previous[key] and current[key]],
        "regressed": [key for key in previous if previous[key] and not current[key]],
        "attempt_delta": after["attempts"] - before["attempts"],
    }


def run_experiments():
    baseline = Settings()
    variants = {
        "baseline": baseline,
        "fix_retrieval": replace(baseline, use_aliases=True),
        "fix_arguments": replace(baseline, correct_argument_name=True),
        "fix_parser": replace(baseline, accept_json_fence=True),
        "fix_permissions": replace(baseline, enforce_owner=True),
        "fix_retry": replace(baseline, max_attempts=2),
        "combined": Settings(True, True, True, True, 2),
    }
    reports = {name: evaluate(settings) for name, settings in variants.items()}
    comparisons = {
        name: compare(reports["baseline"], report)
        for name, report in reports.items()
        if name != "baseline"
    }
    serialized = json.dumps(make_cases(), ensure_ascii=False, sort_keys=True).encode(
        "utf-8"
    )
    return {
        "case_sha256": hashlib.sha256(serialized).hexdigest(),
        "reports": reports,
        "comparisons": comparisons,
        "limitations": [
            "eight synthetic cases only",
            "mock model and transient failure",
            "baseline permission bug intentionally unsafe fixture only",
            "no real production incident",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="五失败Case单变量联调")
    parser.add_argument("--output", type=Path)
    options = parser.parse_args()
    report = run_experiments()
    for name, experiment in report["reports"].items():
        print(
            name,
            f"{experiment['successes']}/{experiment['n']}",
            "工具尝试",
            experiment["attempts"],
        )
        if name != "baseline":
            print(report["comparisons"][name])
    if options.output:
        with options.output.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
