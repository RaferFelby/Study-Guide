"""逐题记录证据排名、答案和失败阶段；gold 只在这里用于打分。"""

import math

from answering import Answer, answer_question
from data import Question
from retrieval import Retriever


def ranking_metrics(
    ranked_ids: list[str], relevant_ids: tuple[str, ...], top_k: int
) -> dict[str, float]:
    if top_k < 1:
        raise ValueError("top_k 必须大于 0")
    if not relevant_ids:
        raise ValueError("无答案题不进入检索 Recall/MRR/nDCG 分母")
    if len(ranked_ids) != len(set(ranked_ids)):
        raise ValueError("排名不能有重复 document_id")
    relevant = set(relevant_ids)
    top_ids = ranked_ids[:top_k]
    recall = len(set(top_ids) & relevant) / len(relevant)
    reciprocal_rank = 0.0
    discounted_gain = 0.0
    for rank, document_id in enumerate(top_ids, start=1):
        if document_id in relevant:
            if reciprocal_rank == 0:
                reciprocal_rank = 1 / rank
            discounted_gain += 1 / math.log2(rank + 1)
    ideal_gain = sum(
        1 / math.log2(rank + 1) for rank in range(1, min(top_k, len(relevant)) + 1)
    )
    return {
        "recall": recall,
        "rr": reciprocal_rank,
        "ndcg": discounted_gain / ideal_gain,
    }


def classify_failure(question: Question, ranked_ids: list[str], answer: Answer) -> str:
    if question.answer is None:
        return "correct_rejection" if answer.text is None else "unsupported_answer"
    if not set(ranked_ids) & set(question.relevant_ids):
        return "retrieval_miss"
    if answer.text is None:
        return "false_rejection"
    if answer.text != question.answer:
        return "answer_error"
    return "correct_answer"


def evaluate(
    retriever: Retriever,
    questions: list[Question],
    strategy: str,
    top_k: int = 3,
    threshold: float = 0.0,
    allow_unknown_words: bool = False,
) -> tuple[dict, list[dict]]:
    if not questions:
        raise ValueError("评估集不能为空")
    rows = []
    metric_sums = {"recall": 0.0, "rr": 0.0, "ndcg": 0.0}
    answerable_count = 0
    answered_count = 0
    correct_count = 0
    faithful_count = 0
    accurate_citations = 0
    rejected_answerable = 0
    correct_unknown_rejections = 0
    failures = {}
    for question in questions:
        hits = retriever.search(question.query, strategy, question.audience, top_k)
        ranked_ids = [hit.document.document_id for hit in hits]
        answer = answer_question(question.query, hits, threshold, allow_unknown_words)
        failure = classify_failure(question, ranked_ids, answer)
        failures[failure] = failures.get(failure, 0) + 1
        if question.answer is not None:
            answerable_count += 1
            metrics = ranking_metrics(ranked_ids, question.relevant_ids, top_k)
            for name, value in metrics.items():
                metric_sums[name] += value
            if answer.text is None:
                rejected_answerable += 1
        elif answer.text is None:
            correct_unknown_rejections += 1
        is_correct = answer.text == question.answer
        correct_count += int(is_correct)
        if answer.text is not None:
            answered_count += 1
            cited_document = next(
                (
                    hit.document
                    for hit in hits
                    if hit.document.document_id == answer.citation_id
                ),
                None,
            )
            is_faithful = (
                cited_document is not None
                and answer.text in cited_document.text
                and answer.locator == cited_document.locator
            )
            faithful_count += int(is_faithful)
            accurate_citations += int(
                answer.citation_id in question.relevant_ids
                and answer.locator == question.evidence_locator
            )
        rows.append(
            {
                "question_id": question.question_id,
                "query": question.query,
                "category": question.category,
                "audience": question.audience,
                "ranked_ids": ranked_ids,
                "gold_ids": question.relevant_ids,
                "gold_answer": question.answer,
                "answer": answer.text,
                "citation_id": answer.citation_id,
                "locator": answer.locator,
                "confidence": answer.confidence,
                "reason": answer.reason,
                "stage": failure,
            }
        )
    unknown_count = len(questions) - answerable_count
    report = {
        "strategy": strategy,
        "questions": len(questions),
        "answerable": answerable_count,
        "unanswerable": unknown_count,
        "top_k": top_k,
        "threshold": threshold,
        "recall_at_k": metric_sums["recall"] / answerable_count
        if answerable_count
        else None,
        "mrr_at_k": metric_sums["rr"] / answerable_count if answerable_count else None,
        "ndcg_at_k": metric_sums["ndcg"] / answerable_count
        if answerable_count
        else None,
        "answer_accuracy": correct_count / len(questions),
        "coverage": answered_count / len(questions),
        "faithfulness_proxy": faithful_count / answered_count
        if answered_count
        else None,
        "citation_accuracy": accurate_citations / answered_count
        if answered_count
        else None,
        "false_rejection_rate": rejected_answerable / answerable_count
        if answerable_count
        else None,
        "unknown_rejection_rate": correct_unknown_rejections / unknown_count
        if unknown_count
        else None,
        "failures": failures,
    }
    return report, rows


def select_threshold(
    retriever: Retriever, dev_questions: list[Question], strategy: str, top_k: int
) -> tuple[float, list[dict]]:
    if not dev_questions or any(question.split != "dev" for question in dev_questions):
        raise ValueError("阈值只能用非空 dev 集选择")
    reports = []
    for threshold in [0.0, 0.4, 0.6, 0.8]:
        report, _ = evaluate(retriever, dev_questions, strategy, top_k, threshold)
        reports.append(report)
    # 本教学目标是整体精确答案/拒答正确率；同分选择覆盖率更高者。
    best = max(
        reports, key=lambda report: (report["answer_accuracy"], report["coverage"])
    )
    return best["threshold"], reports
