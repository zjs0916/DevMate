from __future__ import annotations

import os
from pathlib import Path

from fastembed import TextEmbedding
from langchain_core.embeddings import Embeddings

_DEFAULT_CACHE_DIR = str(Path(__file__).parent.parent.parent / ".fastembed_cache")


class FastEmbedEmbeddings(Embeddings):
    """Local semantic embeddings backed by FastEmbed."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        cache_dir = os.environ.get("FASTEMBED_CACHE_PATH", _DEFAULT_CACHE_DIR)
        self.model = TextEmbedding(model_name=model_name, cache_dir=cache_dir)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed document chunks for vector storage."""
        if not texts:
            return []

        embeddings = self.model.embed(texts)
        return [embedding.tolist() for embedding in embeddings]

    def embed_query(self, text: str) -> list[float]:
        """Embed a user query for vector search."""
        return self.embed_documents([text])[0]