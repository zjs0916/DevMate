from __future__ import annotations

import pytest

from devmate.rag import split_text


def test_short_text_returns_single_chunk() -> None:
    chunks = split_text("A short paragraph.")

    assert chunks == ["A short paragraph."]


def test_markdown_headers_and_paragraphs_split_into_units() -> None:
    text = (
        "# Title\n\n"
        "First paragraph here.\n\n"
        "## Section\n\n"
        "Second paragraph here."
    )

    chunks = split_text(text, chunk_size=25, overlap=5)

    # With a small chunk size each header/paragraph unit stays separate.
    assert len(chunks) >= 3
    assert any("# Title" in chunk for chunk in chunks)
    assert any("## Section" in chunk for chunk in chunks)


def test_long_text_is_split_into_multiple_bounded_chunks() -> None:
    long_text = "\n\n".join(
        f"Paragraph {i} " + ("word " * 60) for i in range(10)
    )

    chunks = split_text(long_text, chunk_size=300, overlap=40)

    assert len(chunks) > 1
    for chunk in chunks:
        # Oversized single units may exceed slightly, but bounded chunks
        # should not be wildly over the limit.
        assert len(chunk) <= 300 + 60


def test_oversized_single_paragraph_is_char_split() -> None:
    blob = "x" * 5000  # one giant token-free unit, no sentence breaks

    chunks = split_text(blob, chunk_size=900, overlap=120)

    assert len(chunks) > 1
    assert all(len(chunk) <= 900 for chunk in chunks)


def test_chunk_size_must_exceed_overlap() -> None:
    with pytest.raises(ValueError, match="chunk_size"):
        split_text("text", chunk_size=100, overlap=100)
