"""运行传统机器学习分类对比，并在独立测试集上做一次最终评估。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.data import make_customer_dataset
from app.evaluation import choose_f1_threshold, evaluate_probabilities
from app.modeling import make_candidate_models, split_data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    output_directory = parser.parse_args().output_dir
    output_directory.mkdir(parents=True, exist_ok=True)

    frame = make_customer_dataset()
    frame.to_csv(output_directory / "synthetic_customers.csv", index=False)
    splits = split_data(frame)

    print(f"Rows: {len(frame)}")
    print(
        "Split sizes: "
        f"train={len(splits.y_train)}, dev={len(splits.y_dev)}, "
        f"test={len(splits.y_test)}"
    )
    print(f"Training positive rate: {splits.y_train.mean():.3f}")

    fitted_models = {}
    dev_scores = {}
    for name, pipeline in make_candidate_models().items():
        pipeline.fit(splits.x_train, splits.y_train)
        fitted_models[name] = pipeline
        dev_probabilities = pipeline.predict_proba(splits.x_dev)[:, 1]
        dev_scores[name] = evaluate_probabilities(splits.y_dev, dev_probabilities)
        print(
            f"{name:>20}  dev AP={dev_scores[name]['average_precision']:.3f}  "
            f"ROC-AUC={dev_scores[name]['roc_auc']:.3f}"
        )

    selected_name = max(
        dev_scores, key=lambda name: dev_scores[name]["average_precision"]
    )
    selected_model = fitted_models[selected_name]
    dev_probabilities = selected_model.predict_proba(splits.x_dev)[:, 1]
    threshold = choose_f1_threshold(splits.y_dev, dev_probabilities)
    test_probabilities = selected_model.predict_proba(splits.x_test)[:, 1]
    test_metrics = evaluate_probabilities(
        splits.y_test, test_probabilities, threshold=threshold
    )
    report = {
        "dataset": "deterministic synthetic customer renewal data",
        "random_seed": 34,
        "selected_model_by_dev_pr_auc": selected_name,
        "selected_model_by_dev_average_precision": selected_name,
        "metric_definitions": {
            "average_precision": "scikit-learn average_precision_score；AP，非梯形PR-AUC",
            "pr_auc": "旧字段兼容别名，数值与 average_precision 相同",
            "selected_model_by_dev_pr_auc": "旧字段兼容；实际按开发集 AP 选择",
        },
        "threshold_selected_on_dev": threshold,
        "dev_model_comparison": dev_scores,
        "test_metrics": test_metrics,
        "test_accuracy": test_metrics["accuracy"],
        "test_balanced_accuracy": test_metrics["balanced_accuracy"],
        "limitations": [
            "数据由已知公式合成，不能代表真实客户或业务效果。",
            "测试集只用于最终评估；不要据此反复调参。",
            "阈值按开发集 F1 选择，不等于业务最优阈值。",
        ],
    }
    (output_directory / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\nSelected model by dev AP: {selected_name}")
    print(f"Threshold selected on dev: {threshold:.2f}")
    print(f"Final test metrics: {test_metrics}")
    print(f"Report written to: {output_directory / 'report.json'}")


if __name__ == "__main__":
    main()
