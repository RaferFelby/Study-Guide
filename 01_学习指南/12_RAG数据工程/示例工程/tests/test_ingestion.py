from pathlib import Path

import pytest

from ingestion import parse_source

FIXTURES = Path(__file__).parents[1] / "fixtures"


def test_parse_markdown_keeps_paragraph_locations() -> None:
    sections = parse_source(FIXTURES / "compute.md")

    assert sections[0].locator == "段落 1"
    assert "GPU 显存" in sections[0].text
    assert len(sections) == 4


def test_parse_html_skips_navigation_script_and_footer() -> None:
    sections = parse_source(FIXTURES / "webpage.html")
    text = " ".join(section.text for section in sections)

    assert "设备维护" in text
    assert "每月检查" in text
    assert "导航菜单" not in text
    assert "ignore_this_script" not in text
    assert "页脚" not in text


def test_parse_csv_keeps_row_number_and_headers() -> None:
    sections = parse_source(FIXTURES / "permissions.csv")

    assert sections[0].locator == "CSV 第 2 行"
    assert "公司报销" in sections[0].text
    assert sections[0].permission == "staff"


def test_unsupported_file_has_actionable_error() -> None:
    source = Path(__file__).with_suffix(".pdf")

    with pytest.raises(ValueError, match="暂不支持"):
        parse_source(source)
