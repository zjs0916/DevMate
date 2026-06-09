from __future__ import annotations

from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document

from devmate.config import AppConfig
from devmate.model import create_embedding_model

COLLECTION_NAME = "devmate_docs"
SUPPORTED_SUFFIXES = {".md", ".txt"}


def split_text(
    text: str,
    chunk_size: int = 900,
    overlap: int = 120,
) -> list[str]:
    if chunk_size <= overlap:
        message = "chunk_size must be greater than overlap."
        raise ValueError(message)

    chunks: list[str] = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end == text_length:
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

    return Chroma.from_documents(
        documents=documents,
        embedding=embedding_model,
        collection_name=COLLECTION_NAME,
        persist_directory=str(persist_dir),
    )


def load_knowledge_base(
    config: AppConfig,
    persist_dir: str | Path = ".chroma",
) -> Chroma:
    embedding_model = create_embedding_model(config)

    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embedding_model,
        persist_directory=str(persist_dir),
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
