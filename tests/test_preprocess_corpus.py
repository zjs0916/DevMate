from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest


CHINESE_SOURCE_FILENAME = "《凡人修仙传》（精校全本）作者：忘语....txt"
PLAYER_SOURCE_FILENAME = "Player's Handbook.pdf"


def _load_preprocess_module() -> ModuleType:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "preprocess_corpus.py"
    spec = importlib.util.spec_from_file_location("preprocess_corpus", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {script_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


preprocess_corpus = _load_preprocess_module()


def _write_required_raw_files(raw_dir: Path) -> None:
    raw_dir.mkdir(parents=True)
    (raw_dir / CHINESE_SOURCE_FILENAME).write_bytes(
        "\ufeff第一章\r\n\r\n\r\n韩立没有改名。\r\n第二段。\r\n".encode("utf-8"),
    )
    _write_text_pdf(
        raw_dir / PLAYER_SOURCE_FILENAME,
        [
            "Player's Handbook",
            "13",
            "Ability checks use a d20.",
            "DUNGEONSANDDRAGONS.COM",
            "Advantage means roll two d20s and use the higher roll.",
        ],
    )


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


def test_chinese_file_preserves_original_filename_and_normalizes_text(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "rag_eval" / "raw"
    output_dir = tmp_path / "corpus"
    _write_required_raw_files(raw_dir)

    processed = preprocess_corpus.preprocess_corpus(raw_dir, output_dir)

    output = output_dir / CHINESE_SOURCE_FILENAME
    assert output in {item.output_path for item in processed}
    text = output.read_text(encoding="utf-8")
    assert not text.startswith("\ufeff")
    assert "\r" not in text
    assert "\n\n\n" not in text
    assert "韩立没有改名。\n第二段。" in text


def test_player_handbook_pdf_is_extracted_to_title_txt(tmp_path: Path) -> None:
    raw_dir = tmp_path / "rag_eval" / "raw"
    output_dir = tmp_path / "corpus"
    _write_required_raw_files(raw_dir)

    preprocess_corpus.preprocess_corpus(raw_dir, output_dir)

    output = output_dir / "Player's Handbook.txt"
    text = output.read_text(encoding="utf-8")
    assert output.exists()
    assert "Ability checks use a d20." in text
    assert "Advantage means roll two d20s and use the higher roll." in text
    assert "\n13\n" not in text
    assert "DUNGEONSANDDRAGONS.COM" not in text


def test_preprocessor_does_not_emit_legacy_normalized_names(tmp_path: Path) -> None:
    raw_dir = tmp_path / "rag_eval" / "raw"
    output_dir = tmp_path / "corpus"
    _write_required_raw_files(raw_dir)
    output_dir.mkdir()
    (output_dir / "fanren.txt").write_text("stale", encoding="utf-8")
    (output_dir / "fanren_original_gb18030.txt").write_text("stale", encoding="utf-8")
    (output_dir / "players_handbook.txt").write_text("stale", encoding="utf-8")
    (output_dir / "玩家手册.txt").write_text("stale", encoding="utf-8")

    preprocess_corpus.preprocess_corpus(raw_dir, output_dir)

    assert sorted(path.name for path in output_dir.glob("*.txt")) == [
        "Player's Handbook.txt",
        CHINESE_SOURCE_FILENAME,
    ]


def test_preprocessing_preserves_source_content_words(tmp_path: Path) -> None:
    raw_dir = tmp_path / "rag_eval" / "raw"
    output_dir = tmp_path / "corpus"
    raw_dir.mkdir(parents=True)
    original_chinese = "韩立说道：小绿瓶没有变化。"
    original_english = "A proficiency bonus starts at +2 for a 1st-level character."
    (raw_dir / CHINESE_SOURCE_FILENAME).write_text(original_chinese, encoding="utf-8")
    _write_text_pdf(raw_dir / PLAYER_SOURCE_FILENAME, [original_english])

    preprocess_corpus.preprocess_corpus(raw_dir, output_dir)

    assert (
        output_dir / CHINESE_SOURCE_FILENAME
    ).read_text(encoding="utf-8") == f"{original_chinese}\n"
    assert original_english in (output_dir / "Player's Handbook.txt").read_text(
        encoding="utf-8",
    )


def test_preprocessor_defaults_to_rag_eval_raw() -> None:
    assert preprocess_corpus.DEFAULT_RAW_DIR == Path("rag_eval/raw")


def test_explicit_inputs_do_not_require_default_raw_dir(tmp_path: Path) -> None:
    raw_dir = tmp_path / "missing-raw-dir"
    output_dir = tmp_path / "corpus"
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    fanren_input = source_dir / CHINESE_SOURCE_FILENAME
    phb_input = source_dir / PLAYER_SOURCE_FILENAME
    fanren_input.write_text(
        "韩立在七玄门修行。",
        encoding="utf-8",
    )
    _write_text_pdf(
        phb_input,
        ["A proficiency bonus starts at +2."],
    )

    preprocess_corpus.preprocess_corpus(
        raw_dir,
        output_dir,
        fanren_input=fanren_input,
        phb_input=phb_input,
    )

    assert (output_dir / CHINESE_SOURCE_FILENAME).exists()
    assert (output_dir / "Player's Handbook.txt").exists()


def test_multiple_chinese_candidates_require_explicit_input(tmp_path: Path) -> None:
    raw_dir = tmp_path / "rag_eval" / "raw"
    raw_dir.mkdir(parents=True)
    (raw_dir / "凡人修仙传-one.txt").write_text("第一份", encoding="utf-8")
    (raw_dir / "凡人修仙传-two.txt").write_text("第二份", encoding="utf-8")

    with pytest.raises(ValueError, match="--fanren-input"):
        preprocess_corpus.preprocess_corpus(raw_dir, tmp_path / "corpus")


def test_multiple_player_handbook_candidates_require_explicit_input(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "rag_eval" / "raw"
    raw_dir.mkdir(parents=True)
    (raw_dir / CHINESE_SOURCE_FILENAME).write_text("韩立", encoding="utf-8")
    _write_text_pdf(raw_dir / PLAYER_SOURCE_FILENAME, ["first"])
    _write_text_pdf(raw_dir / "Annotated Player's Handbook.pdf", ["second"])

    with pytest.raises(ValueError, match="--phb-input"):
        preprocess_corpus.preprocess_corpus(raw_dir, tmp_path / "corpus")


def test_explicit_inputs_override_ambiguous_detection(tmp_path: Path) -> None:
    raw_dir = tmp_path / "rag_eval" / "raw"
    output_dir = tmp_path / "corpus"
    raw_dir.mkdir(parents=True)
    ignored_chinese = raw_dir / "凡人修仙传-one.txt"
    chosen_chinese = raw_dir / "凡人修仙传-two.txt"
    ignored_chinese.write_text("不应选择", encoding="utf-8")
    chosen_chinese.write_text("韩立应被选择", encoding="utf-8")
    ignored_pdf = raw_dir / PLAYER_SOURCE_FILENAME
    chosen_pdf = raw_dir / "Annotated Player's Handbook.pdf"
    _write_text_pdf(ignored_pdf, ["ignored"])
    _write_text_pdf(chosen_pdf, ["chosen"])

    preprocess_corpus.preprocess_corpus(
        raw_dir,
        output_dir,
        fanren_input=chosen_chinese,
        phb_input=chosen_pdf,
    )

    assert (output_dir / chosen_chinese.name).read_text(encoding="utf-8") == (
        "韩立应被选择\n"
    )
    assert "chosen" in (output_dir / "Annotated Player's Handbook.txt").read_text(
        encoding="utf-8",
    )
    assert not (output_dir / ignored_chinese.name).exists()
    assert not (output_dir / "Player's Handbook.txt").exists()
