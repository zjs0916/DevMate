from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ModelConfig:
    ai_base_url: str
    api_key: str
    model_name: str
    embedding_base_url: str
    embedding_api_key: str
    embedding_model_name: str
    embedding_provider: str
    embedding_dimensions: int


@dataclass(frozen=True)
class SearchConfig:
    tavily_api_key: str


@dataclass(frozen=True)
class LangSmithConfig:
    langchain_tracing_v2: bool
    langchain_api_key: str


@dataclass(frozen=True)
class SkillsConfig:
    skills_dir: str


@dataclass(frozen=True)
class MCPConfig:
    host: str
    port: int
    endpoint: str


@dataclass(frozen=True)
class AppConfig:
    model: ModelConfig
    search: SearchConfig
    langsmith: LangSmithConfig
    skills: SkillsConfig
    mcp: MCPConfig


def load_config(config_path: str | Path = "config.toml") -> AppConfig:
    path = Path(config_path)

    with path.open("rb") as file:
        data = tomllib.load(file)

    return AppConfig(
        model=_load_model_config(data),
        search=_load_search_config(data),
        langsmith=_load_langsmith_config(data),
        skills=_load_skills_config(data),
        mcp=_load_mcp_config(data),
    )


def _load_model_config(data: dict[str, Any]) -> ModelConfig:
    model = data["model"]

    return ModelConfig(
        ai_base_url=_get_env_or_value(
            "DEVMATE_MODEL_BASE_URL",
            model["ai_base_url"],
        ),
        api_key=_get_env_or_value(
            "DEVMATE_MODEL_API_KEY",
            model["api_key"],
        ),
        model_name=_get_env_or_value(
            "DEVMATE_MODEL_NAME",
            model["model_name"],
        ),
        embedding_base_url=_get_env_or_value(
            "DEVMATE_EMBEDDING_BASE_URL",
            model.get("embedding_base_url", model["ai_base_url"]),
        ),
        embedding_api_key=_get_env_or_value(
            "DEVMATE_EMBEDDING_API_KEY",
            model.get("embedding_api_key", model["api_key"]),
        ),
        embedding_model_name=_get_env_or_value(
            "DEVMATE_EMBEDDING_MODEL_NAME",
            model["embedding_model_name"],
        ),
        embedding_provider=_get_env_or_value(
            "DEVMATE_EMBEDDING_PROVIDER",
            model.get("embedding_provider", "openai"),
        ),
        embedding_dimensions=int(
            _get_env_or_value(
                "DEVMATE_EMBEDDING_DIMENSIONS",
                str(model.get("embedding_dimensions", 1536)),
            ),
        ),
    )


def _load_search_config(data: dict[str, Any]) -> SearchConfig:
    search = data["search"]

    return SearchConfig(
        tavily_api_key=_get_env_or_value(
            "DEVMATE_TAVILY_API_KEY",
            search["tavily_api_key"],
        ),
    )


def _load_langsmith_config(data: dict[str, Any]) -> LangSmithConfig:
    langsmith = data["langsmith"]

    return LangSmithConfig(
        langchain_tracing_v2=_to_bool(
            _get_env_or_value(
                "DEVMATE_LANGCHAIN_TRACING_V2",
                str(langsmith["langchain_tracing_v2"]),
            ),
        ),
        langchain_api_key=_get_env_or_value(
            "DEVMATE_LANGCHAIN_API_KEY",
            langsmith["langchain_api_key"],
        ),
    )


def _load_skills_config(data: dict[str, Any]) -> SkillsConfig:
    skills = data["skills"]

    return SkillsConfig(
        skills_dir=_get_env_or_value(
            "DEVMATE_SKILLS_DIR",
            skills.get("skills_dir", ".skills"),
        ),
    )


def _load_mcp_config(data: dict[str, Any]) -> MCPConfig:
    mcp = data.get("mcp", {})

    return MCPConfig(
        host=_get_env_or_value(
            "DEVMATE_MCP_HOST",
            mcp.get("host", "127.0.0.1"),
        ),
        port=int(
            _get_env_or_value(
                "DEVMATE_MCP_PORT",
                str(mcp.get("port", 8000)),
            ),
        ),
        endpoint=_get_env_or_value(
            "DEVMATE_MCP_ENDPOINT",
            mcp.get("endpoint", "/mcp"),
        ),
    )


def _get_env_or_value(name: str, value: str) -> str:
    return os.environ.get(name, value)


def _to_bool(value: str) -> bool:
    return value.lower() in {"1", "true", "yes", "on"}