"""同六个固定合成Case的策略回放，不调用LLM或发送外部消息。"""

import argparse
import json
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

from workflow import load_checkpoint, run_workflow


def load_scenarios():
    return json.loads(
        (Path(__file__).parent / "fixtures/scenarios.json").read_text(encoding="utf-8")
    )


def compare_strategies():
    reports = []
    for strategy in ("fixed", "react_policy", "plan_execute"):
        results = [run_workflow(strategy, scenario) for scenario in load_scenarios()]
        reports.append(
            {
                "strategy": strategy,
                "n": len(results),
                "completed": sum(result["status"] == "completed" for result in results),
                "tool_attempts": sum(result["attempts"] for result in results),
                "llm_calls": 0,
                "currency_cost": None,
                "status_counts": dict(Counter(result["status"] for result in results)),
                "results": results,
            }
        )
    return {
        "origin": "six_fixed_synthetic_scenarios",
        "scope": "policy_replay_not_real_model_strategy_benchmark",
        "strategies": reports,
    }


def demonstrate_resume():
    scenario = load_scenarios()[-1]
    with TemporaryDirectory(prefix="workflow-demo-", dir=Path.cwd()) as folder:
        path = Path(folder) / "state.json"
        waiting = run_workflow("plan_execute", scenario, checkpoint_path=path)
        restored = load_checkpoint(path, "plan_execute", scenario)
        completed = run_workflow(
            "plan_execute",
            scenario,
            state=restored,
            checkpoint_path=path,
            simulated_approval=True,
        )
    return {
        "before": waiting["status"],
        "after": completed["status"],
        "attempts_before": waiting["attempts"],
        "attempts_after": completed["attempts"],
        "publication": completed["completed"]["publish"],
        "approval_origin": "simulated_fixture_not_real_human_approval",
    }


def main():
    parser = argparse.ArgumentParser(description="本机确定性规划与修复演练")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = {"comparison": compare_strategies(), "resume": demonstrate_resume()}
    if args.output is not None:
        with args.output.open("x", encoding="utf-8") as output:
            json.dump(report, output, ensure_ascii=False, indent=2)
    print(
        json.dumps(
            {
                "comparison": [
                    {
                        key: item[key]
                        for key in (
                            "strategy",
                            "n",
                            "completed",
                            "tool_attempts",
                            "llm_calls",
                            "currency_cost",
                        )
                    }
                    for item in report["comparison"]["strategies"]
                ],
                "resume": report["resume"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
