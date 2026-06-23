from __future__ import annotations

from pathlib import Path

from langchain_core.tools import BaseTool, tool

PROJECT_OUTPUT_DIR = Path("generated_projects")


def create_file_tools() -> list[BaseTool]:
    @tool("write_project_file")
    def write_project_file(relative_path: str, content: str) -> str:
        """Write a file inside the generated_projects directory."""
        target_path = _safe_output_path(relative_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")

        return f"Wrote file: {target_path}"

    @tool("read_project_file")
    def read_project_file(relative_path: str) -> str:
        """Read a file from the generated_projects directory."""
        target_path = _safe_output_path(relative_path)

        if not target_path.exists():
            return f"File not found: {target_path}"

        return target_path.read_text(encoding="utf-8")

    @tool("list_project_files")
    def list_project_files() -> str:
        """List generated project files."""
        if not PROJECT_OUTPUT_DIR.exists():
            return "No generated project files found."

        paths = sorted(
            path for path in PROJECT_OUTPUT_DIR.rglob("*") if path.is_file()
        )

        if not paths:
            return "No generated project files found."

        return "\n".join(str(path) for path in paths)

    return [
        write_project_file,
        read_project_file,
        list_project_files,
    ]


def _safe_output_path(relative_path: str) -> Path:
    root = PROJECT_OUTPUT_DIR.resolve()
    target_path = (PROJECT_OUTPUT_DIR / relative_path).resolve()

    if root not in target_path.parents and target_path != root:
        message = "Path must stay inside generated_projects."
        raise ValueError(message)

    return target_path
