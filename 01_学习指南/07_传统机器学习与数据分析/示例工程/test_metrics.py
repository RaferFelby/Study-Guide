import pytest
from app.evaluation import evaluate_probabilities
from sklearn.metrics import auc, precision_recall_curve


def test_average_precision_is_distinct_from_trapezoidal_pr_area():
    labels = [1, 0, 1]
    scores = [0.9, 0.7, 0.4]
    metrics = evaluate_probabilities(labels, scores)
    precision, recall, _ = precision_recall_curve(labels, scores)
    assert metrics["average_precision"] == pytest.approx(5 / 6)
    assert auc(recall, precision) == pytest.approx(19 / 24)
    assert metrics["pr_auc"] == metrics["average_precision"]


def test_lower_threshold_can_increase_both_precision_and_recall():
    labels = [1, 0, 1]
    scores = [0.9, 0.7, 0.4]
    higher = evaluate_probabilities(labels, scores, threshold=0.5)
    lower = evaluate_probabilities(labels, scores, threshold=0.3)
    assert higher["precision"] == 0.5
    assert lower["precision"] == pytest.approx(2 / 3)
    assert higher["recall"] == 0.5
    assert lower["recall"] == 1.0


def test_repeating_same_negative_distribution_preserves_roc_auc():
    original = evaluate_probabilities([1, 0, 1], [0.9, 0.7, 0.4])
    repeated = evaluate_probabilities([1, 0, 0, 0, 1], [0.9, 0.7, 0.7, 0.7, 0.4])
    assert repeated["roc_auc"] == original["roc_auc"]
    assert repeated["average_precision"] < original["average_precision"]


@pytest.mark.parametrize(
    "labels,scores", [([], []), ([1, 1], [0.3, 0.7]), ([0, 1], [0.2, float("nan")])]
)
def test_invalid_metric_inputs_have_clear_errors(labels, scores):
    with pytest.raises(ValueError):
        evaluate_probabilities(labels, scores)
