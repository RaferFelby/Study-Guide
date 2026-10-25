"""Parse small text, Markdown, HTML, and CSV sources into traceable sections."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path


@dataclass(frozen=True)
class SourceSection:
    """One cleaned source passage and its human-readable locator."""

    text: str
    locator: str
    permission: str | None = None


class _HTMLTextParser(HTMLParser):
    """Collect visible HTML text while skipping non-content elements."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "nav", "footer"}:
            self.ignored_depth += 1
        elif tag in {"p", "h1", "h2", "h3", "li", "tr", "br"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "nav", "footer"}:
            self.ignored_depth = max(0, self.ignored_depth - 1)
        elif tag in {"p", "h1", "h2", "h3", "li", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.ignored_depth == 0:
            self.parts.append(data)


def clean_text(text: str) -> str:
    """Normalize whitespace without deleting punctuation or source meaning."""
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def parse_source(path: Path) -> list[SourceSection]:
    """Parse a supported file into sections with page/paragraph/row locators."""
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        text = path.read_text(encoding="utf-8")
        paragraphs = [clean_text(value) for value in re.split(r"\n\s*\n", text)]
        return [
            SourceSection(text=value, locator=f"段落 {index}")
            for index, value in enumerate(paragraphs, start=1)
            if value
        ]

    if suffix in {".html", ".htm"}:
        parser = _HTMLTextParser()
        parser.feed(path.read_text(encoding="utf-8"))
        parser.close()
        lines = [clean_text(value) for value in "".join(parser.parts).splitlines()]
        return [
            SourceSection(text=value, locator=f"网页段落 {index}")
            for index, value in enumerate((line for line in lines if line), start=1)
        ]

    if suffix == ".csv":
        sections = []
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            if not reader.fieldnames:
                raise ValueError(f"CSV 缺少表头：{path}")
            for row_number, row in enumerate(reader, start=2):
                permission = row.get("permission") or None
                cells = [
                    f"{key}：{value.strip()}"
                    for key, value in row.items()
                    if key != "permission" and key and value and value.strip()
                ]
                if cells:
                    sections.append(
                        SourceSection(
                            "；".join(cells), f"CSV 第 {row_number} 行", permission
                        )
                    )
        return sections

    raise ValueError(f"暂不支持的文件类型：{suffix or '无扩展名'}")
