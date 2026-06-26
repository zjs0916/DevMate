"""Preprocess original RAG evaluation files into the generated corpus.

The preprocessing layer intentionally does only deterministic hygiene:

* decode source text into UTF-8,
* remove a leading BOM,
* normalize newlines,
* compress excessive blank lines,
* extract Player's Handbook PDF text,
* remove simple Player Handbook page headers / page numbers.

It does not translate, summarize, rewrite, manually rename, or manually copy
source files. Output filenames are derived from the original source identity:
Chinese TXT files keep their original filename, while PDF files keep their title
and only change the extension to ``.txt``.
"""

from __future__ import annotations

import argparse
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

LOGGER = logging.getLogger(__name__)

DEFAULT_RAW_DIR = Path("rag_eval/raw")
DEFAULT_OUTPUT_DIR = Path("rag_eval/corpus")

_TEXT_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "gbk", "big5")

_PAGE_NUMBER_RE = re.compile(r"^\s*(?:page\s*)?\d+\s*$", re.IGNORECASE)
_PLAYER_HEADER_RE = re.compile(
    r"^\s*(?:"
    r"player'?s?\s+handbook|"
    r"dungeons\s*(?:&|and)?\s*dragons(?:\s+player'?s?\s+handbook)?"
    r")\s*$",
    re.IGNORECASE,
)
_PLAYER_FOOTER_RE = re.compile(r"^\s*dungeonsanddragons\.com\s*$", re.IGNORECASE)
_FANREN_FILENAME_HINT = "凡人修仙传"
_PLAYER_HANDBOOK_TOKEN = "playershandbook"


@dataclass(frozen=True)
class CorpusSource:
    """A selected raw source and its generated corpus filename."""

    name: str
    source_path: Path
    output_filename: str
    kind: Literal["text", "pdf"]


@dataclass(frozen=True)
class ProcessedCorpusFile:
    """A generated corpus file."""

    name: str
    source_path: Path
    output_path: Path
    characters: int
    lines: int
    preview: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert original RAG data into the generated corpus directory.",
    )
    parser.add_argument(
        "--raw-dir",
        default=str(DEFAULT_RAW_DIR),
        help="Directory containing original source files.",
    )
    parser.add_argument(
        "--output-dir",
        "--corpus-dir",
        dest="output_dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where generated RAG corpus files are written.",
    )
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="Do not delete existing .txt files in the output directory first.",
    )
    parser.add_argument(
        "--fanren-input",
        default=None,
        help="Explicit path to the 凡人修仙传 raw .txt file.",
    )
    parser.add_argument(
        "--phb-input",
        default=None,
        help="Explicit path to the Player's Handbook raw .pdf file.",
    )
    return parser.parse_args()


def preprocess_corpus(
    raw_dir: str | Path = DEFAULT_RAW_DIR,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    *,
    clean_output: bool = True,
    fanren_input: str | Path | None = None,
    phb_input: str | Path | None = None,
) -> list[ProcessedCorpusFile]:
    """Generate the RAG corpus from original inputs."""

    raw_path = Path(raw_dir)
    corpus_path = Path(output_dir)

    explicit_inputs_provided = fanren_input is not None and phb_input is not None
    if not raw_path.exists() and not explicit_inputs_provided:
        raise FileNotFoundError(f"Raw data directory does not exist: {raw_path}")

    if raw_path.resolve() == corpus_path.resolve():
        raise ValueError("raw-dir and output-dir must be different directories")

    sources = [
        _select_chinese_source(raw_path, fanren_input),
        _select_player_handbook_source(raw_path, phb_input),
    ]

    corpus_path.mkdir(parents=True, exist_ok=True)
    if clean_output:
        _remove_existing_corpus_texts(corpus_path)

    processed: list[ProcessedCorpusFile] = []
    for source in sources:
        cleaned = _read_and_clean_source(source)
        output_path = corpus_path / source.output_filename
        output_path.write_text(cleaned, encoding="utf-8", newline="\n")
        processed.append(
            ProcessedCorpusFile(
                name=source.name,
                source_path=source.source_path,
                output_path=output_path,
                characters=len(cleaned),
                lines=len(cleaned.splitlines()),
                preview=_preview(cleaned),
            ),
        )

    return processed


def _remove_existing_corpus_texts(corpus_dir: Path) -> None:
    for path in corpus_dir.glob("*.txt"):
        if path.is_file():
            path.unlink()


def _select_chinese_source(
    raw_dir: Path,
    explicit_input: str | Path | None = None,
) -> CorpusSource:
    if explicit_input is not None:
        source_path = _resolve_explicit_input(explicit_input, raw_dir, ".txt")
        return CorpusSource(
            name="fanren",
            source_path=source_path,
            output_filename=source_path.name,
            kind="text",
        )

    candidates = [
        path for path in _iter_raw_files(raw_dir, ".txt") if _is_chinese_source(path)
    ]
    if not candidates:
        raise FileNotFoundError(
            "No 凡人修仙传 raw txt found. Expected a .txt filename containing "
            "凡人修仙传. "
            "Use --fanren-input to specify the source explicitly."
        )
    if len(candidates) > 1:
        names = ", ".join(path.as_posix() for path in candidates)
        raise ValueError(
            "Multiple Chinese raw txt candidates found. Use --fanren-input to "
            f"specify one explicitly: {names}"
        )

    source_path = candidates[0]
    return CorpusSource(
        name="fanren",
        source_path=source_path,
        output_filename=source_path.name,
        kind="text",
    )


def _select_player_handbook_source(
    raw_dir: Path,
    explicit_input: str | Path | None = None,
) -> CorpusSource:
    if explicit_input is not None:
        source_path = _resolve_explicit_input(explicit_input, raw_dir, ".pdf")
        return CorpusSource(
            name="player_handbook",
            source_path=source_path,
            output_filename=source_path.with_suffix(".txt").name,
            kind="pdf",
        )

    pdf_candidates = [
        path for path in _iter_raw_files(raw_dir, ".pdf") if _is_player_handbook_source(path)
    ]
    if not pdf_candidates:
        raise FileNotFoundError(
            "No Player's Handbook PDF found. Expected a .pdf filename containing "
            "Player's Handbook. Use --phb-input to specify the source explicitly."
        )
    if len(pdf_candidates) > 1:
        names = ", ".join(path.as_posix() for path in pdf_candidates)
        raise ValueError(
            "Multiple Player's Handbook PDF candidates found. Use --phb-input to "
            f"specify one explicitly: {names}"
        )

    source_path = pdf_candidates[0]
    return CorpusSource(
        name="player_handbook",
        source_path=source_path,
        output_filename=source_path.with_suffix(".txt").name,
        kind="pdf",
    )


def _resolve_explicit_input(input_path: str | Path, raw_dir: Path, suffix: str) -> Path:
    path = Path(input_path)
    if not path.is_absolute() and not path.exists():
        path = raw_dir / path

    if not path.exists():
        raise FileNotFoundError(f"Explicit input does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"Explicit input must be a file: {path}")
    if path.suffix.lower() != suffix:
        raise ValueError(f"Explicit input must be a {suffix} file: {path}")

    return path


def _iter_raw_files(raw_dir: Path, suffix: str) -> list[Path]:
    return sorted(
        (
            path
            for path in raw_dir.iterdir()
            if path.is_file()
            and path.suffix.lower() == suffix
            and not _is_ignored_raw_path(path)
        ),
        key=lambda path: path.as_posix().lower(),
    )


def _is_ignored_raw_path(path: Path) -> bool:
    return path.name.startswith("._") or "__MACOSX" in path.parts


def _is_chinese_source(path: Path) -> bool:
    return _FANREN_FILENAME_HINT in path.stem


def _is_player_handbook_source(path: Path) -> bool:
    token = _filename_token(path)
    return _PLAYER_HANDBOOK_TOKEN in token


def _filename_token(path: Path) -> str:
    return re.sub(r"[^a-z0-9]+", "", path.stem.lower())


def _read_and_clean_source(source: CorpusSource) -> str:
    if source.kind == "text":
        return _clean_text(_read_text(source.source_path))

    if source.kind == "pdf":
        return _clean_player_handbook_pdf_text(_extract_pdf_text(source.source_path))

    raise ValueError(f"Unsupported source type: {source.kind}")


def _read_text(path: Path) -> str:
    data = path.read_bytes()
    last_error: UnicodeDecodeError | None = None

    for encoding in _TEXT_ENCODINGS:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError as exc:
            last_error = exc

    raise UnicodeDecodeError(
        last_error.encoding if last_error else "unknown",
        data,
        last_error.start if last_error else 0,
        last_error.end if last_error else 1,
        f"Unable to decode text file: {path}",
    )


def _extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError(
            "PDF preprocessing requires the pypdf dependency. "
            "Run `uv sync` before preprocessing."
        ) from exc

    reader = PdfReader(str(path))
    pages: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            pages.append(page_text.strip())

    extracted = "\n\n".join(pages)
    if not extracted.strip():
        raise ValueError(f"No extractable text found in PDF: {path}")

    return extracted


def _clean_text(text: str) -> str:
    text = text.lstrip("\ufeff")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _compress_blank_lines(text)
    if text and not text.endswith("\n"):
        text += "\n"
    return text


def _compress_blank_lines(text: str) -> str:
    output_lines: list[str] = []
    previous_blank = False

    for line in text.split("\n"):
        if line.strip():
            output_lines.append(line)
            previous_blank = False
            continue

        if output_lines and not previous_blank:
            output_lines.append("")
        previous_blank = True

    while output_lines and output_lines[-1] == "":
        output_lines.pop()

    return "\n".join(output_lines)


def _clean_player_handbook_pdf_text(text: str) -> str:
    text = text.replace("\u00a0", " ").replace("\t", " ")
    text = _clean_text(text)

    kept_lines: list[str] = []
    for line in text.split("\n"):
        normalized = re.sub(r"\s+", " ", line).strip()

        if not normalized:
            kept_lines.append("")
            continue

        if _PAGE_NUMBER_RE.match(normalized) or _PLAYER_FOOTER_RE.match(normalized):
            continue

        if _PLAYER_HEADER_RE.match(normalized):
            continue

        kept_lines.append(normalized)

    return _clean_text("\n".join(kept_lines))


def _preview(text: str, chars: int = 200) -> str:
    return " ".join(text.split())[:chars]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    args = parse_args()
    try:
        processed = preprocess_corpus(
            raw_dir=args.raw_dir,
            output_dir=args.output_dir,
            clean_output=not args.keep_existing,
            fanren_input=args.fanren_input,
            phb_input=args.phb_input,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        LOGGER.error("%s", exc)
        raise SystemExit(1) from exc

    for item in processed:
        LOGGER.info("input path: %s", item.source_path)
        LOGGER.info("output path: %s", item.output_path)
        LOGGER.info("character count: %s", item.characters)
        LOGGER.info("line count: %s", item.lines)
        LOGGER.info("preview: %s", item.preview)


if __name__ == "__main__":
    main()
