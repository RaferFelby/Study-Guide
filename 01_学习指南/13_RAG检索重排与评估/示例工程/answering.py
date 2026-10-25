"""抽取原文答案的规则基线；不是 LLM，也不保证理解所有限定条件。"""

import re
from dataclasses import dataclass

from retrieval import FIELD_WORDS, SERVICES, Hit, identify_query, tokenize

STOP_WORDS = {
    "what",
    "is",
    "the",
    "how",
    "does",
    "must",
    "i",
    "who",
    "should",
    "about",
    "a",
}
SUPPORTED_WORDS = (
    STOP_WORDS
    | SERVICES
    | {
        "window",
        "period",
        "long",
        "early",
        "allow",
        "for",
        "cancel",
        "keep",
        "records",
    }
)
for field_words in FIELD_WORDS.values():
    SUPPORTED_WORDS.update(field_words)


@dataclass(frozen=True)
class Answer:
    text: str | None
    citation_id: str | None
    locator: str | None
    confidence: float
    reason: str


def answer_question(
    query: str,
    hits: list[Hit],
    threshold: float = 0.0,
    allow_unknown_words: bool = False,
) -> Answer:
    if not 0 <= threshold <= 1:
        raise ValueError("threshold 必须在 0 到 1 之间")
    service, field = identify_query(query)
    if not allow_unknown_words and set(tokenize(query)) - SUPPORTED_WORDS:
        return Answer(None, None, None, 0.0, "问题含基线无法理解的词或限定条件")
    if service is None or field is None:
        return Answer(None, None, None, 0.0, "不认识服务或问题字段")
    query_words = set(tokenize(query)) - STOP_WORDS
    for hit in hits:
        document = hit.document
        if document.service != service or document.field != field:
            continue
        confidence = len(query_words & set(tokenize(document.text))) / max(
            len(query_words), 1
        )
        if confidence < threshold:
            return Answer(None, None, None, confidence, "低于开发集选择的阈值")
        match = re.search(
            rf"{field.capitalize()}: (.*?)\. Policy version:", document.text
        )
        if match is None:
            return Answer(None, None, None, confidence, "证据格式不支持抽取")
        return Answer(
            match.group(1),
            document.document_id,
            document.locator,
            confidence,
            "依据原文抽取",
        )
    return Answer(None, None, None, 0.0, "候选没有服务和字段均匹配的证据")
