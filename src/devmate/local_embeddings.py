from __future__ import annotations

import hashlib
import math
import re

from langchain_core.embeddings import Embeddings

TOKEN_PATTERN = re.compile(r"\w+")


class LocalHashEmbeddings(Embeddings):
    def __init__(self, dimensions: int = 384) -> None:
        if dimensions <= 0:
            message = "dimensions must be greater than zero."
            raise ValueError(message)

        self.dimensions = dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_text(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_text(text)

    def _embed_text(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = TOKEN_PATTERN.findall(text.lower())

        if not tokens:
            tokens = [text.lower()]

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))

        if norm == 0:
            return vector

        return [value / norm for value in vector]
