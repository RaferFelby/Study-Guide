"""切分数据、组装预处理 Pipeline 并比较分类模型。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

TARGET_COLUMN = "renewed"
NUMERIC_FEATURES = ["age", "monthly_usage", "late_payments"]
CATEGORICAL_FEATURES = ["plan_type", "region"]
RANDOM_SEED = 34


@dataclass(frozen=True)
class DataSplits:
    """保留训练、开发和最终测试三份互不重叠的数据。"""

    x_train: pd.DataFrame
    x_dev: pd.DataFrame
    x_test: pd.DataFrame
    y_train: pd.Series
    y_dev: pd.Series
    y_test: pd.Series


def split_data(frame: pd.DataFrame) -> DataSplits:
    """按标签比例分层切出 60%/20%/20% 的训练、开发和测试集。"""
    if TARGET_COLUMN not in frame:
        raise ValueError(f"数据缺少目标列 {TARGET_COLUMN!r}")

    features = frame.drop(columns=TARGET_COLUMN)
    labels = frame[TARGET_COLUMN].astype("int64")
    x_train, x_remaining, y_train, y_remaining = train_test_split(
        features,
        labels,
        test_size=0.4,
        random_state=RANDOM_SEED,
        stratify=labels,
    )
    x_dev, x_test, y_dev, y_test = train_test_split(
        x_remaining,
        y_remaining,
        test_size=0.5,
        random_state=RANDOM_SEED,
        stratify=y_remaining,
    )
    return DataSplits(x_train, x_dev, x_test, y_train, y_dev, y_test)


def make_preprocessor() -> ColumnTransformer:
    """为数值列和类别列分别定义训练集拟合的处理步骤。"""
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, NUMERIC_FEATURES),
            ("categorical", categorical_pipeline, CATEGORICAL_FEATURES),
        ]
    )


def make_candidate_models() -> dict[str, Pipeline]:
    """返回共享同一预处理流程的简单基线、线性模型和树模型。"""
    estimators = {
        "baseline": DummyClassifier(strategy="most_frequent"),
        "logistic_regression": LogisticRegression(
            C=1.0, max_iter=1000, random_state=RANDOM_SEED
        ),
        "decision_tree": DecisionTreeClassifier(
            max_depth=4, min_samples_leaf=20, random_state=RANDOM_SEED
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=200,
            min_samples_leaf=8,
            class_weight="balanced",
            random_state=RANDOM_SEED,
            n_jobs=1,
        ),
        "gradient_boosting": HistGradientBoostingClassifier(
            max_iter=120, l2_regularization=1.0, random_state=RANDOM_SEED
        ),
    }
    return {
        name: Pipeline(
            steps=[("preprocess", make_preprocessor()), ("model", estimator)]
        )
        for name, estimator in estimators.items()
    }
