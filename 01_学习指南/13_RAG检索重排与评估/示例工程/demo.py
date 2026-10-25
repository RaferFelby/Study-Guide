import argparse
import hashlib
import json
from importlib.metadata import version
from pathlib import Path

from data import load_dataset
from evaluation import evaluate, select_threshold
from retrieval import Retriever


def main() -> None:
    parser = argparse.ArgumentParser(description="离线 RAG 检索与答案评估")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--dimensions", type=int, default=8)
    parser.add_argument(
        "--output", type=Path, default=Path(__file__).parent / "results"
    )
    args = parser.parse_args()
    directory = Path(__file__).parent / "fixtures"
    documents, questions = load_dataset(directory)
    retriever = Retriever(documents, args.dimensions)
    dev_questions = [item for item in questions if item.split == "dev"]
    test_questions = [item for item in questions if item.split == "test"]
    args.output.mkdir(parents=True, exist_ok=True)
    dataset_digest = hashlib.sha256(
        (directory / "questions.json").read_bytes()
    ).hexdigest()
    corpus_digest = hashlib.sha256((directory / "corpus.json").read_bytes()).hexdigest()
    reports = []
    print(
        f"语料={len(documents)}，dev={len(dev_questions)}，test={len(test_questions)}"
    )
    print(f"LSA 维度={retriever.dense_vectors.shape[1]}；非神经 Embedding，CPU 运行")
    for strategy in ["bm25", "dense", "hybrid", "rerank"]:
        threshold, dev_reports = select_threshold(
            retriever, dev_questions, strategy, args.top_k
        )
        report, rows = evaluate(
            retriever, test_questions, strategy, args.top_k, threshold
        )
        reports.append(report)
        print(
            f"{strategy:6s} Recall@{args.top_k}={report['recall_at_k']:.3f} "
            f"MRR={report['mrr_at_k']:.3f} nDCG={report['ndcg_at_k']:.3f} "
            f"答案正确率={report['answer_accuracy']:.3f} 阈值={threshold}"
        )
        with (args.output / f"{strategy}.json").open("w", encoding="utf-8") as target:
            json.dump(
                {"dev_candidates": dev_reports, "test_report": report, "rows": rows},
                target,
                ensure_ascii=False,
                indent=2,
            )
    unsafe_report, unsafe_rows = evaluate(
        retriever, test_questions, "rerank", args.top_k, allow_unknown_words=True
    )
    with (args.output / "unsafe_baseline.json").open("w", encoding="utf-8") as target:
        json.dump(
            {"report": unsafe_report, "rows": unsafe_rows},
            target,
            ensure_ascii=False,
            indent=2,
        )
    print(
        "反例：放过未知限定词后，忠实度代理仍为 "
        f"{unsafe_report['faithfulness_proxy']:.3f}，"
        f"无答案拒答率降为 {unsafe_report['unknown_rejection_rate']:.3f}"
    )
    with (args.output / "summary.json").open("w", encoding="utf-8") as target:
        json.dump(
            {
                "questions_sha256": dataset_digest,
                "corpus_sha256": corpus_digest,
                "requested_dimensions": args.dimensions,
                "actual_dimensions": retriever.dense_vectors.shape[1],
                "top_k": args.top_k,
                "candidate_k": 8,
                "rrf_constant": 60,
                "random_state": 42,
                "scikit_learn_version": version("scikit-learn"),
                "reports": reports,
            },
            target,
            ensure_ascii=False,
            indent=2,
        )
    print(f"逐题结果保存在：{args.output.resolve()}")


if __name__ == "__main__":
    main()
