from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest


def _load_preprocess_module() -> ModuleType:
    script_path = (
        Path(__file__).resolve().parents[1] / "scripts" / "preprocess_corpus.py"
    )
    spec = importlib.util.spec_from_file_location("preprocess_corpus", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {script_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


preprocess_corpus = _load_preprocess_module()


def _write_text_pdf(path: Path, lines: list[str]) -> None:
    escaped_lines = [_escape_pdf_text(line) for line in lines]
    content_lines = ["BT", "/F1 12 Tf", "72 720 Td"]
    for index, line in enumerate(escaped_lines):
        if index:
            content_lines.append("0 -20 Td")
        content_lines.append(f"({line}) Tj")
    content_lines.append("ET")

    content = "\n".join(content_lines)
    content_bytes = content.encode("latin-1")
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            "/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(content_bytes)} >>\nstream\n{content}\nendstream",
    ]

    data = b"%PDF-1.4\n"
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(data))
        data += f"{index} 0 obj\n{body}\nendobj\n".encode("latin-1")

    xref_offset = len(data)
    data += f"xref\n0 {len(objects) + 1}\n".encode("latin-1")
    data += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        data += f"{offset:010d} 00000 n \n".encode("latin-1")
    data += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode("latin-1")

    path.write_bytes(data)


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _read_manifest(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_arbitrary_utf8_txt_to_corpus_txt(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "corpus"
    manifest = tmp_path / "manifest.jsonl"
    raw_dir.mkdir()
    (raw_dir / "notes.txt").write_text(
        "\ufeffLine one\r\n\r\n\r\nLine two.\x00\r\n",
        encoding="utf-8",
    )

    processed = preprocess_corpus.preprocess_corpus(
        raw_dir,
        output_dir,
        manifest_path=manifest,
    )

    assert [item.output_filename for item in processed] == ["notes.txt"]
    assert (output_dir / "notes.txt").read_text(encoding="utf-8") == (
        "Line one\n\nLine two.\n"
    )


def test_gb18030_txt_decoded_to_utf8(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "corpus"
    manifest = tmp_path / "manifest.jsonl"
    raw_dir.mkdir()
    (raw_dir / "gb-file.txt").write_bytes("编码测试，中文。".encode("gb18030"))

    preprocess_corpus.preprocess_corpus(raw_dir, output_dir, manifest_path=manifest)

    assert (output_dir / "gb-file.txt").read_text(
        encoding="utf-8"
    ) == "编码测试，中文。\n"
    [record] = _read_manifest(manifest)
    assert record["encoding_used"] == "gb18030"


def test_arbitrary_pdf_extracts_to_txt_with_page_metadata(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "corpus"
    manifest = tmp_path / "manifest.jsonl"
    raw_dir.mkdir()
    _write_text_pdf(
        raw_dir / "Rules Reference.pdf",
        ["1", "Ability checks use a d20.", "Advantage uses the higher roll."],
    )

    preprocess_corpus.preprocess_corpus(raw_dir, output_dir, manifest_path=manifest)

    output = output_dir / "Rules Reference.txt"
    text = output.read_text(encoding="utf-8")
    assert "[[page:1]]" in text
    assert "Ability checks use a d20." in text
    assert "Advantage uses the higher roll." in text
    assert "\n1\n" not in text

    [record] = _read_manifest(manifest)
    assert record["file_type"] == "pdf"
    assert record["extractor"] == "pypdf"
    assert record["pages"] == 1


def test_filename_with_spaces_apostrophe_and_chinese_chars_is_preserved(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "corpus"
    raw_dir.mkdir()
    filename = "Alice's 数据 set.txt"
    (raw_dir / filename).write_text("content", encoding="utf-8")

    preprocess_corpus.preprocess_corpus(raw_dir, output_dir)

    assert (output_dir / filename).read_text(encoding="utf-8") == "content\n"


def test_output_filename_collision_gets_stable_suffix(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "corpus"
    raw_dir.mkdir()
    (raw_dir / "a").mkdir()
    (raw_dir / "b").mkdir()
    (raw_dir / "a" / "report.txt").write_text("alpha", encoding="utf-8")
    (raw_dir / "b" / "report.md").write_text("beta", encoding="utf-8")

    first = preprocess_corpus.preprocess_corpus(
        raw_dir,
        output_dir,
        recursive=True,
        clean_output=True,
    )
    second = preprocess_corpus.preprocess_corpus(
        raw_dir,
        output_dir,
        recursive=True,
        clean_output=True,
    )

    first_names = sorted(item.output_filename for item in first)
    second_names = sorted(item.output_filename for item in second)
    assert first_names == second_names
    assert len(first_names) == 2
    assert all(
        name.startswith("report-") and name.endswith(".txt") for name in first_names
    )


def test_manifest_contains_core_fields(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "corpus"
    manifest = tmp_path / "manifest.jsonl"
    raw_dir.mkdir()
    (raw_dir / "dataset.md").write_text("# Title\n\nBody", encoding="utf-8")

    preprocess_corpus.preprocess_corpus(raw_dir, output_dir, manifest_path=manifest)

    [record] = _read_manifest(manifest)
    assert record["source_path"].endswith("dataset.md")
    assert record["output_path"].endswith("dataset.txt")
    assert record["original_filename"] == "dataset.md"
    assert record["output_filename"] == "dataset.txt"
    assert record["file_type"] == "md"
    assert record["sha256"]
    assert record["characters"] > 0
    assert record["lines"] > 0
    assert record["preprocessing_steps"]
    assert isinstance(record["warnings"], list)


def test_recursive_scan_ignores_hidden_and_macos_files(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "corpus"
    raw_dir.mkdir()
    (raw_dir / "visible.txt").write_text("visible", encoding="utf-8")
    (raw_dir / ".hidden.txt").write_text("hidden", encoding="utf-8")
    (raw_dir / "__MACOSX").mkdir()
    (raw_dir / "__MACOSX" / "ignored.txt").write_text("ignored", encoding="utf-8")
    (raw_dir / ".DS_Store").write_text("ignored", encoding="utf-8")

    preprocess_corpus.preprocess_corpus(raw_dir, output_dir, recursive=True)

    assert sorted(path.name for path in output_dir.glob("*.txt")) == ["visible.txt"]


def test_preprocessor_defaults_to_rag_eval_raw() -> None:
    assert preprocess_corpus.DEFAULT_RAW_DIR == Path("rag_eval/raw")


def test_missing_raw_dir_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        preprocess_corpus.preprocess_corpus(tmp_path / "missing", tmp_path / "corpus")
