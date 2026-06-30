from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_SPECIFIC_TOKENS = (
    "凡人修仙传",
    "Player's Handbook",
    "fanren",
    "players_handbook",
    "玩家手册",
)
FIXED_RETRIEVAL_DEFAULTS = (
    "DEFAULT_QUESTIONS",
    "DEFAULT_FANREN_SOURCE",
    "PLAYER_HANDBOOK_SOURCE",
)


def _load_preprocess_module() -> ModuleType:
    script_path = PROJECT_ROOT / "scripts" / "preprocess_corpus.py"
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


def test_preprocess_script_has_no_dataset_specific_tokens() -> None:
    script = (PROJECT_ROOT / "scripts" / "preprocess_corpus.py").read_text(
        encoding="utf-8"
    )

    for token in DATASET_SPECIFIC_TOKENS:
        assert token not in script


def test_retrieval_script_depends_on_external_eval_cases() -> None:
    script = (PROJECT_ROOT / "scripts" / "test_rag_retrieval.py").read_text(
        encoding="utf-8"
    )

    for token in FIXED_RETRIEVAL_DEFAULTS:
        assert token not in script
    assert "DEFAULT_EVAL_CASES" in script
    assert "--eval-cases" in script


def test_preprocess_supports_arbitrary_txt_chinese_txt_and_pdf_names(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "corpus"
    raw_dir.mkdir()
    (raw_dir / "field notes.txt").write_text("alpha\n", encoding="utf-8")
    (raw_dir / "领域资料.txt").write_text("中文内容\n", encoding="utf-8")
    _write_text_pdf(raw_dir / "Reference Guide.pdf", ["General PDF content."])

    processed = preprocess_corpus.preprocess_corpus(raw_dir, output_dir)
    output_names = sorted(item.output_filename for item in processed)

    assert output_names == [
        "Reference Guide.txt",
        "field notes.txt",
        "领域资料.txt",
    ]
    assert (output_dir / "field notes.txt").read_text(encoding="utf-8") == "alpha\n"
    assert (output_dir / "领域资料.txt").read_text(encoding="utf-8") == "中文内容\n"
    assert "General PDF content." in (output_dir / "Reference Guide.txt").read_text(
        encoding="utf-8"
    )


def test_preprocess_filename_collisions_get_stable_hash_suffix(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "corpus"
    (raw_dir / "a").mkdir(parents=True)
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
    assert all(re.fullmatch(r"report-[0-9a-f]{8}\.txt", name) for name in first_names)
