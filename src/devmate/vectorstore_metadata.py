from __future__ import annotations

import json
import logging
from pathlib import Path

from devmate.config import AppConfig

SIGNATURE_FILENAME = "embedding_config.json"

logger = logging.getLogger(__name__)


def build_embedding_signature(config: AppConfig) -> dict:
    return {
        "embedding_provider": config.model.embedding_provider,
        "embedding_model_name": config.model.embedding_model_name,
        "embedding_dimensions": config.model.embedding_dimensions,
    }


def write_embedding_signature(persist_directory: str | Path, config: AppConfig) -> None:
    path = Path(persist_directory) / SIGNATURE_FILENAME
    path.write_text(json.dumps(build_embedding_signature(config), indent=2), encoding="utf-8")


def validate_embedding_signature(persist_directory: str | Path, config: AppConfig) -> None:
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
    current = build_embedding_signature(config)

    if stored != current:
        raise RuntimeError(
            "Existing vector store was built with a different embedding configuration.\n"
            f"Current: {current['embedding_provider']} / {current['embedding_model_name']} / {current['embedding_dimensions']}\n"
            f"Stored:  {stored.get('embedding_provider')} / {stored.get('embedding_model_name')} / {stored.get('embedding_dimensions')}\n"
            "Please rebuild the vector store by deleting .chroma and .skills/.chroma "
            "or rerunning the indexing command."
        )
