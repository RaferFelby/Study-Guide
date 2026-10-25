import numpy as np
import pytest
from sklearn.calibration import calibration_curve
from sklearn.exceptions import NotFittedError
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from sklearn.pipeline import Pipeline

from app.data import make_customer_dataset
from app.modeling import split_data
from calibration_demo import (
    fit_base_model,
    fit_calibrator,
    probability_metrics,
    reliability_table,
    require_disjoint_rows,
)


def test_hand_calculation_and_empty_bin():
    labels = [0, 1, 0, 0, 1, 1, 0, 1]
    probabilities = [0.1, 0.1, 0.4, 0.4, 0.6, 0.6, 0.9, 0.9]
    assert probability_metrics(labels, probabilities) == pytest.approx(
        {"brier": 0.285, "ece": 0.4}
    )
    rows = reliability_table(labels, probabilities)
    assert [row["count"] for row in rows] == [2, 2, 2, 0, 2]
    assert rows[3]["mean_probability"] is None
    assert rows[3]["positive_rate"] is None


def test_boundaries_and_library_agree():
    probabilities = np.linspace(0, 1, 6)
    labels = np.array([0, 1, 0, 1, 0, 1])
    rows = reliability_table(labels, probabilities)
    assert [row["count"] for row in rows] == [2, 1, 1, 1, 1]
    true, predicted = calibration_curve(labels, probabilities, n_bins=5)
    assert [row["positive_rate"] for row in rows] == pytest.approx(true)
    assert [row["mean_probability"] for row in rows] == pytest.approx(predicted)
    assert probability_metrics(labels, probabilities)["brier"] == pytest.approx(
        brier_score_loss(labels, probabilities)
    )


def test_empty_bins_omitted_by_library_but_retained_in_table():
    rows = reliability_table([0, 1], [0.1, 0.9])
    true, predicted = calibration_curve([0, 1], [0.1, 0.9], n_bins=5)
    nonempty = [row for row in rows if row["count"] > 0]
    assert len(rows) == 5
    assert len(nonempty) == 2
    assert [row["positive_rate"] for row in nonempty] == pytest.approx(true)
    assert [row["mean_probability"] for row in nonempty] == pytest.approx(predicted)


def test_coarse_ece_can_hide_opposite_errors():
    assert probability_metrics([0, 1], [0.9, 0.1], 1) == pytest.approx(
        {"brier": 0.81, "ece": 0}
    )
    assert probability_metrics([0, 1], [0.9, 0.1], 2)["ece"] == pytest.approx(0.9)


def test_ece_weights_unequal_bins_by_sample_count():
    assert probability_metrics([0, 0, 1], [0.1, 0.1, 0.8]) == pytest.approx(
        {"brier": 0.02, "ece": 2 / 15}
    )


def test_perfect_predictions_include_zero_and_one():
    assert probability_metrics([0, 1], [0, 1]) == {"brier": 0, "ece": 0}


def test_single_class_evaluation_and_input_not_modified():
    labels = np.array([1, 1])
    probabilities = np.array([0.5, 1])
    assert probability_metrics(labels, probabilities)["brier"] == 0.125
    np.testing.assert_array_equal(labels, [1, 1])
    np.testing.assert_array_equal(probabilities, [0.5, 1])


@pytest.mark.parametrize(
    "labels,probabilities",
    [
        ([], []),
        ([0], [0.1, 0.2]),
        ([[0]], [0.1]),
        ([0], [[0.1]]),
        ([2], [0.1]),
        ([0], [-0.1]),
        ([1], [1.1]),
        ([np.nan], [0.1]),
        ([1], [np.inf]),
        ([1], [np.nan]),
    ],
)
def test_invalid_probabilities_rejected(labels, probabilities):
    with pytest.raises(ValueError):
        probability_metrics(labels, probabilities)


@pytest.mark.parametrize("n_bins", [0, -1, True, 1.5])
def test_invalid_bin_count_rejected(n_bins):
    with pytest.raises(ValueError, match="n_bins"):
        reliability_table([0, 1], [0.2, 0.8], n_bins)


@pytest.fixture
def splits():
    return split_data(make_customer_dataset())


def test_split_sizes_and_row_disjointness(splits):
    assert [len(splits.y_train), len(splits.y_dev), len(splits.y_test)] == [
        720,
        240,
        240,
    ]
    require_disjoint_rows(splits.x_train, splits.x_dev, splits.x_test)
    with pytest.raises(ValueError, match="重复"):
        require_disjoint_rows(splits.x_train, splits.x_train)
    with pytest.raises(ValueError, match="重复"):
        require_disjoint_rows(splits.x_train.iloc[[0, 0]])


@pytest.mark.parametrize("method", ["sigmoid", "isotonic"])
def test_frozen_pipeline_and_valid_predictions(splits, method):
    base = fit_base_model(splits.x_train, splits.y_train)
    coefficients = base.named_steps["classifier"].coef_.copy()
    intercept = base.named_steps["classifier"].intercept_.copy()
    numeric_steps = base.named_steps["preprocessor"].named_transformers_["numeric"]
    fill_values = numeric_steps.named_steps["imputer"].statistics_.copy()
    feature_means = numeric_steps.named_steps["scaler"].mean_.copy()
    original = base.predict_proba(splits.x_test)
    calibrated = fit_calibrator(base, splits.x_dev, splits.y_dev, method)
    np.testing.assert_array_equal(base.named_steps["classifier"].coef_, coefficients)
    np.testing.assert_array_equal(base.named_steps["classifier"].intercept_, intercept)
    np.testing.assert_array_equal(
        numeric_steps.named_steps["imputer"].statistics_, fill_values
    )
    np.testing.assert_array_equal(
        numeric_steps.named_steps["scaler"].mean_, feature_means
    )
    np.testing.assert_array_equal(base.predict_proba(splits.x_test), original)
    assert len(calibrated.calibrated_classifiers_) == 1
    predictions = calibrated.predict_proba(splits.x_test)
    assert predictions.shape == (240, 2)
    assert np.isfinite(predictions).all()
    assert np.all((predictions >= 0) & (predictions <= 1))
    np.testing.assert_allclose(predictions.sum(axis=1), 1)


def test_changing_test_labels_only_changes_evaluation(splits):
    base = fit_base_model(splits.x_train, splits.y_train)
    calibrated = fit_calibrator(base, splits.x_dev, splits.y_dev)
    first = calibrated.predict_proba(splits.x_test)[:, 1]
    original_metrics = probability_metrics(splits.y_test, first)
    changed_labels = 1 - splits.y_test
    changed_metrics = probability_metrics(changed_labels, first)
    np.testing.assert_array_equal(calibrated.predict_proba(splits.x_test)[:, 1], first)
    assert original_metrics["brier"] != changed_metrics["brier"]


def test_invalid_training_and_calibration_rejected(splits):
    with pytest.raises(ValueError, match="同时包含"):
        fit_base_model(splits.x_train, np.zeros(len(splits.y_train)))
    base = fit_base_model(splits.x_train, splits.y_train)
    with pytest.raises(ValueError, match="同时包含"):
        fit_calibrator(base, splits.x_dev, np.zeros(len(splits.y_dev)))
    with pytest.raises(ValueError, match="本课只演示"):
        fit_calibrator(base, splits.x_dev, splits.y_dev, "unknown")
    # 用新的未拟合分类器验证调用顺序；不修改已有 base 的步骤。
    unfitted = Pipeline([("classifier", LogisticRegression())])
    with pytest.raises(NotFittedError):
        fit_calibrator(unfitted, splits.x_dev, splits.y_dev)
