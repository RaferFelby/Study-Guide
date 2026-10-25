"""一维线性回归与训练均值基线；只使用本地合成小数据。"""

import numpy as np
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def as_vector(values, name: str) -> np.ndarray:
    result = np.asarray(values, dtype=float)
    if result.ndim != 1 or result.size == 0:
        raise ValueError(f"{name} 必须是非空一维数值序列")
    if not np.isfinite(result).all():
        raise ValueError(f"{name} 不能包含 NaN 或无穷值")
    return result


def regression_metrics(targets, predictions) -> dict:
    targets = as_vector(targets, "targets")
    predictions = as_vector(predictions, "predictions")
    if targets.shape != predictions.shape:
        raise ValueError("目标与预测数量必须相同")
    mae = float(mean_absolute_error(targets, predictions))
    mse = float(mean_squared_error(targets, predictions))
    rmse = float(np.sqrt(mse))
    if not np.isfinite([mae, mse, rmse]).all():
        raise ValueError("误差统计溢出，请检查数值尺度")
    # 常量目标或不足两个样本时，本教程明确报告 R² 无定义。
    r2 = None
    if len(targets) >= 2 and not np.all(targets == targets[0]):
        r2 = float(r2_score(targets, predictions, force_finite=False))
        if not np.isfinite(r2):
            raise ValueError("R² 统计不是有限数，请检查数值尺度")
    return {"mae": mae, "mse": mse, "rmse": rmse, "r2": r2}


def fit_and_evaluate(train_x, train_y, test_x, test_y) -> dict:
    train_x = as_vector(train_x, "train_x")
    train_y = as_vector(train_y, "train_y")
    test_x = as_vector(test_x, "test_x")
    test_y = as_vector(test_y, "test_y")
    if len(train_x) != len(train_y) or len(test_x) != len(test_y):
        raise ValueError("每组特征与目标数量必须相同")
    if len(train_x) < 2 or np.all(train_x == train_x[0]):
        raise ValueError("本课拟合斜率需要至少两个不同的训练 x")
    train_features = train_x.reshape(-1, 1)
    test_features = test_x.reshape(-1, 1)
    model = LinearRegression()
    baseline = DummyRegressor(strategy="mean")
    model.fit(train_features, train_y)
    baseline.fit(train_features, train_y)
    predictions = model.predict(test_features)
    baseline_predictions = baseline.predict(test_features)
    return {
        "slope": float(model.coef_[0]),
        "intercept": float(model.intercept_),
        "training_mean": float(train_y.mean()),
        "predictions": predictions.tolist(),
        "baseline_predictions": baseline_predictions.tolist(),
        "model_metrics": regression_metrics(test_y, predictions),
        "baseline_metrics": regression_metrics(test_y, baseline_predictions),
    }


def main() -> None:
    report = fit_and_evaluate([1, 2, 3, 4], [3, 5, 7, 9], [5, 6], [11, 14])
    print("斜率与截距", round(report["slope"], 4), round(report["intercept"], 4))
    print("模型预测", [round(value, 4) for value in report["predictions"]])
    print("训练均值基线", report["baseline_predictions"])
    for name in ("model_metrics", "baseline_metrics"):
        print(
            name,
            {
                key: None if value is None else round(value, 4)
                for key, value in report[name].items()
            },
        )


if __name__ == "__main__":
    main()
