"""生成固定合成夹具；正常 demo 只读取夹具，不重新生成。"""

import json
from pathlib import Path

# 六个虚构服务，每个有四项政策。同一服务的两种问法放同一 split。
POLICIES = [
    (
        "compute",
        "dev",
        "public",
        "24 hours",
        "14 days",
        "64 GB",
        "compute@example.invalid",
    ),
    (
        "storage",
        "test",
        "public",
        "48 hours",
        "30 days",
        "2 TB",
        "storage@example.invalid",
    ),
    (
        "network",
        "dev",
        "public",
        "12 hours",
        "7 days",
        "10 Gbps",
        "network@example.invalid",
    ),
    (
        "database",
        "test",
        "staff",
        "72 hours",
        "21 days",
        "500 connections",
        "db@example.invalid",
    ),
    (
        "training",
        "dev",
        "staff",
        "6 hours",
        "3 days",
        "4 GPUs",
        "train@example.invalid",
    ),
    (
        "analytics",
        "test",
        "public",
        "36 hours",
        "10 days",
        "8 workers",
        "data@example.invalid",
    ),
]


def build_rows() -> tuple[list[dict], list[dict]]:
    documents = []
    questions = []
    for service, split, permission, cancel, retain, limit, contact in POLICIES:
        values = {
            "cancellation": cancel,
            "retention": retain,
            "capacity": limit,
            "contact": contact,
        }
        for field, answer in values.items():
            document_id = f"{service}-{field}"
            locator = f"policies/{service}.md#{field}"
            text = f"Service: {service}. {field.capitalize()}: {answer}. Policy version: 1."
            documents.append(
                {
                    "document_id": document_id,
                    "service": service,
                    "field": field,
                    "text": text,
                    "locator": locator,
                    "permission": permission,
                }
            )
            variants = {
                "cancellation": [
                    f"What is the {service} cancellation window?",
                    f"How early must I cancel {service}?",
                ],
                "retention": [
                    f"What is the {service} retention period?",
                    f"How long does {service} keep records?",
                ],
                "capacity": [
                    f"What is the {service} capacity limit?",
                    f"What quota does {service} allow?",
                ],
                "contact": [
                    f"What is the {service} contact email?",
                    f"Who should I email about {service}?",
                ],
            }
            for variant_index, query in enumerate(variants[field], start=1):
                questions.append(
                    {
                        "question_id": f"{document_id}-{variant_index}",
                        "query": query,
                        "split": split,
                        "audience": "staff",
                        "answer": answer,
                        "relevant_ids": [document_id],
                        "evidence_locator": locator,
                        "category": "direct" if variant_index == 1 else "paraphrase",
                    }
                )
    unknown_queries = [
        ("dev", "staff", "What is the compute price?", "missing_fact"),
        ("dev", "staff", "What is the network uptime guarantee?", "missing_fact"),
        (
            "dev",
            "staff",
            "What is the compute capacity for the premium plan?",
            "unsupported_qualifier",
        ),
        ("dev", "staff", "What is the quantum capacity limit?", "unknown_service"),
        ("dev", "public", "What is the training capacity limit?", "permission_denied"),
        ("dev", "public", "What is the training contact email?", "permission_denied"),
        ("test", "staff", "What is the storage price?", "missing_fact"),
        (
            "test",
            "staff",
            "What is the storage retention for the premium plan?",
            "unsupported_qualifier",
        ),
        ("test", "staff", "What is the database encryption algorithm?", "missing_fact"),
        ("test", "staff", "What is the archive retention period?", "unknown_service"),
        ("test", "public", "What is the database contact email?", "permission_denied"),
        (
            "test",
            "public",
            "What is the database cancellation window?",
            "permission_denied",
        ),
    ]
    for index, (split, audience, query, category) in enumerate(
        unknown_queries, start=1
    ):
        questions.append(
            {
                "question_id": f"unknown-{index:02d}",
                "query": query,
                "split": split,
                "audience": audience,
                "answer": None,
                "relevant_ids": [],
                "evidence_locator": None,
                "category": category,
            }
        )
    return documents, questions


def main() -> None:
    directory = Path(__file__).parent / "fixtures"
    directory.mkdir(exist_ok=True)
    documents, questions = build_rows()
    for name, rows in [("corpus.json", documents), ("questions.json", questions)]:
        with (directory / name).open("w", encoding="utf-8") as target:
            json.dump(rows, target, ensure_ascii=False, indent=2)
    print(f"生成 {len(documents)} 个证据片段、{len(questions)} 条合成评估题")


if __name__ == "__main__":
    main()
