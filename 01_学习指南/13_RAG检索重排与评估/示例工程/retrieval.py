"""BM25、LSA 稠密检索、RRF 融合与透明规则重排。"""

import math
import re
from collections import Counter
from dataclasses import dataclass

from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from data import Document

SERVICES = {"compute", "storage", "network", "database", "training", "analytics"}
FIELD_WORDS = {
    "cancellation": {"cancellation", "cancel"},
    "retention": {"retention", "keep", "records"},
    "capacity": {"capacity", "quota", "limit"},
    "contact": {"contact", "email"},
}


@dataclass(frozen=True)
class Hit:
    document: Document
    score: float


def tokenize(text: str) -> list[str]:
    """本夹具使用英文，按英文词及数字分词；不是中文通用分词器。"""
    return re.findall(r"[a-z0-9]+", text.lower())


def identify_query(query: str) -> tuple[str | None, str | None]:
    words = set(tokenize(query))
    services = SERVICES & words
    fields = []
    for field, field_words in FIELD_WORDS.items():
        if words & field_words:
            fields.append(field)
    service = next(iter(services)) if len(services) == 1 else None
    field = fields[0] if len(fields) == 1 else None
    return service, field


def rewrite_query(query: str) -> str:
    """保留原问题，只补充识别到的规范字段；不使用评估答案。"""
    _, field = identify_query(query)
    if field is None:
        return query
    return f"{query} {field}"


def reciprocal_rank_fusion(rankings: list[list[Hit]], constant: int = 60) -> list[Hit]:
    if constant <= 0:
        raise ValueError("RRF constant 必须大于 0")
    scores = {}
    documents = {}
    for ranking in rankings:
        seen = set()
        for rank, hit in enumerate(ranking, start=1):
            document_id = hit.document.document_id
            if document_id in seen:
                continue
            seen.add(document_id)
            scores[document_id] = scores.get(document_id, 0.0) + 1 / (constant + rank)
            documents[document_id] = hit.document
    hits = [Hit(documents[key], score) for key, score in scores.items()]
    return sorted(hits, key=lambda hit: (-hit.score, hit.document.document_id))


class Retriever:
    def __init__(self, documents: list[Document], dimensions: int = 8):
        if len(documents) < 2:
            raise ValueError("LSA 教学索引至少需要两个片段")
        if dimensions < 1:
            raise ValueError("dimensions 必须大于 0")
        self.documents = documents
        self.tokens = [Counter(tokenize(item.text)) for item in documents]
        self.lengths = [sum(counter.values()) for counter in self.tokens]
        self.average_length = sum(self.lengths) / len(self.lengths)
        if self.average_length == 0:
            raise ValueError("语料不能全部为空")
        self.document_frequency = Counter()
        for counter in self.tokens:
            self.document_frequency.update(counter.keys())
        self.vectorizer = TfidfVectorizer(tokenizer=tokenize, token_pattern=None)
        sparse_vectors = self.vectorizer.fit_transform(
            [item.text for item in documents]
        )
        component_count = min(
            dimensions, sparse_vectors.shape[1] - 1, len(documents) - 1
        )
        if component_count < 1:
            raise ValueError("LSA 需要至少两个不同词项")
        self.reducer = TruncatedSVD(n_components=component_count, random_state=42)
        self.dense_vectors = normalize(self.reducer.fit_transform(sparse_vectors))

    def search(
        self, query: str, strategy: str, audience: str = "staff", top_k: int = 3
    ) -> list[Hit]:
        if top_k < 1:
            raise ValueError("top_k 必须大于 0")
        if audience not in {"public", "staff"}:
            raise ValueError("未知 audience")
        if strategy not in {"bm25", "dense", "hybrid", "rerank"}:
            raise ValueError("未知检索策略")
        allowed = []
        for index, document in enumerate(self.documents):
            if audience == "staff" or document.permission == "public":
                allowed.append(index)
        if strategy in {"bm25", "dense"}:
            return self._rank(query, strategy, allowed)[:top_k]
        # 原问题和改写问题各走两路，统一按排名融合。
        rankings = []
        for variant in dict.fromkeys([query, rewrite_query(query)]):
            for method in ["bm25", "dense"]:
                rankings.append(self._rank(variant, method, allowed)[:8])
        hits = reciprocal_rank_fusion(rankings)
        if strategy == "rerank":
            service, field = identify_query(query)
            reranked = []
            for hit in hits[:8]:
                # 重排只见 query 和候选元数据，不读 gold answer/relevant_ids。
                pair_score = float(hit.document.service == service) + float(
                    hit.document.field == field
                )
                reranked.append(Hit(hit.document, pair_score + hit.score))
            hits = sorted(
                reranked, key=lambda hit: (-hit.score, hit.document.document_id)
            )
        return hits[:top_k]

    def _rank(self, query: str, method: str, allowed: list[int]) -> list[Hit]:
        if method == "bm25":
            scores = self._bm25_scores(query)
        else:
            sparse_query = self.vectorizer.transform([query])
            dense_query = normalize(self.reducer.transform(sparse_query))
            scores = (self.dense_vectors @ dense_query[0]).tolist()
        hits = []
        for index in allowed:
            if scores[index] > 0:
                hits.append(Hit(self.documents[index], float(scores[index])))
        return sorted(hits, key=lambda hit: (-hit.score, hit.document.document_id))

    def _bm25_scores(self, query: str) -> list[float]:
        scores = []
        document_count = len(self.documents)
        k1 = 1.5
        b = 0.75
        for counter, length in zip(self.tokens, self.lengths):
            score = 0.0
            for word in set(tokenize(query)):
                frequency = counter[word]
                document_frequency = self.document_frequency[word]
                inverse_frequency = math.log(
                    1
                    + (document_count - document_frequency + 0.5)
                    / (document_frequency + 0.5)
                )
                denominator = frequency + k1 * (
                    1 - b + b * length / self.average_length
                )
                score += inverse_frequency * frequency * (k1 + 1) / denominator
            scores.append(score)
        return scores
