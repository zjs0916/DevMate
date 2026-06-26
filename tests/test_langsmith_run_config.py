from __future__ import annotations

import pytest

from devmate.agent import build_langsmith_run_config


def test_langsmith_run_config_defaults_to_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DEVMATE_RUNTIME", raising=False)
    monkeypatch.delenv("HOSTNAME", raising=False)

    run_config = build_langsmith_run_config("config.toml")

    assert run_config["tags"] == ["devmate", "rag", "local"]
    assert run_config["metadata"] == {
        "runtime": "local",
        "devmate_config": "config.toml",
        "rag_persist_dir": ".chroma",
        "hostname": None,
    }


def test_langsmith_run_config_uses_runtime_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEVMATE_RUNTIME", "docker")
    monkeypatch.setenv("HOSTNAME", "container-host")

    run_config = build_langsmith_run_config("/app/config.docker.toml")

    assert run_config["tags"] == ["devmate", "rag", "docker"]
    assert run_config["metadata"]["runtime"] == "docker"
    assert run_config["metadata"]["devmate_config"] == "config.docker.toml"
    assert run_config["metadata"]["rag_persist_dir"] == ".chroma"
    assert run_config["metadata"]["hostname"] == "container-host"
