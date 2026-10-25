"""在独立合成耗时数据上比较回归模型；固定开发集选优后才评估测试集。"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeRegressor

from regression_demo import regression_metrics

FEATURE_COLUMNS = ["page_count", "text_chars", "attachment_count"]
TARGET_COLUMN = "duration_minutes"
RANDOM_SEED = 73


@dataclass
class RegressionSplits:
    x_train: pd.DataFrame
    x_dev: pd.DataFrame
    x_test: pd.DataFrame
    y_train: pd.Series
    y_dev: pd.Series
    y_test: pd.Series


def make_duration_dataset(sample_count: int = 300) -> pd.DataFrame:
    if type(sample_count) is not int or sample_count < 30:
        raise ValueError("sample_count 必须是至少 30 的整数")
    generator = np.random.default_rng(RANDOM_SEED)
    pages = generator.integers(1, 21, sample_count)
    characters = np.maximum(100, pages * 400 + generator.normal(0, 300, sample_count))
    attachments = generator.integers(0, 6, sample_count)
    noise = generator.normal(0, 2, sample_count)
    duration = (
        5
        + 0.4 * pages
        + 0.001 * characters
        + 1.5 * attachments
        + 8 * (pages > 12)
        + noise
    )
    frame = pd.DataFrame(
        {
            "page_count": pages.astype(float),
            "text_chars": characters,
            "attachment_count": attachments.astype(float),
            TARGET_COLUMN: duration,
        }
    )
    # 先按完整潜在特征生成标签，再模拟观测缺失；不把目标送进填补器。
    for column in FEATURE_COLUMNS:
        missing = generator.choice(sample_count, size=sample_count // 20, replace=False)
        frame.loc[missing, column] = np.nan
    return frame


def split_regression_data(frame: pd.DataFrame) -> RegressionSplits:
    if len(frame) < 30 or not frame.index.is_unique:
        raise ValueError("至少需要 30 行，且原始行索引必须唯一")
    required = FEATURE_COLUMNS + [TARGET_COLUMN]
    if not frame.columns.is_unique or any(column not in frame for column in required):
        raise ValueError("特征列或目标列缺失，或存在重复列名")
    features = frame[FEATURE_COLUMNS].astype(float)
    targets = frame[TARGET_COLUMN].astype(float)
    if np.isinf(features.to_numpy()).any() or features.isna().all().any():
        raise ValueError("特征不能含无穷值或整列缺失")
    if not np.isfinite(targets.to_numpy()).all():
        raise ValueError("目标必须是完整有限数值")
    x_train, x_remaining, y_train, y_remaining = train_test_split(
        features, targets, test_size=0.4, random_state=RANDOM_SEED
    )
    x_dev, x_test, y_dev, y_test = train_test_split(
        x_remaining, y_remaining, test_size=0.5, random_state=RANDOM_SEED
    )
    if x_train.isna().all().any():
        raise ValueError("训练划分存在整列缺失，不能按训练中位数填补")
    return RegressionSplits(x_train, x_dev, x_test, y_train, y_dev, y_test)


def make_regression_models() -> dict[str, Pipeline]:
    estimators = {
        "mean": DummyRegressor(strategy="mean"),
        "linear": LinearRegression(),
        "ridge_1": Ridge(alpha=1.0, solver="svd"),
        "ridge_100": Ridge(alpha=100.0, solver="svd"),
        "tree_depth_3": DecisionTreeRegressor(
            max_depth=3, min_samples_leaf=8, random_state=RANDOM_SEED
        ),
    }
    models = {}
    for name, estimator in estimators.items():
        steps = [("imputer", SimpleImputer(strategy="median"))]
        if name in ("linear", "ridge_1", "ridge_100"):
            steps.append(("scaler", StandardScaler()))
        steps.append(("model", estimator))
        models[name] = Pipeline(steps)
    return models


def select_on_dev(x_train, y_train, x_dev, y_dev) -> tuple[str, dict, dict]:
    """只接收训练／开发数据；返回选中名称、已拟合模型和比较记录。"""
    if x_train.isna().all().any():
        raise ValueError("训练划分存在整列缺失")
    models = make_regression_models()
    scores = {}
    for name, model in models.items():
        model.fit(x_train, y_train)
        scores[name] = {
            "train": regression_metrics(y_train, model.predict(x_train)),
            "dev": regression_metrics(y_dev, model.predict(x_dev)),
        }
    # 开发集 RMSE 越小越好；完全并列时按候选定义顺序保留第一个。
    selected_name = min(scores, key=lambda name: scores[name]["dev"]["rmse"])
    return selected_name, models, scores


def residual_summary(targets, predictions) -> dict:
    metrics = regression_metrics(targets, predictions)
    residuals = np.asarray(targets, dtype=float) - np.asarray(predictions, dtype=float)
    metrics["mean_residual"] = float(residuals.mean())
    metrics["max_absolute_residual"] = float(np.max(np.abs(residuals)))
    return metrics


def main() -> None:
    splits = split_regression_data(make_duration_dataset())
    print(
        f"train={len(splits.y_train)}, dev={len(splits.y_dev)}, test={len(splits.y_test)}"
    )
    selected_name, models, scores = select_on_dev(
        splits.x_train, splits.y_train, splits.x_dev, splits.y_dev
    )
    for name, score in scores.items():
        print(
            f"{name}: train_RMSE={score['train']['rmse']:.4f}, "
            f"dev_RMSE={score['dev']['rmse']:.4f}, dev_MAE={score['dev']['mae']:.4f}"
        )
    print("开发集选中", selected_name)
    # 本课锁定已拟合状态，不在 train+dev 上重训；测试同时保留固定均值基线。
    final_names = ["mean"]
    if selected_name != "mean":
        final_names.append(selected_name)
    for name in final_names:
        predictions = models[name].predict(splits.x_test)
        metrics = residual_summary(splits.y_test, predictions)
        print(
            "test",
            name,
            {
                key: None if value is None else round(value, 4)
                for key, value in metrics.items()
            },
        )


if __name__ == "__main__":
    main()
