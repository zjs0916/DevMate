from __future__ import annotations

import socket
from pathlib import Path

from devmate.config import PreviewConfig
from devmate.config import load_config
from devmate.preview import _find_available_port
from devmate.preview import start_fastapi_preview


def _make_preview_cfg(generated_dir: Path, **overrides) -> PreviewConfig:
    defaults = dict(
        enabled=True,
        host="127.0.0.1",
        port_start=8000,
        port_end=8099,
        open_browser=False,
        generated_projects_dir=str(generated_dir),
    )
    defaults.update(overrides)
    return PreviewConfig(**defaults)


def test_path_outside_generated_projects_rejected(tmp_path: Path) -> None:
    gen_dir = tmp_path / "generated_projects"
    gen_dir.mkdir()
    outside = tmp_path / "sneaky"
    outside.mkdir()

    cfg = _make_preview_cfg(gen_dir)
    result = start_fastapi_preview(str(outside), cfg)

    assert "Error" in result
    assert "generated_projects" in result or str(gen_dir) in result


def test_path_traversal_rejected(tmp_path: Path) -> None:
    gen_dir = tmp_path / "generated_projects"
    gen_dir.mkdir()
    project = gen_dir / "real-project"
    project.mkdir()

    cfg = _make_preview_cfg(gen_dir)
    # Attempt traversal: inside then escape
    result = start_fastapi_preview(str(project / ".." / ".."), cfg)

    assert "Error" in result


def test_missing_pyproject_toml_fails(tmp_path: Path) -> None:
    gen_dir = tmp_path / "generated_projects"
    gen_dir.mkdir()
    project = gen_dir / "my-app"
    project.mkdir()
    # No pyproject.toml, no src/main.py

    cfg = _make_preview_cfg(gen_dir)
    result = start_fastapi_preview(str(project), cfg)

    assert "Error" in result
    assert "pyproject.toml" in result


def test_missing_src_main_fails(tmp_path: Path) -> None:
    gen_dir = tmp_path / "generated_projects"
    gen_dir.mkdir()
    project = gen_dir / "my-app"
    project.mkdir()
    (project / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    # src/main.py absent

    cfg = _make_preview_cfg(gen_dir)
    result = start_fastapi_preview(str(project), cfg)

    assert "Error" in result
    assert "main.py" in result


def test_port_finder_returns_available_port(tmp_path: Path) -> None:
    gen_dir = tmp_path / "generated_projects"
    gen_dir.mkdir()
    cfg = _make_preview_cfg(gen_dir)

    port = _find_available_port(cfg)

    assert port is not None
    assert cfg.port_start <= port <= cfg.port_end

    # Verify the returned port is actually free
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((cfg.host, port))


def test_port_finder_skips_occupied_port(tmp_path: Path) -> None:
    gen_dir = tmp_path / "generated_projects"
    gen_dir.mkdir()

    # Dynamically grab a free port and keep it bound so the test does not
    # depend on a fixed port (e.g. 8000) being available on the host. Binding
    # to port 0 both picks a currently-free port and occupies it race-free.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as blocker:
        blocker.bind(("127.0.0.1", 0))
        start_port = blocker.getsockname()[1]

        cfg = _make_preview_cfg(
            gen_dir, port_start=start_port, port_end=start_port + 50
        )
        port = _find_available_port(cfg)

    assert port is not None
    assert port != start_port

    # The returned port must actually be free.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((cfg.host, port))


def test_preview_config_loads_from_config_toml() -> None:
    config = load_config("config.toml")

    assert config.preview.enabled is True
    assert config.preview.host == "127.0.0.1"
    assert config.preview.port_start == 8000
    assert config.preview.port_end == 8099
    assert config.preview.open_browser is True
    assert config.preview.generated_projects_dir == "generated_projects"


def test_preview_disabled_returns_early(tmp_path: Path) -> None:
    gen_dir = tmp_path / "generated_projects"
    gen_dir.mkdir()
    project = gen_dir / "my-app"
    project.mkdir()
    (project / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    (project / "src").mkdir()
    (project / "src" / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n")

    cfg = _make_preview_cfg(gen_dir, enabled=False)
    result = start_fastapi_preview(str(project), cfg)

    assert "disabled" in result.lower()
