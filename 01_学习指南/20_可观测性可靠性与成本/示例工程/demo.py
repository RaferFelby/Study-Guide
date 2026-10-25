import json
from pathlib import Path

from costs import RATE_VERSION
from pipeline import Pipeline
from reporting import check_slo, summarize, write_dashboard
from workload import make_workload


def run_experiments():
    workload = make_workload()
    experiments = {}
    for variant in ("baseline", "cached", "routed", "cache_routed", "bad_crop"):
        pipeline = Pipeline(variant)
        rows = []
        for task in workload:
            result = pipeline.run(task["input"])
            result["task_id"] = task["task_id"]
            result["quality_passed"] = all(
                result["output"][key] == value for key, value in task["gold"].items()
            )
            rows.append(result)
        experiments[variant] = {
            "summary": summarize(rows),
            "slo": check_slo(rows),
            "rows": rows,
            "events": pipeline.recorder.events,
        }
    return experiments


def main():
    import argparse

    parser = argparse.ArgumentParser(description="合成trace、成本与质量对照")
    parser.add_argument("--output-dir", type=Path)
    options = parser.parse_args()
    experiments = run_experiments()
    for variant, experiment in experiments.items():
        print(variant, json.dumps(experiment["summary"], ensure_ascii=False))
    print("费率版本", RATE_VERSION, "baseline SLO", experiments["baseline"]["slo"])
    if options.output_dir:
        options.output_dir.mkdir(parents=True, exist_ok=False)
        write_dashboard(options.output_dir / "dashboard.html", experiments)
        for variant, experiment in experiments.items():
            with (options.output_dir / f"{variant}-trace.jsonl").open(
                "x", encoding="utf-8"
            ) as stream:
                for event in experiment["events"]:
                    stream.write(json.dumps(event, ensure_ascii=False) + "\n")
        (options.output_dir / "report.json").write_text(
            json.dumps(
                {"rate_version": RATE_VERSION, "experiments": experiments},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print("报告", options.output_dir.resolve())


if __name__ == "__main__":
    main()
