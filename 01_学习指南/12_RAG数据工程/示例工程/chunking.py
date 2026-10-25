"""Create fixed-window or source-structure-preserving chunks."""

from __future__ import annotations

from dataclasses import dataclass

from ingestion import SourceSection


@dataclass(frozen=True)
class Chunk:
    text: str
    locator: str
    chunk_index: int
    permission: str | None = None


def fixed_length_chunks(
    sections: list[SourceSection], chunk_size: int, overlap: int
) -> list[Chunk]:
    """Split joined source text into character windows with a small overlap."""
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap 必须大于等于 0 且小于 chunk_size")

    chunks = []
    for section in sections:
        start = 0
        while start < len(section.text):
            end = min(start + chunk_size, len(section.text))
            locator = f"{section.locator} 字符 {start}–{end}"
            chunks.append(
                Chunk(section.text[start:end], locator, len(chunks), section.permission)
            )
            if end == len(section.text):
                break
            start = end - overlap
    return chunks


def structure_chunks(sections: list[SourceSection]) -> list[Chunk]:
    """Keep each parsed paragraph, HTML block, or CSV row together."""
    return [
        Chunk(section.text, section.locator, index, section.permission)
        for index, section in enumerate(sections)
        if section.text.strip()
    ]
