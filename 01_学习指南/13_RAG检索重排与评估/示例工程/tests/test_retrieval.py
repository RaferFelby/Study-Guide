from pathlib import Path

import pytest

from answering import answer_question
from data import load_dataset
from retrieval import Hit, Retriever, reciprocal_rank_fusion, rewrite_query


@pytest.fixture(scope="module")
def dataset():
    return load_dataset(Path(__file__).parents[1] / "fixtures")


@pytest.fixture(scope="module")
def retriever(dataset):
    return Retriever(dataset[0])


def test_fixture_has_sixty_questions_and_disjoint_source_groups(dataset):
    documents, questions = dataset
    assert len(documents) == 24
    assert len(questions) == 60
    assert sum(item.answer is None for item in questions) == 12
    split_ids = {}
    for split in ["dev", "test"]:
        split_ids[split] = {
            identifier
            for question in questions
            if question.split == split
            for identifier in question.relevant_ids
        }
    assert not split_ids["dev"] & split_ids["test"]


@pytest.mark.parametrize("strategy", ["bm25", "dense", "hybrid", "rerank"])
def test_permission_filter_precedes_candidate_selection(retriever, strategy):
    hits = retriever.search("database contact email", strategy, "public", 24)
    assert all(hit.document.permission == "public" for hit in hits)


def test_rewrite_retains_original_question():
    query = "How early must I cancel compute?"
    assert rewrite_query(query) == f"{query} cancellation"
    assert rewrite_query("What is the price?") == "What is the price?"


def test_rrf_uses_rank_and_deduplicates_each_list(dataset):
    first, second = dataset[0][:2]
    result = reciprocal_rank_fusion(
        [[Hit(first, 900), Hit(second, 1)], [Hit(second, 0.2), Hit(second, 0.1)]]
    )
    assert result[0].document.document_id == second.document_id
    assert result[0].score == pytest.approx(1 / 62 + 1 / 61)


def test_rerank_cannot_invent_unrecalled_document(dataset):
    first = dataset[0][0]
    # 重排的输入仅有 first；融合也不会创造新的候选。
    hits = reciprocal_rank_fusion([[Hit(first, 1)]])
    assert {hit.document.document_id for hit in hits} == {first.document_id}


@pytest.mark.parametrize(
    "query",
    [
        "",
        "What is the compute price?",
        "What is the storage retention for the premium plan?",
    ],
)
def test_unknown_or_unsupported_question_is_rejected(retriever, query):
    answer = answer_question(query, retriever.search(query, "rerank"))
    assert answer.text is None
    assert answer.citation_id is None


def test_unsafe_baseline_is_faithful_but_wrong_for_qualifier(retriever):
    query = "What is the storage retention for the premium plan?"
    hits = retriever.search(query, "rerank")
    answer = answer_question(query, hits, allow_unknown_words=True)
    assert answer.text == "30 days"
    assert answer.text in hits[0].document.text
    assert "premium" not in hits[0].document.text


@pytest.mark.parametrize(
    "kwargs", [{"top_k": 0}, {"audience": "admin"}, {"strategy": "magic"}]
)
def test_search_rejects_invalid_parameters(retriever, kwargs):
    parameters = {"strategy": "bm25", **kwargs}
    with pytest.raises(ValueError):
        retriever.search("compute", **parameters)


def test_empty_corpus_and_invalid_dimensions_fail(dataset):
    with pytest.raises(ValueError):
        Retriever([])
    with pytest.raises(ValueError):
        Retriever(dataset[0], dimensions=0)
