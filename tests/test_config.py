from devmate.config import load_config


def test_default_embedding_config() -> None:
    config = load_config("config.toml")

    assert config.model.embedding_provider == "fastembed"
    assert config.model.embedding_model_name == "BAAI/bge-small-en-v1.5"
    assert config.model.embedding_dimensions == 384


def test_mcp_required_config_exists() -> None:
    config = load_config("config.toml")

    assert isinstance(config.mcp.required, bool)
