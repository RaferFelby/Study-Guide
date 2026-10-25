"""评分官方历史输出，不把本次Prompt演示称为其生成配置。"""

import argparse
import hashlib
import json
import platform
from pathlib import Path

from metrics import paired_bootstrap, wilson_interval
from scoring import NUMERIC_POLICY, grade_numeric
from suite import ARCHIVE_MODELS, PROMPT_VERSION, build_prompt, load_snapshot


def evaluate_records(records, model_name):
    if not records:
        raise ValueError("评测记录不能为空；未评测不等于0%")
    details = []
    for index, record in enumerate(records):
        archived = record[model_name]
        graded = grade_numeric(archived["solution"], record["ground_truth"])
        details.append(
            {
                "task_id": f"gsm8k-archive-{index:04d}",
                "raw_response": archived["solution"],
                "upstream_correct": archived["is_correct"],
                **graded,
            }
        )
    total = len(details)
    correct = sum(row["correct"] for row in details)
    return {
        "n": total,
        "correct": correct,
        "accuracy": correct / total,
        "format_failures": sum(not row["format_valid"] for row in details),
        "upstream_correct": sum(row["upstream_correct"] for row in details),
        "label_disagreements": [
            row["task_id"]
            for row in details
            if row["correct"] != row["upstream_correct"]
        ],
        "wilson_95": wilson_interval(correct, total),
        "details": details,
    }


def run(output_dir):
    records, demos, manifest = load_snapshot()
    results = {name: evaluate_records(records, name) for name in ARCHIVE_MODELS}
    paired = paired_bootstrap(
        [row["correct"] for row in results[ARCHIVE_MODELS[0]]["details"]],
        [row["correct"] for row in results[ARCHIVE_MODELS[1]]["details"]],
    )
    prompts = {str(shots): build_prompt(records[0], demos, shots) for shots in (0, 2)}
    report = {
        "scope": "official_GSM8K_saved_outputs_replay_not_live_generation",
        "python": platform.python_version(),
        "dataset": manifest,
        "evaluator_sha256": {
            name: hashlib.sha256(
                (Path(__file__).parent / name).read_bytes()
            ).hexdigest()
            for name in ("experiment.py", "scoring.py", "metrics.py", "suite.py")
        },
        "extractor": NUMERIC_POLICY,
        "archive_generation_config": {
            "shots": None,
            "temperature": None,
            "top_p": None,
            "precision": None,
            "weights_hash": None,
        },
        "prompt_demo": {
            "version": PROMPT_VERSION,
            "not_archive_prompt": True,
            "sha256": {
                key: hashlib.sha256(value.encode()).hexdigest()
                for key, value in prompts.items()
            },
        },
        "results": results,
        "paired_archive_difference": paired,
        "interval_assumptions": "IID_question_approximation_does_not_cover_contamination_or_protocol_bias",
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for shots, text in prompts.items():
        (output_dir / f"prompt-{shots}-shot.txt").write_text(text, encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.output_dir)
    print(
        json.dumps(
            {
                name: {key: value for key, value in result.items() if key != "details"}
                for name, result in report["results"].items()
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print(json.dumps(report["paired_archive_difference"], indent=2))


if __name__ == "__main__":
    main()
