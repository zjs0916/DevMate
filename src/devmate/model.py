from __future__ import annotations

import os

from langchain_core.embeddings import Embeddings
from langchain_ollama import OllamaEmbeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from devmate.config import AppConfig
from devmate.fastembed_embeddings import FastEmbedEmbeddings


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

    if provider == "openai":
        model = OpenAIEmbeddings(
            model=config.model.embedding_model_name,
            base_url=config.model.embedding_base_url,
            api_key=config.model.embedding_api_key,
            dimensions=config.model.embedding_dimensions,
        )

    elif provider == "fastembed":
        model = FastEmbedEmbeddings(
            model_name=config.model.embedding_model_name,
        )

    elif provider == "ollama":
        model = OllamaEmbeddings(
            model=config.model.embedding_model_name,
            base_url=config.model.embedding_base_url,
        )

    else:
        message = f"Unsupported embedding provider: {provider}"
        raise ValueError(message)

    validate_embedding_dimensions(
        model,
        config.model.embedding_dimensions,
        provider=provider,
        model_name=config.model.embedding_model_name,
    )
    return model


def validate_embedding_dimensions(
    embedding_model: Embeddings,
    expected_dimensions: int,
    *,
    provider: str,
    model_name: str,
) -> None:
    if expected_dimensions <= 0:
        return

    vector = embedding_model.embed_query("devmate embedding dimension check")
    actual_dimensions = len(vector)

    if actual_dimensions != expected_dimensions:
        raise ValueError(
            "Embedding dimension mismatch: "
            f"provider={provider!r}, model={model_name!r}, "
            f"expected={expected_dimensions}, actual={actual_dimensions}. "
            "Update config.toml or rebuild the vector store with the correct embedding settings."
        )
