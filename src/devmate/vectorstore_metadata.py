from __future__ import annotations

import json
import logging
from pathlib import Path

from devmate.config import AppConfig

SIGNATURE_FILENAME = "embedding_config.json"

logger = logging.getLogger(__name__)


def build_embedding_signature(
    config: AppConfig,
    *,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    corpus_manifest_sha256: str | None = None,
) -> dict:
    signature = {
        "embedding_provider": config.model.embedding_provider,
        "embedding_model_name": config.model.embedding_model_name,
        "embedding_dimensions": config.model.embedding_dimensions,
    }
    if chunk_size is not None:
        signature["chunk_size"] = chunk_size
    if chunk_overlap is not None:
        signature["chunk_overlap"] = chunk_overlap
    if corpus_manifest_sha256 is not None:
        signature["corpus_manifest_sha256"] = corpus_manifest_sha256
    return signature


def write_embedding_signature(
    persist_directory: str | Path,
    config: AppConfig,
    *,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    corpus_manifest_sha256: str | None = None,
) -> None:
    path = Path(persist_directory) / SIGNATURE_FILENAME
    path.write_text(
        json.dumps(
            build_embedding_signature(
                config,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                corpus_manifest_sha256=corpus_manifest_sha256,
            ),
            indent=2,
        ),
        encoding="utf-8",
    )


def validate_embedding_signature(
    persist_directory: str | Path,
    config: AppConfig,
    *,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    corpus_manifest_sha256: str | None = None,
) -> None:
    sig_path = Path(persist_directory) / SIGNATURE_FILENAME

    if not sig_path.exists():
        if Path(persist_directory).exists():
            logger.warning(
                "Vector store at %s has no embedding signature (built with an older version). "
                "Consider rebuilding the index to ensure compatibility.",
                persist_directory,
            )
        return

    stored = json.loads(sig_path.read_text(encoding="utf-8"))
    current = build_embedding_signature(
        config,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        corpus_manifest_sha256=corpus_manifest_sha256,
    )

    stored_current_fields = {key: stored.get(key) for key in current}
    if stored_current_fields != current:
        raise RuntimeError(
            "Existing vector store was built with a different embedding configuration.\n"
            f"Current: {current}\n"
            f"Stored:  {stored}\n"
            "Please rebuild the vector store by deleting .chroma and .skills/.chroma "
            "or rerunning the indexing command."
        )
