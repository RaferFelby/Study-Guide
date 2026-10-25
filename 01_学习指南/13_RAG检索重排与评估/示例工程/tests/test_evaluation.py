from pathlib import Path

import pytest

from answering import Answer
from data import Question, load_dataset
from evaluation import classify_failure, evaluate, ranking_metrics, select_threshold
from retrieval import Retriever


def test_hand_calculated_multi_gold_metrics():
    metrics = ranking_metrics(["bad", "a", "b"], ("a", "b"), 3)
    assert metrics["recall"] == 1
    assert metrics["rr"] == 0.5
    assert metrics["ndcg"] == pytest.approx(
        (1 / 1.584962500721156 + 0.5) / (1 + 1 / 1.584962500721156)
    )


@pytest.mark.parametrize(
    "ranked,gold,k", [([], (), 3), (["a", "a"], ("a",), 3), (["a"], ("a",), 0)]
)
def test_invalid_metric_inputs_fail(ranked, gold, k):
    with pytest.raises(ValueError):
        ranking_metrics(ranked, gold, k)


def test_failure_stage_distinguishes_retrieval_and_answer_errors():
    question = Question(
        "q", "query", "test", "staff", "right", ("a",), "a.md#p1", "direct"
    )
    wrong = Answer("wrong", "a", "a.md#p1", 1, "example")
    refusal = Answer(None, None, None, 0, "example")
    assert classify_failure(question, ["b"], wrong) == "retrieval_miss"
    assert classify_failure(question, ["a"], wrong) == "answer_error"
    assert classify_failure(question, ["a"], refusal) == "false_rejection"


def test_dev_only_threshold_selection_and_test_denominators():
    documents, questions = load_dataset(Path(__file__).parents[1] / "fixtures")
    retriever = Retriever(documents)
    dev = [item for item in questions if item.split == "dev"]
    test = [item for item in questions if item.split == "test"]
    threshold, reports = select_threshold(retriever, dev, "rerank", 3)
    assert len(reports) == 4
    with pytest.raises(ValueError):
        select_threshold(retriever, test, "rerank", 3)
    report, rows = evaluate(retriever, test, "rerank", threshold=threshold)
    assert report["answerable"] == 24
    assert report["unanswerable"] == 6
    assert len(rows) == 30
    assert report["unknown_rejection_rate"] == 1
    assert report["coverage"] == 0.8
    assert report["false_rejection_rate"] == 0
