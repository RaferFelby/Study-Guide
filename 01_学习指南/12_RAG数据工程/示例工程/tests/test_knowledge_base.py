from pathlib import Path

import pytest

from chunking import structure_chunks
from ingestion import SourceSection
from knowledge_base import KnowledgeBase


def make_chunks(text: str = "GPU 显存训练") -> list:
    return structure_chunks([SourceSection(text, "第 4 页 / 段落 2")])


def test_replace_source_skips_unchanged_and_replaces_new_version() -> None:
    database = KnowledgeBase(Path(":memory:"))

    assert database.replace_source("doc", "doc.md", "v1", "staff", make_chunks())
    assert not database.replace_source("doc", "doc.md", "v1", "staff", make_chunks())
    assert database.count_chunks("doc") == 1
    assert database.replace_source(
        "doc", "doc.md", "v2", "staff", make_chunks("GPU 显存上升")
    )

    result = database.search("GPU 显存", {"staff"})[0]
    assert result.version == "v2"
    assert result.source_path == "doc.md"
    assert result.locator == "第 4 页 / 段落 2"
    database.close()


def test_search_filters_permissions_before_returning_citations() -> None:
    database = KnowledgeBase(Path(":memory:"))
    database.replace_source("private", "a.md", "v1", "staff", make_chunks())

    assert database.search("GPU 显存", {"public"}) == []
    assert database.search("GPU 显存", {"staff"})[0].source_id == "private"
    database.close()


def test_delete_removes_source_and_chunks() -> None:
    database = KnowledgeBase(Path(":memory:"))
    database.replace_source("doc", "doc.md", "v1", "public", make_chunks())

    database.delete_source("doc")

    assert database.count_chunks("doc") == 0
    assert database.search("GPU 显存", {"public"}) == []
    database.close()


def test_search_rejects_non_positive_limit() -> None:
    database = KnowledgeBase(Path(":memory:"))
    with pytest.raises(ValueError, match="limit"):
        database.search("问题", {"public"}, limit=0)
    database.close()


def test_chunks_can_keep_different_permissions_within_one_source() -> None:
    database = KnowledgeBase(Path(":memory:"))
    chunks = structure_chunks(
        [
            SourceSection("公司报销需要审批", "CSV 第 2 行", "staff"),
            SourceSection("公开课程开放报名", "CSV 第 3 行", "public"),
        ]
    )
    database.replace_source("policy", "policy.csv", "v1", "public", chunks)

    assert database.search("公司报销", {"public"}) == []
    assert database.search("公司报销", {"staff"})[0].locator == "CSV 第 2 行"
    assert database.search("公开课程", {"public"})[0].locator == "CSV 第 3 行"
    database.close()
