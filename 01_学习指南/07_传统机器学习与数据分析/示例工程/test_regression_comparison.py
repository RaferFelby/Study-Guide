import numpy as np
import pytest
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeRegressor

from regression_comparison import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    make_duration_dataset,
    make_regression_models,
    residual_summary,
    select_on_dev,
    split_regression_data,
)


def test_ridge_hand_solution():
    x = np.array([[-1.0], [1.0]])
    y = np.array([-2.0, 2.0])
    ridge = Ridge(alpha=2, fit_intercept=False, solver="svd").fit(x, y)
    linear = LinearRegression(fit_intercept=False).fit(x, y)
    assert ridge.coef_ == pytest.approx([1])
    assert linear.coef_ == pytest.approx([2])


def test_scaling_restores_unit_equivalence_for_ridge():
    x = np.array([[-1.0], [1.0]])
    y = np.array([-2.0, 2.0])
    raw = Ridge(alpha=2).fit(x, y)
    raw_large = Ridge(alpha=2).fit(x * 1000, y)
    assert not np.allclose(raw.predict(x), raw_large.predict(x * 1000))
    results = []
    for inputs in (x, x * 1000):
        model = Pipeline([("scale", StandardScaler()), ("model", Ridge(alpha=2))])
        results.append(model.fit(inputs, y).predict(inputs))
    np.testing.assert_allclose(results[0], results[1])
    np.testing.assert_allclose(results[0], [-1, 1])


def test_tree_leaf_means_and_extrapolation_boundary():
    model = DecisionTreeRegressor(max_depth=1, random_state=73)
    model.fit([[1], [2], [3], [4]], [2, 2, 8, 8])
    assert model.tree_.threshold[0] == 2.5
    np.testing.assert_array_equal(model.predict([[0], [1], [4], [10]]), [2, 2, 8, 8])


def test_data_is_reproducible_and_target_not_missing():
    first = make_duration_dataset()
    assert first.equals(make_duration_dataset())
    assert first.shape == (300, 4)
    assert first[FEATURE_COLUMNS].isna().sum().tolist() == [15, 15, 15]
    assert np.isfinite(first[TARGET_COLUMN]).all()


def test_splits_are_disjoint_and_do_not_modify_input():
    frame = make_duration_dataset()
    before = frame.copy(deep=True)
    splits = split_regression_data(frame)
    groups = [splits.x_train, splits.x_dev, splits.x_test]
    assert [len(group) for group in groups] == [180, 60, 60]
    seen = set()
    for group in groups:
        assert not seen.intersection(group.index)
        seen.update(group.index)
        assert group.columns.tolist() == FEATURE_COLUMNS
    assert seen == set(frame.index)
    assert frame.equals(before)
    for features, targets in [
        (splits.x_train, splits.y_train),
        (splits.x_dev, splits.y_dev),
        (splits.x_test, splits.y_test),
    ]:
        assert features.index.equals(targets.index)


def test_selection_and_preprocessing_use_training_data_only():
    splits = split_regression_data(make_duration_dataset())
    selected, models, scores = select_on_dev(
        splits.x_train, splits.y_train, splits.x_dev, splits.y_dev
    )
    assert selected == min(scores, key=lambda name: scores[name]["dev"]["rmse"])
    for model in models.values():
        imputer = model.named_steps["imputer"]
        np.testing.assert_allclose(imputer.statistics_, splits.x_train.median())
        if "scaler" in model.named_steps:
            filled = imputer.transform(splits.x_train)
            np.testing.assert_allclose(
                model.named_steps["scaler"].mean_, filled.mean(axis=0)
            )
        before = imputer.statistics_.copy()
        extreme = splits.x_test.fillna(0) * 1000
        assert np.isfinite(model.predict(extreme)).all()
        np.testing.assert_array_equal(imputer.statistics_, before)
    assert models["mean"].predict(splits.x_test) == pytest.approx(
        np.repeat(splits.y_train.mean(), len(splits.y_test))
    )


def test_test_targets_cannot_change_model_selection_or_predictions():
    frame = make_duration_dataset()
    splits = split_regression_data(frame)
    selected, models, scores = select_on_dev(
        splits.x_train, splits.y_train, splits.x_dev, splits.y_dev
    )
    changed = frame.copy()
    changed.loc[splits.y_test.index, TARGET_COLUMN] += 100
    second = split_regression_data(changed)
    other_name, other_models, other_scores = select_on_dev(
        second.x_train, second.y_train, second.x_dev, second.y_dev
    )
    assert selected == other_name and scores == other_scores
    original_predictions = models[selected].predict(splits.x_test)
    np.testing.assert_array_equal(
        original_predictions, other_models[selected].predict(second.x_test)
    )
    assert (
        residual_summary(splits.y_test, original_predictions)["rmse"]
        != residual_summary(second.y_test, original_predictions)["rmse"]
    )


def test_new_candidates_do_not_share_fitted_steps():
    first = make_regression_models()
    second = make_regression_models()
    assert (
        first["linear"].named_steps["imputer"]
        is not first["ridge_1"].named_steps["imputer"]
    )
    assert (
        first["linear"].named_steps["scaler"]
        is not second["linear"].named_steps["scaler"]
    )


def test_zero_mean_residual_does_not_imply_zero_error():
    report = residual_summary([10, 20], [15, 15])
    assert report["mean_residual"] == 0
    assert report["mae"] == 5
    assert report["rmse"] == 5
    assert report["max_absolute_residual"] == 5


@pytest.mark.parametrize("sample_count", [0, 29, True, 30.5])
def test_invalid_sample_count_rejected(sample_count):
    with pytest.raises(ValueError):
        make_duration_dataset(sample_count)


@pytest.mark.parametrize(
    "problem",
    [
        "missing_column",
        "missing_target",
        "infinite",
        "empty_column",
        "duplicate_index",
        "too_short",
    ],
)
def test_invalid_frames_rejected(problem):
    frame = make_duration_dataset()
    if problem == "missing_column":
        frame = frame.drop(columns=[FEATURE_COLUMNS[0]])
    elif problem == "missing_target":
        frame.loc[0, TARGET_COLUMN] = np.nan
    elif problem == "infinite":
        frame.loc[0, FEATURE_COLUMNS[0]] = np.inf
    elif problem == "empty_column":
        frame[FEATURE_COLUMNS[0]] = np.nan
    elif problem == "duplicate_index":
        frame.index = [0] * len(frame)
    elif problem == "too_short":
        frame = frame.iloc[:10]
    with pytest.raises(ValueError):
        split_regression_data(frame)


def test_all_missing_training_column_is_rejected():
    frame = make_duration_dataset()
    indices = split_regression_data(frame).x_train.index
    frame.loc[indices, FEATURE_COLUMNS[0]] = np.nan
    with pytest.raises(ValueError, match="训练划分"):
        split_regression_data(frame)
