from __future__ import annotations

import re
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document

from devmate.config import AppConfig
from devmate.model import create_embedding_model
from devmate.vectorstore_metadata import validate_embedding_signature
from devmate.vectorstore_metadata import write_embedding_signature

import chromadb

COLLECTION_NAME = "devmate_docs"
SUPPORTED_SUFFIXES = {".md", ".txt"}

_HEADER_RE = re.compile(r"(?=^#{1,6}\s)", re.MULTILINE)
_SENTENCE_END_RE = re.compile(r"(?<=[.!?。！？])\s+")


def split_text(
    text: str,
    chunk_size: int = 900,
    overlap: int = 120,
) -> list[str]:
    if chunk_size <= overlap:
        message = "chunk_size must be greater than overlap."
        raise ValueError(message)

    units = _split_into_units(text)
    return _merge_into_chunks(units, chunk_size, overlap)


def _split_into_units(text: str) -> list[str]:
    units: list[str] = []
    for section in _HEADER_RE.split(text):
        for para in re.split(r"\n{2,}", section):
            para = para.strip()
            if para:
                units.append(para)
    return units


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

    return [c for c in chunks if c.strip()]


def _split_oversized(text: str, chunk_size: int, overlap: int) -> list[str]:
    sentences = _SENTENCE_END_RE.split(text)
    if len(sentences) <= 1:
        return _char_split(text, chunk_size, overlap)

    chunks: list[str] = []
    buf: list[str] = []
    buf_len = 0

    for s in sentences:
        s = s.strip()
        if not s:
            continue
        sep = 1 if buf else 0
        if len(s) > chunk_size:
            if buf:
                chunks.append(" ".join(buf))
                buf = []
                buf_len = 0
            chunks.extend(_char_split(s, chunk_size, overlap))
        elif buf_len + sep + len(s) > chunk_size:
            chunks.append(" ".join(buf))
            if buf and len(buf[-1]) <= overlap:
                prev = buf[-1]
                buf = [prev, s]
                buf_len = len(prev) + 1 + len(s)
            else:
                buf = [s]
                buf_len = len(s)
        else:
            buf_len += sep + len(s)
            buf.append(s)

    if buf:
        chunks.append(" ".join(buf))

    return [c for c in chunks if c.strip()]


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


def load_local_documents(docs_dir: str | Path = "docs") -> list[Document]:
    root = Path(docs_dir)

    if not root.exists():
        return []

    documents: list[Document] = []

    for path in sorted(root.rglob("*")):
        if not _is_supported_document(path):
            continue

        text = path.read_text(encoding="utf-8").strip()

        if not text:
            continue

        chunks = split_text(text)

        for chunk_index, chunk in enumerate(chunks):
            documents.append(
                Document(
                    page_content=chunk,
                    metadata={
                        "source": str(path),
                        "chunk_index": chunk_index,
                    },
                ),
            )

    return documents


def build_knowledge_base(
    config: AppConfig,
    docs_dir: str | Path = "docs",
    persist_dir: str | Path = ".chroma",
) -> Chroma:
    documents = load_local_documents(docs_dir)

    if not documents:
        message = "No markdown or text documents found in docs directory."
        raise ValueError(message)

    embedding_model = create_embedding_model(config)
    client = chromadb.PersistentClient(path=str(persist_dir))

    store = Chroma.from_documents(
        documents=documents,
        embedding=embedding_model,
        collection_name=COLLECTION_NAME,
        client=client,
    )
    write_embedding_signature(persist_dir, config)
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


def _is_supported_document(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
