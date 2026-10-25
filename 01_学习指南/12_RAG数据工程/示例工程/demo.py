"""Run a local, dependency-free RAG data engineering walkthrough."""

from __future__ import annotations

import tempfile
from pathlib import Path

from chunking import Chunk, fixed_length_chunks, structure_chunks
from ingestion import parse_source
from knowledge_base import KnowledgeBase, SearchResult

FIXTURES = Path(__file__).parent / "fixtures"
EVALUATION_QUERIES = [
    ("GPU 显存训练", "compute", "段落 2"),
    ("服务器风扇散热", "webpage", "网页段落 2"),
    ("公司报销票据", "permissions", "CSV 第 2 行"),
]


def prepare_chunks(strategy: str) -> dict[str, tuple[Path, list[Chunk]]]:
    """Parse all fixtures and apply the requested chunking strategy."""
    chunks_by_source = {}
    for path in sorted(FIXTURES.iterdir()):
        sections = parse_source(path)
        if strategy == "fixed":
            chunks = fixed_length_chunks(sections, chunk_size=32, overlap=6)
        elif strategy == "structure":
            chunks = structure_chunks(sections)
        else:
            raise ValueError(f"未知 chunk 策略：{strategy}")
        chunks_by_source[path.stem] = (path, chunks)
    return chunks_by_source


def run_strategy(
    strategy: str, database_path: Path
) -> tuple[int, int, list[SearchResult]]:
    """Build a throwaway index and evaluate three labeled Recall@3 probes."""
    knowledge_base = KnowledgeBase(database_path)
    for source_id, (path, chunks) in prepare_chunks(strategy).items():
        source_path = str(path.relative_to(Path(__file__).parent))
        knowledge_base.replace_source(source_id, source_path, "v1", "public", chunks)
    recall_hits = 0
    first_query_results = []
    for query_index, (query, gold_source_id, gold_locator) in enumerate(
        EVALUATION_QUERIES
    ):
        results = knowledge_base.search(query, {"public", "staff"}, limit=3)
        has_gold_chunk = any(
            result.source_id == gold_source_id
            and result.locator.startswith(gold_locator)
            for result in results
        )
        if has_gold_chunk:
            recall_hits += 1
        if query_index == 0:
            first_query_results = results
    count = knowledge_base.count_chunks()
    knowledge_base.close()
    return count, recall_hits, first_query_results


def demonstrate_updates(database_path: Path) -> None:
    """Show idempotent ingestion, version replacement, citations, ACL, and delete."""
    path = FIXTURES / "compute.md"
    sections = parse_source(path)
    chunks = structure_chunks(sections)
    knowledge_base = KnowledgeBase(database_path)
    source_path = str(path.relative_to(Path(__file__).parent))
    first_update = knowledge_base.replace_source(
        "compute", source_path, "v1", "public", chunks
    )
    unchanged_update = knowledge_base.replace_source(
        "compute", source_path, "v1", "public", chunks
    )
    query = EVALUATION_QUERIES[0][0]
    results = knowledge_base.search(query, {"public"})
    print(f"首次写入={first_update}，重复写入有变化={unchanged_update}")
    print(f"compute 当前 chunk 数={knowledge_base.count_chunks('compute')}")
    if results:
        result = results[0]
        print(
            f"引用：{result.source_id} ({result.source_path}) / "
            f"{result.version} / {result.locator}"
        )
        print(f"原文片段：{result.text}")
    knowledge_base.replace_source("compute", source_path, "v2", "staff", chunks)
    print(f"v2 后公开权限可见数={len(knowledge_base.search(query, {'public'}))}")
    knowledge_base.delete_source("compute")
    print(f"删除后 compute chunk 数={knowledge_base.count_chunks('compute')}")
    csv_path = FIXTURES / "permissions.csv"
    csv_chunks = structure_chunks(parse_source(csv_path))
    knowledge_base.replace_source(
        "permissions",
        str(csv_path.relative_to(Path(__file__).parent)),
        "v1",
        "public",
        csv_chunks,
    )
    print(
        "CSV 行级权限过滤：public 命中数="
        f"{len(knowledge_base.search('公司报销', {'public'}))}，"
        f"staff 命中数={len(knowledge_base.search('公司报销', {'staff'}))}"
    )
    knowledge_base.close()


def main() -> None:
    print("本演示使用词面重叠，不运行真实 embedding 或生成式模型。")
    with tempfile.TemporaryDirectory() as directory:
        for strategy in ("fixed", "structure"):
            database_path = Path(directory) / f"{strategy}.sqlite3"
            count, recall_hits, results = run_strategy(strategy, database_path)
            print(
                f"策略={strategy}，chunk 数={count}，三条标注 query 的 Recall@3="
                f"{recall_hits}/{len(EVALUATION_QUERIES)}，"
                f"命中={results[0].source_id if results else '无'}"
            )
        demonstrate_updates(Path(directory) / "updates.sqlite3")


if __name__ == "__main__":
    main()
