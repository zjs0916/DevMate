from __future__ import annotations

import logging
import socket
import subprocess
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import NamedTuple

from devmate.config import AppConfig, PreviewConfig

LOGGER = logging.getLogger(__name__)


class _RunningPreview(NamedTuple):
    process: subprocess.Popen
    port: int
    log_path: Path
    url: str


_PREVIEWS: dict[str, _RunningPreview] = {}


def create_preview_tools(config: AppConfig) -> list:
    from langchain_core.tools import tool

    preview_cfg = config.preview

    @tool("start_fastapi_preview")
    def _start_fastapi_preview(project_path: str) -> str:
        """Start a FastAPI preview server for a generated project and open the browser."""
        return start_fastapi_preview(project_path, preview_cfg)

    @tool("stop_preview")
    def _stop_preview(project_path: str = "") -> str:
        """Stop a running preview. Pass the project path to stop a specific one, or empty string to stop all."""
        return stop_preview(project_path or None, preview_cfg)

    @tool("list_previews")
    def _list_previews() -> str:
        """List all currently running previews and their URLs."""
        return list_previews()

    return [_start_fastapi_preview, _stop_preview, _list_previews]


def start_fastapi_preview(project_path: str, preview_cfg: PreviewConfig) -> str:
    if not preview_cfg.enabled:
        return "Preview is disabled in config."

    generated_dir = Path(preview_cfg.generated_projects_dir).resolve()
    resolved = Path(project_path).resolve()

    if generated_dir not in resolved.parents and resolved != generated_dir:
        return (
            f"Error: project_path must be inside {generated_dir}. Got: {resolved}"
        )

    if not (resolved / "pyproject.toml").exists():
        return f"Error: {resolved / 'pyproject.toml'} not found."

    if not (resolved / "src" / "main.py").exists():
        return f"Error: {resolved / 'src' / 'main.py'} not found."

    key = str(resolved)
    if key in _PREVIEWS:
        prev = _PREVIEWS[key]
        if prev.process.poll() is None:
            return f"Preview already running at {prev.url}"
        del _PREVIEWS[key]

    port = _find_available_port(preview_cfg)
    if port is None:
        return (
            f"Error: No available port in range "
            f"{preview_cfg.port_start}–{preview_cfg.port_end}."
        )

    log_dir = resolved / ".devmate"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / "preview.log"

    cmd = [
        "uv",
        "run",
        "uvicorn",
        "src.main:app",
        "--host",
        preview_cfg.host,
        "--port",
        str(port),
    ]

    LOGGER.info("Starting preview for %s on port %d", resolved.name, port)

    with log_path.open("w", encoding="utf-8") as log_file:
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(resolved),
                stdout=log_file,
                stderr=log_file,
            )
        except FileNotFoundError as exc:
            return f"Error: Could not launch uvicorn (is uv installed?): {exc}"

    url = f"http://{preview_cfg.host}:{port}"
    _PREVIEWS[key] = _RunningPreview(proc, port, log_path, url)

    status = _probe_url(url)

    if status is None:
        proc.terminate()
        del _PREVIEWS[key]
        return (
            f"Error: Preview did not respond within 10 seconds. "
            f"Check logs: {log_path}"
        )

    if status >= 500:
        proc.terminate()
        del _PREVIEWS[key]
        return (
            f"Error: Preview started but returned HTTP {status}. "
            f"Check logs: {log_path}"
        )

    if preview_cfg.open_browser and not _is_in_docker():
        webbrowser.open(url)

    return f"Preview started at {url} (logs: {log_path})"


def stop_preview(project_path: str | None, preview_cfg: PreviewConfig) -> str:
    if project_path is None:
        if not _PREVIEWS:
            return "No running previews."
        stopped = []
        for key, prev in list(_PREVIEWS.items()):
            prev.process.terminate()
            del _PREVIEWS[key]
            stopped.append(prev.url)
        return "Stopped previews: " + ", ".join(stopped)

    resolved = str(Path(project_path).resolve())
    if resolved not in _PREVIEWS:
        return f"No preview running for: {project_path}"

    prev = _PREVIEWS.pop(resolved)
    prev.process.terminate()
    return f"Stopped preview at {prev.url}"


def list_previews() -> str:
    if not _PREVIEWS:
        return "No running previews."
    lines = []
    for key, prev in _PREVIEWS.items():
        status = "running" if prev.process.poll() is None else "stopped"
        lines.append(f"  {prev.url} ({status}) — {key}")
    return "Running previews:\n" + "\n".join(lines)


def _find_available_port(preview_cfg: PreviewConfig) -> int | None:
    for port in range(preview_cfg.port_start, preview_cfg.port_end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((preview_cfg.host, port))
                return port
            except OSError:
                continue
    return None


def _probe_url(url: str, timeout: float = 10.0) -> int | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                return resp.status
        except urllib.error.HTTPError as exc:
            return exc.code
        except Exception:
            time.sleep(0.5)
    return None


def _is_in_docker() -> bool:
    if Path("/.dockerenv").exists():
        return True
    try:
        return "docker" in Path("/proc/1/cgroup").read_text(encoding="utf-8")
    except OSError:
        return False
