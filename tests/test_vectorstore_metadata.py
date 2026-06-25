from __future__ import annotations

import json
from pathlib import Path

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
from devmate.vectorstore_metadata import (
    SIGNATURE_FILENAME,
    build_embedding_signature,
    validate_embedding_signature,
    write_embedding_signature,
)


def _make_config(provider: str, model: str, dimensions: int) -> AppConfig:
    return AppConfig(
        model=ModelConfig(
            ai_base_url="http://example",
            api_key="k",
            model_name="m",
            embedding_base_url="",
            embedding_api_key="",
            embedding_model_name=model,
            embedding_provider=provider,
            embedding_dimensions=dimensions,
        ),
        search=SearchConfig(tavily_api_key="t"),
        langsmith=LangSmithConfig(langchain_tracing_v2=False, langchain_api_key=""),
        skills=SkillsConfig(skills_dir=".skills"),
        mcp=MCPConfig(host="127.0.0.1", port=8765, endpoint="/mcp", required=False),
        preview=PreviewConfig(
            enabled=False,
            host="127.0.0.1",
            port_start=8000,
            port_end=8099,
            open_browser=False,
            generated_projects_dir="generated_projects",
        ),
    )


def test_signature_written_and_read(tmp_path: Path) -> None:
    config = _make_config("fastembed", "BAAI/bge-small-en-v1.5", 384)

    write_embedding_signature(tmp_path, config)

    sig_path = tmp_path / SIGNATURE_FILENAME
    assert sig_path.exists()
    stored = json.loads(sig_path.read_text(encoding="utf-8"))
    assert stored == build_embedding_signature(config)
    assert stored["embedding_provider"] == "fastembed"
    assert stored["embedding_model_name"] == "BAAI/bge-small-en-v1.5"
    assert stored["embedding_dimensions"] == 384


def test_matching_signature_validates_silently(tmp_path: Path) -> None:
    config = _make_config("fastembed", "BAAI/bge-small-en-v1.5", 384)
    write_embedding_signature(tmp_path, config)

    # Should not raise.
    validate_embedding_signature(tmp_path, config)


def test_dimension_mismatch_raises(tmp_path: Path) -> None:
    written = _make_config("fastembed", "BAAI/bge-small-en-v1.5", 384)
    write_embedding_signature(tmp_path, written)

    different = _make_config("ollama", "bge-m3", 1024)

    with pytest.raises(RuntimeError, match="different embedding configuration"):
        validate_embedding_signature(tmp_path, different)


def test_missing_signature_does_not_raise(tmp_path: Path) -> None:
    config = _make_config("fastembed", "BAAI/bge-small-en-v1.5", 384)

    # No signature file present at all -> should be tolerant (warning only).
    validate_embedding_signature(tmp_path, config)
