import pytest

from chunking import fixed_length_chunks, structure_chunks
from ingestion import SourceSection


def test_fixed_length_chunks_have_requested_overlap() -> None:
    sections = [SourceSection("abcdefghij", "段落 1")]

    chunks = fixed_length_chunks(sections, chunk_size=6, overlap=2)

    assert [chunk.text for chunk in chunks] == ["abcdef", "efghij"]


@pytest.mark.parametrize(("chunk_size", "overlap"), [(0, 0), (4, -1), (4, 4)])
def test_fixed_length_chunks_reject_invalid_boundaries(
    chunk_size: int, overlap: int
) -> None:
    with pytest.raises(ValueError):
        fixed_length_chunks([SourceSection("text", "段落 1")], chunk_size, overlap)


def test_structure_chunks_keep_source_locator() -> None:
    sections = [
        SourceSection("第一行", "CSV 第 2 行"),
        SourceSection("第二行", "CSV 第 3 行"),
    ]

    chunks = structure_chunks(sections)

    assert [chunk.locator for chunk in chunks] == ["CSV 第 2 行", "CSV 第 3 行"]
