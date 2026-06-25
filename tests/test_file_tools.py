from __future__ import annotations

import pytest

from devmate import file_tools
from devmate.file_tools import PROJECT_OUTPUT_DIR, _safe_output_path


def test_nested_path_inside_root_is_allowed() -> None:
    target = _safe_output_path("demo/src/main.py")

    root = PROJECT_OUTPUT_DIR.resolve()
    assert target == root / "demo" / "src" / "main.py"
    assert root in target.parents


def test_parent_traversal_is_rejected() -> None:
    with pytest.raises(ValueError, match="generated_projects"):
        _safe_output_path("../escape.txt")


def test_deep_traversal_is_rejected() -> None:
    with pytest.raises(ValueError):
        _safe_output_path("../../etc/passwd")


def test_absolute_path_escape_is_rejected() -> None:
    with pytest.raises(ValueError):
        _safe_output_path("/etc/passwd")


def test_write_tool_blocks_traversal(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Point the output root at an isolated temp dir to avoid touching the repo.
    monkeypatch.setattr(file_tools, "PROJECT_OUTPUT_DIR", tmp_path / "generated_projects")
    write_tool, _read_tool, _list_tool = file_tools.create_file_tools()

    with pytest.raises(ValueError):
        write_tool.invoke({"relative_path": "../outside.txt", "content": "x"})
