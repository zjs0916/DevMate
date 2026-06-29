from __future__ import annotations

import json
from pathlib import Path

import pytest

from devmate.rag import load_local_documents, split_text


def test_short_text_returns_single_chunk() -> None:
    chunks = split_text("A short paragraph.")

    assert chunks == ["A short paragraph."]


def test_markdown_headers_and_paragraphs_split_into_units() -> None:
    text = "# Title\n\nFirst paragraph here.\n\n## Section\n\nSecond paragraph here."

    chunks = split_text(text, chunk_size=25, overlap=5)

    # With a small chunk size each header/paragraph unit stays separate.
    assert len(chunks) >= 3
    assert any("# Title" in chunk for chunk in chunks)
    assert any("## Section" in chunk for chunk in chunks)


def test_long_text_is_split_into_multiple_bounded_chunks() -> None:
    long_text = "\n\n".join(f"Paragraph {i} " + ("word " * 60) for i in range(10))

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


def test_load_local_documents_adds_stable_chunk_metadata(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.txt").write_text("A paragraph about indexing.", encoding="utf-8")

    [document] = load_local_documents(docs_dir, chunk_size=200, chunk_overlap=20)

    metadata = document.metadata
    assert metadata["source"].endswith("guide.txt")
    assert metadata["source_name"] == "guide.txt"
    assert metadata["source_suffix"] == ".txt"
    assert metadata["chunk_index"] == 0
    assert metadata["chunk_id"]
    assert metadata["content_sha256"]


def test_load_local_documents_adds_pdf_page_metadata_from_manifest(
    tmp_path: Path,
) -> None:
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    (corpus_dir / "manual.txt").write_text(
        "[[page:2]]\nPage two text.",
        encoding="utf-8",
    )
    manifest = tmp_path / "corpus_manifest.jsonl"
    manifest.write_text(
        json.dumps(
            {
                "output_filename": "manual.txt",
                "output_path": str(corpus_dir / "manual.txt"),
                "original_filename": "manual.pdf",
                "file_type": "pdf",
                "pages": 3,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    [document] = load_local_documents(
        corpus_dir,
        chunk_size=200,
        chunk_overlap=20,
        manifest_path=manifest,
    )

    assert document.metadata["file_type"] == "pdf"
    assert document.metadata["original_filename"] == "manual.pdf"
    assert document.metadata["page_start"] == 2
    assert document.metadata["page_end"] == 2
