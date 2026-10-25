"""二分类概率检查与独立留出校准；只打印结果，不改写分类训练报告。"""

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, log_loss
from sklearn.pipeline import Pipeline
from sklearn.utils.validation import check_is_fitted

from app.data import make_customer_dataset
from app.modeling import make_preprocessor, split_data


def validate_predictions(labels, probabilities) -> tuple[np.ndarray, np.ndarray]:
    """本课只接收非空、一维、等长的 0/1 标签及正类概率。"""
    labels = np.asarray(labels, dtype=float)
    probabilities = np.asarray(probabilities, dtype=float)
    if labels.ndim != 1 or probabilities.ndim != 1:
        raise ValueError("标签与概率必须是一维数组")
    if labels.size == 0 or labels.shape != probabilities.shape:
        raise ValueError("标签与概率必须非空且等长")
    if not np.isfinite(labels).all() or not np.isfinite(probabilities).all():
        raise ValueError("标签与概率必须是有限数值")
    if not np.isin(labels, [0, 1]).all():
        raise ValueError("本课标签只能为 0 或 1，正类固定为 1")
    if np.any(probabilities < 0) or np.any(probabilities > 1):
        raise ValueError("概率必须在 [0, 1] 内")
    return labels, probabilities


def reliability_table(labels, probabilities, n_bins: int = 5) -> list[dict]:
    """等宽分箱：第一箱 [0, upper]，后续箱 (lower, upper]。"""
    labels, probabilities = validate_predictions(labels, probabilities)
    if type(n_bins) is not int or n_bins < 1:
        raise ValueError("n_bins 必须是正整数")
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    rows = []
    for index in range(n_bins):
        lower = edges[index]
        upper = edges[index + 1]
        if index == 0:
            selected = (probabilities >= lower) & (probabilities <= upper)
        else:
            selected = (probabilities > lower) & (probabilities <= upper)
        count = int(selected.sum())
        mean_probability = None
        positive_rate = None
        if count > 0:
            mean_probability = float(probabilities[selected].mean())
            positive_rate = float(labels[selected].mean())
        rows.append(
            {
                "lower": float(lower),
                "upper": float(upper),
                "count": count,
                "mean_probability": mean_probability,
                "positive_rate": positive_rate,
            }
        )
    return rows


def probability_metrics(labels, probabilities, n_bins: int = 5) -> dict[str, float]:
    labels, probabilities = validate_predictions(labels, probabilities)
    rows = reliability_table(labels, probabilities, n_bins)
    weighted_gap = 0.0
    for row in rows:
        if row["count"] > 0:
            gap = abs(row["mean_probability"] - row["positive_rate"])
            weighted_gap += row["count"] / len(labels) * gap
    return {
        "brier": float(np.mean((probabilities - labels) ** 2)),
        "ece": weighted_gap,
    }


def print_reliability_table(labels, probabilities, n_bins: int = 5) -> None:
    print("区间              数量    平均概率    正例比例")
    for index, row in enumerate(reliability_table(labels, probabilities, n_bins)):
        bracket = "[" if index == 0 else "("
        interval = f"{bracket}{row['lower']:.2f}, {row['upper']:.2f}]"
        if row["count"] == 0:
            print(f"{interval:<18}{0:>4}      --          --")
        else:
            print(
                f"{interval:<18}{row['count']:>4}"
                f"      {row['mean_probability']:.4f}      {row['positive_rate']:.4f}"
            )


def require_binary_training_labels(labels) -> None:
    labels = np.asarray(labels)
    if labels.ndim != 1 or not np.array_equal(np.unique(labels), [0, 1]):
        raise ValueError("拟合数据必须同时包含标签 0 和 1")


def fit_base_model(features, labels) -> Pipeline:
    require_binary_training_labels(labels)
    model = Pipeline(
        [
            ("preprocessor", make_preprocessor()),
            ("classifier", LogisticRegression(C=1.0, max_iter=1000, random_state=34)),
        ]
    )
    model.fit(features, labels)
    return model


def fit_calibrator(
    fitted_model: Pipeline, calibration_features, calibration_labels, method="sigmoid"
) -> CalibratedClassifierCV:
    """调用者负责划分独立校准集；冻结包装不会自动检查样本重叠。"""
    if method not in ("sigmoid", "isotonic"):
        raise ValueError("本课只演示 sigmoid 或 isotonic")
    require_binary_training_labels(calibration_labels)
    check_is_fitted(fitted_model)
    if not np.array_equal(fitted_model.classes_, [0, 1]):
        raise ValueError("基础模型类别必须按 [0, 1] 排列")
    calibrated_model = CalibratedClassifierCV(
        FrozenEstimator(fitted_model), method=method, ensemble=False
    )
    calibrated_model.fit(calibration_features, calibration_labels)
    return calibrated_model


def require_disjoint_rows(*feature_groups) -> None:
    """检查本工程保留的唯一行索引；不代表已检查用户实体或时间泄漏。"""
    seen = set()
    for features in feature_groups:
        current = set(features.index)
        if len(current) != len(features) or seen.intersection(current):
            raise ValueError("划分存在重复行索引")
        seen.update(current)


def main() -> None:
    splits = split_data(make_customer_dataset())
    # 此独立实验固定模型和校准法；原 dev 划分在这里专用于校准。
    require_disjoint_rows(splits.x_train, splits.x_dev, splits.x_test)
    base_model = fit_base_model(splits.x_train, splits.y_train)
    calibrated_model = fit_calibrator(base_model, splits.x_dev, splits.y_dev)
    print(
        f"train={len(splits.y_train)}, calibration={len(splits.y_dev)}, "
        f"test={len(splits.y_test)}"
    )
    print("固定方案：逻辑回归 + sigmoid；未根据 test 选模型或校准法")
    for name, model in [("原模型", base_model), ("校准后", calibrated_model)]:
        probabilities = model.predict_proba(splits.x_test)[:, 1]
        metrics = probability_metrics(splits.y_test, probabilities)
        loss = log_loss(splits.y_test, probabilities, labels=[0, 1])
        ap = average_precision_score(splits.y_test, probabilities)
        print(
            f"{name}: Brier={metrics['brier']:.6f}, ECE(5)={metrics['ece']:.6f}, "
            f"LogLoss={loss:.6f}, AP={ap:.6f}"
        )
        print_reliability_table(splits.y_test, probabilities)


if __name__ == "__main__":
    main()
