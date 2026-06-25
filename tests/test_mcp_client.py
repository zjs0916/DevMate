from __future__ import annotations

import os

import pytest

from devmate.config import (
    AppConfig,
    LangSmithConfig,
    MCPConfig,
    ModelConfig,
    PreviewConfig,
    SearchConfig,
    SkillsConfig,
)
from devmate.mcp_client import (
    build_mcp_url,
    create_mcp_client,
    ensure_localhost_bypasses_proxy,
)


def _make_config(host: str, port: int, endpoint: str) -> AppConfig:
    return AppConfig(
        model=ModelConfig(
            ai_base_url="http://example",
            api_key="k",
            model_name="m",
            embedding_base_url="",
            embedding_api_key="",
            embedding_model_name="BAAI/bge-small-en-v1.5",
            embedding_provider="fastembed",
            embedding_dimensions=384,
        ),
        search=SearchConfig(tavily_api_key="t"),
        langsmith=LangSmithConfig(langchain_tracing_v2=False, langchain_api_key=""),
        skills=SkillsConfig(skills_dir=".skills"),
        mcp=MCPConfig(host=host, port=port, endpoint=endpoint, required=False),
        preview=PreviewConfig(
            enabled=False,
            host="127.0.0.1",
            port_start=8000,
            port_end=8099,
            open_browser=False,
            generated_projects_dir="generated_projects",
        ),
    )


def test_build_url_standard() -> None:
    config = _make_config("127.0.0.1", 8765, "/mcp")
    assert build_mcp_url(config) == "http://127.0.0.1:8765/mcp"


def test_build_url_adds_leading_slash() -> None:
    config = _make_config("localhost", 9000, "mcp")
    assert build_mcp_url(config) == "http://localhost:9000/mcp"


def test_build_url_strips_trailing_slash() -> None:
    config = _make_config("127.0.0.1", 8765, "/mcp/")
    assert build_mcp_url(config) == "http://127.0.0.1:8765/mcp"


def test_build_url_empty_endpoint_defaults() -> None:
    config = _make_config("127.0.0.1", 8765, "")
    assert build_mcp_url(config) == "http://127.0.0.1:8765/mcp"


def test_ensure_localhost_bypasses_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NO_PROXY", raising=False)
    monkeypatch.delenv("no_proxy", raising=False)

    ensure_localhost_bypasses_proxy()

    no_proxy = os.environ["NO_PROXY"]
    assert "127.0.0.1" in no_proxy
    assert "localhost" in no_proxy
    assert os.environ["no_proxy"] == no_proxy


def test_create_client_uses_http_transport() -> None:
    config = _make_config("127.0.0.1", 8765, "/mcp")
    client = create_mcp_client(config)

    # MultiServerMCPClient stores the connection spec it was built with.
    connections = getattr(client, "connections", None)
    assert connections is not None, "client has no connections attribute"
    spec = connections["devmate_search"]
    assert spec["transport"] == "http"
    assert spec["url"] == "http://127.0.0.1:8765/mcp"
