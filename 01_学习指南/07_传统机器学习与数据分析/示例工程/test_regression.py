import numpy as np
import pytest

from regression_demo import fit_and_evaluate, regression_metrics


def test_line_parameters_and_mean_baseline_match_hand_calculation():
    report = fit_and_evaluate([1, 2, 3, 4], [3, 5, 7, 9], [5, 6], [11, 14])
    assert report["slope"] == pytest.approx(2)
    assert report["intercept"] == pytest.approx(1)
    assert report["predictions"] == pytest.approx([11, 13])
    assert report["baseline_predictions"] == [6, 6]
    assert report["model_metrics"] == pytest.approx(
        {"mae": 0.5, "mse": 0.5, "rmse": np.sqrt(0.5), "r2": 7 / 9}
    )
    assert report["baseline_metrics"]["r2"] == pytest.approx(-169 / 9)


def test_heldout_targets_do_not_change_fitted_parameters_or_predictions():
    first = fit_and_evaluate([1, 2, 3], [3, 5, 7], [4, 5], [9, 11])
    changed = fit_and_evaluate([1, 2, 3], [3, 5, 7], [4, 5], [-100, 100])
    for field in (
        "slope",
        "intercept",
        "training_mean",
        "predictions",
        "baseline_predictions",
    ):
        assert first[field] == changed[field]
    assert first["model_metrics"] != changed["model_metrics"]


def test_constant_targets_and_single_target_have_undefined_r2():
    assert regression_metrics([3, 3], [3, 3]) == {
        "mae": 0,
        "mse": 0,
        "rmse": 0,
        "r2": None,
    }
    assert regression_metrics([3, 3], [2, 4])["r2"] is None
    assert regression_metrics([3], [2])["r2"] is None


def test_same_mae_can_have_different_mse_due_to_concentrated_error():
    concentrated = regression_metrics([0, 0, 0, 0], [0, 0, 0, 4])
    spread = regression_metrics([0, 0, 0, 0], [1, 1, 1, 1])
    assert concentrated["mae"] == spread["mae"] == 1
    assert concentrated["mse"] == 4
    assert spread["mse"] == 1


def test_metrics_scale_with_units_but_r2_does_not():
    first = regression_metrics([11, 14], [11, 13])
    scaled = regression_metrics([11000, 14000], [11000, 13000])
    assert scaled["mae"] == pytest.approx(first["mae"] * 1000)
    assert scaled["rmse"] == pytest.approx(first["rmse"] * 1000)
    assert scaled["mse"] == pytest.approx(first["mse"] * 1000**2)
    assert scaled["r2"] == pytest.approx(first["r2"])


@pytest.mark.parametrize(
    "targets,predictions",
    [
        ([], []),
        ([1], [1, 2]),
        ([float("nan")], [1]),
        ([1], [float("inf")]),
        ([[1]], [1]),
    ],
)
def test_invalid_metric_inputs_are_rejected(targets, predictions):
    with pytest.raises(ValueError):
        regression_metrics(targets, predictions)


@pytest.mark.parametrize(
    "train_x,train_y",
    [([1], [2]), ([1, 1], [2, 3]), ([1, 2], [3]), ([1, float("nan")], [2, 3])],
)
def test_invalid_training_inputs_are_rejected(train_x, train_y):
    with pytest.raises(ValueError):
        fit_and_evaluate(train_x, train_y, [3, 4], [5, 6])


def test_input_arrays_are_not_modified():
    train_x = np.array([1.0, 2.0, 3.0])
    train_y = np.array([3.0, 5.0, 7.0])
    fit_and_evaluate(train_x, train_y, [4, 5], [9, 11])
    np.testing.assert_array_equal(train_x, [1, 2, 3])
    np.testing.assert_array_equal(train_y, [3, 5, 7])
