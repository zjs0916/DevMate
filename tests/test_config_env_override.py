from __future__ import annotations

import pytest

from devmate.config import load_config


def test_env_overrides_model_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEVMATE_MODEL_NAME", "override-model")
    monkeypatch.setenv("DEVMATE_MODEL_API_KEY", "override-key")

    config = load_config("config.toml")

    assert config.model.model_name == "override-model"
    assert config.model.api_key == "override-key"


def test_env_overrides_embedding_dimensions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEVMATE_EMBEDDING_DIMENSIONS", "1024")

    config = load_config("config.toml")

    assert config.model.embedding_dimensions == 1024


def test_env_overrides_mcp_and_skills(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEVMATE_MCP_PORT", "9999")
    monkeypatch.setenv("DEVMATE_MCP_REQUIRED", "false")
    monkeypatch.setenv("DEVMATE_SKILLS_DIR", "/tmp/custom-skills")

    config = load_config("config.toml")

    assert config.mcp.port == 9999
    assert config.mcp.required is False
    assert config.skills.skills_dir == "/tmp/custom-skills"


def test_values_fall_back_to_file_without_env() -> None:
    config = load_config("config.toml")

    assert config.skills.skills_dir == ".skills"
    assert config.mcp.endpoint == "/mcp"
