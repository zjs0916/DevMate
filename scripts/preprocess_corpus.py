"""Preprocess raw txt, markdown, and PDF files into a UTF-8 RAG corpus."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import logging
import re
import shutil
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

LOGGER = logging.getLogger(__name__)

DEFAULT_RAW_DIR = Path("rag_eval/raw")
DEFAULT_OUTPUT_DIR = Path("rag_eval/corpus")
DEFAULT_MANIFEST_PATH = Path("rag_eval/corpus_manifest.jsonl")

SUPPORTED_SUFFIXES = {".txt", ".md", ".pdf"}
DEFAULT_INCLUDES = ("*.txt", "*.md", "*.pdf")
DEFAULT_EXCLUDES = (
    "__MACOSX/*",
    "*/__MACOSX/*",
    ".DS_Store",
    "*/.DS_Store",
    ".*",
    "*/.*",
)
TEXT_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "gbk", "big5")

PAGE_MARKER_TEMPLATE = "[[page:{page}]]"
PAGE_NUMBER_RE = re.compile(r"^\s*(?:page\s*)?\d+\s*$", re.IGNORECASE)
WHITESPACE_RE = re.compile(r"[ \t\f\v]+")


@dataclass(frozen=True)
class PageSpan:
    page: int
    start_line: int
    end_line: int


@dataclass(frozen=True)
class ProcessedCorpusFile:
    source_path: Path
    output_path: Path
    original_filename: str
    output_filename: str
    file_type: Literal["txt", "md", "pdf"]
    sha256: str
    characters: int
    lines: int
    preprocessing_steps: list[str]
    warnings: list[str]
    encoding_used: str | None = None
    extractor: str | None = None
    pages: int | None = None
    page_spans: list[PageSpan] | None = None

    def to_manifest_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["source_path"] = str(self.source_path)
        record["output_path"] = str(self.output_path)
        return record


@dataclass(frozen=True)
class DecodedText:
    text: str
    encoding: str
    warnings: list[str]


@dataclass(frozen=True)
class ExtractedPdf:
    pages: list[str]
    extractor: str
    warnings: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert raw txt, markdown, and PDF files into a RAG corpus.",
    )
    parser.add_argument(
        "--raw-dir",
        default=str(DEFAULT_RAW_DIR),
        help="Directory containing raw source files.",
    )
    parser.add_argument(
        "--output-dir",
        "--corpus-dir",
        dest="output_dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where generated corpus text files are written.",
    )
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST_PATH),
        help="JSONL manifest path. Use an empty string to skip manifest output.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively scan raw-dir for supported files.",
    )
    parser.add_argument(
        "--clean-output",
        action="store_true",
        help="Delete output-dir before writing the generated corpus.",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        help="Glob pattern to include, relative to raw-dir. Can be repeated.",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Glob pattern to exclude, relative to raw-dir. Can be repeated.",
    )
    return parser.parse_args()


def preprocess_corpus(
    raw_dir: str | Path = DEFAULT_RAW_DIR,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    *,
    manifest_path: str | Path | None = None,
    recursive: bool = False,
    clean_output: bool = False,
    include_patterns: list[str] | tuple[str, ...] | None = None,
    exclude_patterns: list[str] | tuple[str, ...] | None = None,
) -> list[ProcessedCorpusFile]:
    raw_path = Path(raw_dir)
    corpus_path = Path(output_dir)

    if not raw_path.exists():
        raise FileNotFoundError(f"Raw data directory does not exist: {raw_path}")
    if not raw_path.is_dir():
        raise ValueError(f"Raw data path must be a directory: {raw_path}")
    if _same_path(raw_path, corpus_path):
        raise ValueError("raw-dir and output-dir must be different directories")

    sources = discover_sources(
        raw_path,
        recursive=recursive,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
    )
    if not sources:
        raise ValueError(f"No supported raw files found in {raw_path}")

    if clean_output and corpus_path.exists():
        shutil.rmtree(corpus_path)
    corpus_path.mkdir(parents=True, exist_ok=True)

    output_names = _assign_output_names(sources)
    processed: list[ProcessedCorpusFile] = []
    for source_path in sources:
        output_path = corpus_path / output_names[source_path]
        item = _process_source(source_path, output_path)
        processed.append(item)

    if manifest_path is not None:
        write_manifest(processed, manifest_path)

    return processed


def discover_sources(
    raw_dir: Path,
    *,
    recursive: bool,
    include_patterns: list[str] | tuple[str, ...] | None = None,
    exclude_patterns: list[str] | tuple[str, ...] | None = None,
) -> list[Path]:
    includes = tuple(include_patterns or DEFAULT_INCLUDES)
    excludes = (*DEFAULT_EXCLUDES, *(exclude_patterns or ()))
    iterator = raw_dir.rglob("*") if recursive else raw_dir.glob("*")

    sources = [
        path
        for path in iterator
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_SUFFIXES
        and not _is_hidden_or_system_path(raw_dir, path)
        and _matches_patterns(raw_dir, path, includes)
        and not _matches_patterns(raw_dir, path, excludes)
    ]
    return sorted(
        sources, key=lambda path: path.relative_to(raw_dir).as_posix().lower()
    )


def write_manifest(
    processed: list[ProcessedCorpusFile],
    manifest_path: str | Path,
) -> None:
    path = Path(manifest_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    records = [item.to_manifest_record() for item in processed]
    with path.open("w", encoding="utf-8", newline="\n") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            file.write("\n")


def _process_source(source_path: Path, output_path: Path) -> ProcessedCorpusFile:
    suffix = source_path.suffix.lower()
    source_hash = _sha256_file(source_path)

    if suffix in {".txt", ".md"}:
        decoded = _read_text(source_path)
        cleaned = _clean_text(decoded.text)
        warnings = [*decoded.warnings]
        encoding_used = decoded.encoding
        extractor = None
        pages = None
        page_spans = None
        steps = [
            "decode_text",
            "strip_bom",
            "normalize_newlines",
            "remove_control_characters",
            "compress_blank_lines",
        ]
    elif suffix == ".pdf":
        extracted = _extract_pdf(source_path)
        cleaned, page_spans = _clean_pdf_pages(extracted.pages)
        warnings = [*extracted.warnings]
        encoding_used = None
        extractor = extracted.extractor
        pages = len(extracted.pages)
        steps = [
            "extract_pdf_text",
            "normalize_newlines",
            "remove_control_characters",
            "remove_page_numbers",
            "remove_repeated_edge_lines",
            "compress_blank_lines",
            "insert_page_markers",
        ]
    else:
        raise ValueError(f"Unsupported source type: {source_path}")

    output_path.write_text(cleaned, encoding="utf-8", newline="\n")
    return ProcessedCorpusFile(
        source_path=source_path,
        output_path=output_path,
        original_filename=source_path.name,
        output_filename=output_path.name,
        file_type=suffix.lstrip("."),
        encoding_used=encoding_used,
        extractor=extractor,
        sha256=source_hash,
        characters=len(cleaned),
        lines=len(cleaned.splitlines()),
        pages=pages,
        page_spans=page_spans,
        preprocessing_steps=steps,
        warnings=warnings,
    )


def _assign_output_names(sources: list[Path]) -> dict[Path, str]:
    base_names: dict[str, list[Path]] = {}
    for source_path in sources:
        base_names.setdefault(f"{source_path.stem}.txt", []).append(source_path)

    output_names: dict[Path, str] = {}
    used: set[str] = set()
    for source_path in sources:
        candidate = f"{source_path.stem}.txt"
        if len(base_names[candidate]) > 1 or candidate in used:
            digest = _short_path_hash(source_path)
            candidate = f"{source_path.stem}-{digest}.txt"
        while candidate in used:
            digest = _short_path_hash(Path(f"{source_path.as_posix()}:{candidate}"))
            candidate = f"{source_path.stem}-{digest}.txt"
        output_names[source_path] = candidate
        used.add(candidate)

    return output_names


def _read_text(path: Path) -> DecodedText:
    data = path.read_bytes()
    warnings: list[str] = []
    last_error: UnicodeDecodeError | None = None

    for encoding in TEXT_ENCODINGS:
        try:
            return DecodedText(data.decode(encoding), encoding, warnings)
        except UnicodeDecodeError as exc:
            last_error = exc

    warnings.append("decoded_with_replacement")
    if last_error:
        LOGGER.warning("Decoding %s with replacement after %s", path, last_error)
    return DecodedText(
        data.decode("utf-8", errors="replace"), "utf-8-replace", warnings
    )


def _extract_pdf(path: Path) -> ExtractedPdf:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError(
            "PDF preprocessing requires the pypdf dependency. Run `uv sync` first."
        ) from exc

    reader = PdfReader(str(path))
    pages: list[str] = []
    warnings: list[str] = []
    for page_number, page in enumerate(reader.pages, start=1):
        try:
            pages.append(page.extract_text() or "")
        except Exception as exc:  # pragma: no cover - depends on malformed PDFs.
            pages.append("")
            warnings.append(f"page_{page_number}_extract_failed:{type(exc).__name__}")

    if not any(page.strip() for page in pages):
        raise ValueError(f"No extractable text found in PDF: {path}")

    return ExtractedPdf(pages=pages, extractor="pypdf", warnings=warnings)


def _clean_text(text: str) -> str:
    text = text.lstrip("\ufeff")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _remove_control_characters(text)
    text = _compress_blank_lines(text)
    if text and not text.endswith("\n"):
        text += "\n"
    return text


def _clean_pdf_pages(pages: list[str]) -> tuple[str, list[PageSpan]]:
    normalized_pages = [_normalise_pdf_page(page) for page in pages]
    repeated_edge_lines = _find_repeated_edge_lines(normalized_pages)

    output_lines: list[str] = []
    page_spans: list[PageSpan] = []
    for page_number, page_text in enumerate(normalized_pages, start=1):
        kept_lines = [
            line
            for line in page_text.splitlines()
            if line
            and not PAGE_NUMBER_RE.match(line)
            and line.casefold() not in repeated_edge_lines
        ]
        if not kept_lines:
            continue

        if output_lines:
            output_lines.append("")
        output_lines.append(PAGE_MARKER_TEMPLATE.format(page=page_number))
        start_line = len(output_lines) + 1
        output_lines.extend(kept_lines)
        end_line = len(output_lines)
        page_spans.append(
            PageSpan(
                page=page_number,
                start_line=start_line,
                end_line=end_line,
            )
        )

    text = _clean_text("\n".join(output_lines))
    return text, page_spans


def _normalise_pdf_page(text: str) -> str:
    text = _clean_text(text)
    lines = [WHITESPACE_RE.sub(" ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _find_repeated_edge_lines(pages: list[str]) -> set[str]:
    counter: Counter[str] = Counter()
    for page in pages:
        lines = [line.strip() for line in page.splitlines() if line.strip()]
        edge_lines = {line.casefold() for line in [*lines[:2], *lines[-2:]]}
        counter.update(edge_lines)

    threshold = max(2, len(pages) // 3)
    return {
        line for line, count in counter.items() if count >= threshold and len(line) > 3
    }


def _compress_blank_lines(text: str) -> str:
    output_lines: list[str] = []
    previous_blank = False

    for line in text.split("\n"):
        if line.strip():
            output_lines.append(line.rstrip())
            previous_blank = False
            continue

        if output_lines and not previous_blank:
            output_lines.append("")
        previous_blank = True

    while output_lines and output_lines[-1] == "":
        output_lines.pop()

    return "\n".join(output_lines)


def _remove_control_characters(text: str) -> str:
    kept: list[str] = []
    for char in text:
        if char in {"\n", "\t"}:
            kept.append(char)
            continue
        if char == "\ufeff":
            continue
        category = unicodedata.category(char)
        if category in {"Cc", "Cf"}:
            continue
        kept.append(char)
    return "".join(kept)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _short_path_hash(path: Path) -> str:
    return hashlib.sha256(path.as_posix().encode("utf-8")).hexdigest()[:8]


def _matches_patterns(
    raw_dir: Path,
    path: Path,
    patterns: tuple[str, ...] | list[str],
) -> bool:
    relative = path.relative_to(raw_dir).as_posix()
    return any(
        fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(path.name, pattern)
        for pattern in patterns
    )


def _is_hidden_or_system_path(raw_dir: Path, path: Path) -> bool:
    relative_parts = path.relative_to(raw_dir).parts
    return any(
        part == "__MACOSX"
        or part == ".DS_Store"
        or part.startswith(".")
        or part.startswith("._")
        for part in relative_parts
    )


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except FileNotFoundError:
        return left.absolute() == right.absolute()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    args = parse_args()
    manifest = Path(args.manifest) if args.manifest else None

    try:
        processed = preprocess_corpus(
            raw_dir=args.raw_dir,
            output_dir=args.output_dir,
            manifest_path=manifest,
            recursive=args.recursive,
            clean_output=args.clean_output,
            include_patterns=args.include or None,
            exclude_patterns=args.exclude or None,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        LOGGER.error("%s", exc)
        raise SystemExit(1) from exc

    for item in processed:
        LOGGER.info(
            "processed %s -> %s (%s chars, %s lines)",
            item.source_path,
            item.output_path,
            item.characters,
            item.lines,
        )
    if manifest is not None:
        LOGGER.info("manifest: %s", manifest)


if __name__ == "__main__":
    main()
