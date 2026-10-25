"""读取带定位的合成语料和人工设计的评估问题。"""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Document:
    document_id: str
    service: str
    field: str
    text: str
    locator: str
    permission: str


@dataclass(frozen=True)
class Question:
    question_id: str
    query: str
    split: str
    audience: str
    answer: str | None
    relevant_ids: tuple[str, ...]
    evidence_locator: str | None
    category: str


def load_dataset(directory: Path) -> tuple[list[Document], list[Question]]:
    with (directory / "corpus.json").open(encoding="utf-8") as source:
        documents = [Document(**row) for row in json.load(source)]
    with (directory / "questions.json").open(encoding="utf-8") as source:
        rows = json.load(source)
    questions = []
    for row in rows:
        row["relevant_ids"] = tuple(row["relevant_ids"])
        questions.append(Question(**row))
    document_by_id = {item.document_id: item for item in documents}
    if len(document_by_id) != len(documents):
        raise ValueError("语料 document_id 不能重复")
    question_ids = {item.question_id for item in questions}
    if len(question_ids) != len(questions):
        raise ValueError("question_id 不能重复")
    for question in questions:
        if question.split not in {"dev", "test"}:
            raise ValueError("split 必须是 dev 或 test")
        if question.audience not in {"public", "staff"}:
            raise ValueError("audience 必须是 public 或 staff")
        if question.answer is None:
            if question.relevant_ids or question.evidence_locator is not None:
                raise ValueError("无答案题不能有可见证据标注")
            continue
        if not question.relevant_ids:
            raise ValueError("可回答题必须有 relevant_ids")
        for document_id in question.relevant_ids:
            if document_id not in document_by_id:
                raise ValueError(f"证据不存在：{document_id}")
            document = document_by_id[document_id]
            if question.answer not in document.text:
                raise ValueError(f"答案不在证据原文中：{question.question_id}")
            if question.evidence_locator != document.locator:
                raise ValueError("证据定位与语料不一致")
            if question.audience == "public" and document.permission != "public":
                raise ValueError("public 可回答题不能引用 staff 文档")
    return documents, questions
