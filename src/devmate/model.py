from __future__ import annotations

import os

from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings

from devmate.config import AppConfig


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


def create_embedding_model(config: AppConfig) -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=config.model.embedding_model_name,
        base_url=config.model.ai_base_url,
        api_key=config.model.api_key,
    )
