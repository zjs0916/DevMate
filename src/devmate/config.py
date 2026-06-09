from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import tomllib


@dataclass(frozen=True)
class ModelConfig:
    ai_base_url: str
    api_key: str
    model_name: str
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
        ai_base_url=model["ai_base_url"],
        api_key=model["api_key"],
        model_name=model["model_name"],
        embedding_model_name=model["embedding_model_name"],
        embedding_provider=model.get("embedding_provider", "openai"),
        embedding_dimensions=model.get("embedding_dimensions", 1536),
    )


def _load_search_config(data: dict[str, Any]) -> SearchConfig:
    search = data["search"]

    return SearchConfig(
        tavily_api_key=search["tavily_api_key"],
    )


def _load_langsmith_config(data: dict[str, Any]) -> LangSmithConfig:
    langsmith = data["langsmith"]

    return LangSmithConfig(
        langchain_tracing_v2=langsmith["langchain_tracing_v2"],
        langchain_api_key=langsmith["langchain_api_key"],
    )


def _load_skills_config(data: dict[str, Any]) -> SkillsConfig:
    skills = data["skills"]

    return SkillsConfig(
        skills_dir=skills.get("skills_dir", ".skills"),
    )


def _load_mcp_config(data: dict[str, Any]) -> MCPConfig:
    mcp = data.get("mcp", {})

    return MCPConfig(
        host=mcp.get("host", "127.0.0.1"),
        port=mcp.get("port", 8000),
        endpoint=mcp.get("endpoint", "/mcp"),
    )
