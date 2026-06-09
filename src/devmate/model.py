from __future__ import annotations

import os

from langchain_core.embeddings import Embeddings
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings

from devmate.config import AppConfig
from devmate.local_embeddings import LocalHashEmbeddings


def configure_langsmith(config: AppConfig) -> None:
    os.environ["LANGCHAIN_TRACING_V2"] = str(
        config.langsmith.langchain_tracing_v2,
    ).lower()
    os.environ["LANGCHAIN_API_KEY"] = config.langsmith.langchain_api_key


def create_chat_model(config: AppConfig) -> ChatOpenAI:
    return ChatOpenAI(
        model=config.model.model_name,
        base_url=config.model.ai_base_url,
        api_key=config.model.api_key,
        temperature=0,
    )


def create_embedding_model(config: AppConfig) -> Embeddings:
    provider = config.model.embedding_provider.lower()

    if provider == "hash":
        return LocalHashEmbeddings(
            dimensions=config.model.embedding_dimensions,
        )

    if provider == "openai":
        return OpenAIEmbeddings(
            model=config.model.embedding_model_name,
            base_url=config.model.ai_base_url,
            api_key=config.model.api_key,
        )

    message = f"Unsupported embedding provider: {provider}"
    raise ValueError(message)
