from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document

from devmate.config import AppConfig
from devmate.model import create_embedding_model
from devmate.vectorstore_metadata import (
    validate_embedding_signature,
    write_embedding_signature,
)

COLLECTION_NAME = "devmate_docs"
SUPPORTED_SUFFIXES = {".md", ".txt"}
DEFAULT_CHUNK_SIZE = 900
DEFAULT_CHUNK_OVERLAP = 120

# Insert embeddings in batches so a single request never has to handle the
# whole corpus at once. Some embedding backends (e.g. Ollama) crash or time
# out on one huge batch; FastEmbed produces identical vectors either way.
EMBED_BATCH_SIZE = 256

_HEADER_RE = re.compile(r"(?=^#{1,6}\s)", re.MULTILINE)
_SENTENCE_RE = re.compile(r"[^.!?。！？]+[.!?。！？]?")
_PAGE_MARKER_RE = re.compile(r"^\[\[page:(?P<page>\d+)]]$", re.MULTILINE)


def split_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
    *,
    is_markdown: bool | None = None,
) -> list[str]:
    if chunk_size <= overlap:
        message = "chunk_size must be greater than overlap."
        raise ValueError(message)

    markdown = bool(_HEADER_RE.search(text)) if is_markdown is None else is_markdown
    units = _split_into_units(text, is_markdown=markdown)
    return _merge_into_chunks(units, chunk_size, overlap)


def _split_into_units(text: str, *, is_markdown: bool) -> list[str]:
    if is_markdown:
        units = [
            section.strip() for section in _HEADER_RE.split(text) if section.strip()
        ]
        if units:
            return units

    return [para.strip() for para in re.split(r"\n{2,}", text) if para.strip()]


def _merge_into_chunks(
    units: list[str],
    chunk_size: int,
    overlap: int,
) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for unit in units:
        sep = 2 if current else 0
        if len(unit) > chunk_size:
            if current:
                chunks.append("\n\n".join(current))
                current = []
                current_len = 0
            chunks.extend(_split_oversized(unit, chunk_size, overlap))
        elif current_len + sep + len(unit) > chunk_size:
            chunks.append("\n\n".join(current))
            if current and len(current[-1]) <= overlap:
                prev = current[-1]
                current = [prev, unit]
                current_len = len(prev) + 2 + len(unit)
            else:
                current = [unit]
                current_len = len(unit)
        else:
            current_len += sep + len(unit)
            current.append(unit)

    if current:
        chunks.append("\n\n".join(current))

    return [chunk for chunk in chunks if chunk.strip()]


def _split_oversized(text: str, chunk_size: int, overlap: int) -> list[str]:
    sentences = _split_sentences(text)
    if len(sentences) <= 1:
        return _char_split(text, chunk_size, overlap)

    chunks: list[str] = []
    buf: list[str] = []
    buf_len = 0

    for sentence in sentences:
        sep = 1 if buf else 0
        if len(sentence) > chunk_size:
            if buf:
                chunks.append(" ".join(buf))
                buf = []
                buf_len = 0
            chunks.extend(_char_split(sentence, chunk_size, overlap))
        elif buf_len + sep + len(sentence) > chunk_size:
            chunks.append(" ".join(buf))
            if buf and len(buf[-1]) <= overlap:
                prev = buf[-1]
                buf = [prev, sentence]
                buf_len = len(prev) + 1 + len(sentence)
            else:
                buf = [sentence]
                buf_len = len(sentence)
        else:
            buf_len += sep + len(sentence)
            buf.append(sentence)

    if buf:
        chunks.append(" ".join(buf))

    return [chunk for chunk in chunks if chunk.strip()]


def _split_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    sentences = [match.group(0).strip() for match in _SENTENCE_RE.finditer(normalized)]
    return [sentence for sentence in sentences if sentence]


def _char_split(text: str, chunk_size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = end - overlap
    return chunks


def load_local_documents(
    docs_dir: str | Path = "docs",
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    manifest_path: str | Path | None = None,
) -> list[Document]:
    root = Path(docs_dir)

    if not root.exists():
        return []

    manifest_records = load_corpus_manifest(resolve_manifest_path(root, manifest_path))
    documents: list[Document] = []

    for path in sorted(root.rglob("*")):
        if not _is_supported_document(path):
            continue

        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue

        chunks = split_text(
            text,
            chunk_size=chunk_size,
            overlap=chunk_overlap,
            is_markdown=path.suffix.lower() == ".md",
        )
        manifest_record = _manifest_record_for_path(manifest_records, path)

        for chunk_index, chunk in enumerate(chunks):
            metadata = build_chunk_metadata(
                path,
                chunk,
                chunk_index,
                manifest_record=manifest_record,
            )
            documents.append(Document(page_content=chunk, metadata=metadata))

    return documents


def build_chunk_metadata(
    path: Path,
    content: str,
    chunk_index: int,
    *,
    manifest_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    content_sha256 = _sha256_text(content)
    metadata: dict[str, Any] = {
        "source": str(path),
        "source_name": path.name,
        "source_suffix": path.suffix.lower(),
        "chunk_index": chunk_index,
        "chunk_id": _sha256_text(f"{path.as_posix()}:{chunk_index}:{content_sha256}"),
        "content_sha256": content_sha256,
    }

    if manifest_record:
        metadata["original_filename"] = str(
            manifest_record.get("original_filename", "")
        )
        metadata["file_type"] = str(manifest_record.get("file_type", ""))
        page_range = _page_range_for_chunk(content, manifest_record)
        if page_range is not None:
            metadata["page_start"], metadata["page_end"] = page_range

    return metadata


def build_knowledge_base(
    config: AppConfig,
    docs_dir: str | Path = "docs",
    persist_dir: str | Path = ".chroma",
    batch_size: int = EMBED_BATCH_SIZE,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    manifest_path: str | Path | None = None,
    reset: bool = False,
) -> Chroma:
    persist_path = Path(persist_dir)
    resolved_manifest_path = resolve_manifest_path(docs_dir, manifest_path)
    manifest_hash = (
        sha256_file(resolved_manifest_path) if resolved_manifest_path else None
    )

    if reset and persist_path.exists():
        shutil.rmtree(persist_path)
    elif persist_path.exists():
        validate_embedding_signature(
            persist_path,
            config,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            corpus_manifest_sha256=manifest_hash,
        )

    documents = load_local_documents(
        docs_dir,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        manifest_path=resolved_manifest_path,
    )
    if not documents:
        message = "No markdown or text documents found in docs directory."
        raise ValueError(message)

    embedding_model = create_embedding_model(config)
    client = chromadb.PersistentClient(path=str(persist_path))

    store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embedding_model,
        client=client,
    )

    for start in range(0, len(documents), batch_size):
        store.add_documents(documents[start : start + batch_size])

    write_embedding_signature(
        persist_path,
        config,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        corpus_manifest_sha256=manifest_hash,
    )
    return store


def load_knowledge_base(
    config: AppConfig,
    persist_dir: str | Path = ".chroma",
) -> Chroma:
    validate_embedding_signature(persist_dir, config)
    embedding_model = create_embedding_model(config)
    client = chromadb.PersistentClient(path=str(persist_dir))

    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embedding_model,
        client=client,
    )


def search_knowledge_base(
    query: str,
    config: AppConfig,
    persist_dir: str | Path = ".chroma",
    k: int = 4,
) -> str:
    vector_store = load_knowledge_base(config, persist_dir)
    documents = vector_store.similarity_search(query, k=k)

    if not documents:
        return "No relevant local documents found."

    return format_documents(documents)


def format_documents(documents: list[Document]) -> str:
    formatted_documents: list[str] = []

    for document in documents:
        source = document.metadata.get("source", "unknown")
        chunk_index = document.metadata.get("chunk_index", "unknown")
        content = document.page_content.strip()

        formatted_documents.append(
            f"Source: {source}, chunk: {chunk_index}\n{content}",
        )

    return "\n\n---\n\n".join(formatted_documents)


def resolve_manifest_path(
    docs_dir: str | Path,
    manifest_path: str | Path | None = None,
) -> Path | None:
    if manifest_path is not None:
        path = Path(manifest_path)
        if not path.exists():
            raise FileNotFoundError(f"Corpus manifest does not exist: {path}")
        return path

    root = Path(docs_dir)
    candidates = (
        root.parent / "corpus_manifest.jsonl",
        root.parent / "corpus_manifest.json",
        root / "corpus_manifest.jsonl",
        root / "corpus_manifest.json",
    )
    return next((path for path in candidates if path.exists()), None)


def load_corpus_manifest(manifest_path: Path | None) -> dict[str, dict[str, Any]]:
    if manifest_path is None:
        return {}

    if manifest_path.suffix == ".json":
        raw_records = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        raw_records = [
            json.loads(line)
            for line in manifest_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    records: dict[str, dict[str, Any]] = {}
    for record in raw_records:
        if not isinstance(record, dict):
            continue
        output_path = record.get("output_path")
        output_filename = record.get("output_filename")
        if isinstance(output_path, str):
            records[Path(output_path).name] = record
            records[Path(output_path).as_posix()] = record
        if isinstance(output_filename, str):
            records[output_filename] = record
    return records


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_record_for_path(
    records: dict[str, dict[str, Any]],
    path: Path,
) -> dict[str, Any] | None:
    return records.get(path.name) or records.get(path.as_posix())


def _page_range_for_chunk(
    content: str,
    manifest_record: dict[str, Any],
) -> tuple[int, int] | None:
    pages = [int(match.group("page")) for match in _PAGE_MARKER_RE.finditer(content)]
    if pages:
        return min(pages), max(pages)

    if manifest_record.get("pages") == 1:
        return 1, 1

    return None


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _is_supported_document(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
