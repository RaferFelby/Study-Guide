"""固定六题、三种种子配对比较；参考只用于选择后的评分。"""

import argparse
import json
from pathlib import Path

from sampling import evaluation_tasks
from strategies import run_strategy


def compare():
    summaries = []
    for strategy, count in (("single", 1), ("vote", 5), ("best_of_n", 5)):
        runs = []
        for seed in (17, 18, 19):
            for task in evaluation_tasks():
                result = run_strategy(task, strategy, count, seed=seed)
                result["correct"] = result["answer"] == task["left"] + task["right"]
                runs.append(result)
        summaries.append(
            {
                "strategy": strategy,
                "count": count,
                "n": len(runs),
                "correct": sum(run["correct"] for run in runs),
                "answered": sum(run["status"] == "answered" for run in runs),
                "attempts": sum(run["attempts"] for run in runs),
                "verifier_calls": sum(run["verifier_calls"] for run in runs),
                "total_bytes": sum(run["total_bytes"] for run in runs),
                "simulated_seconds": sum(run["simulated_seconds"] for run in runs),
                "wall_seconds": sum(run["wall_seconds"] for run in runs),
                "llm_tokens": None,
                "currency_cost": None,
                "runs": runs,
            }
        )
    return {
        "scope": "fixed_synthetic_policy_comparison_not_real_model_benchmark",
        "seeds": [17, 18, 19],
        "unique_tasks": 6,
        "temperature": 1.0,
        "verifier": "exact_arithmetic_rules_not_learned_prm",
        "summaries": summaries,
        "real_llm_quality_cost_verified": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("report-my-01.json"))
    args = parser.parse_args()
    report = compare()
    with args.output.open("x", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)
    print(
        json.dumps(
            [
                {key: value for key, value in item.items() if key != "runs"}
                for item in report["summaries"]
            ],
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
