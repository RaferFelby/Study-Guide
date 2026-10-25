"""确保教材检查能发现会破坏初学者阅读的围栏问题。"""

from check_guide import check_document


def make_document(tmp_path, body):
    path = tmp_path / "lesson.md"
    path.write_text(
        "---\ntitle: 示例\ntags: [lesson]\nupdated: 2026-10-11\n---\n\n"
        "# 示例\n\n" + body,
        encoding="utf-8",
    )
    return path


def test_python_list_inside_code_is_not_a_wiki_link(tmp_path):
    path = make_document(tmp_path, "```python\nlabels = [[1, 2]]\n```\n")
    assert check_document(path) == []


def test_link_syntax_inside_inline_code_is_not_checked_as_navigation(tmp_path):
    path = make_document(
        tmp_path,
        "写法为 `[[#标题|显示文字]]`、`[源码](./missing.py)`，"
        "也可以用双反引号：`` `[[missing]]` ``。\n",
    )
    assert check_document(path) == []


def test_escaped_code_fence_is_reported(tmp_path):
    path = make_document(tmp_path, "\\`\\`\\`python\nprint(1)\n\\`\\`\\`\n")
    assert "代码围栏被转义，会显示成普通正文" in check_document(path)


def test_unclosed_code_fence_is_reported(tmp_path):
    path = make_document(tmp_path, "```python\nprint(1)\n")
    assert "代码围栏未闭合" in check_document(path)
