from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from langchain_core.messages import BaseMessage
from langchain_core.tools import BaseTool, tool

from devmate.config import AppConfig, load_config
from devmate.file_tools import create_file_tools
from devmate.mcp_client import load_mcp_tools
from devmate.model import configure_langsmith, create_chat_model
from devmate.preview import create_preview_tools
from devmate.rag import search_knowledge_base
from devmate.skills import create_skill_tools

LOGGER = logging.getLogger(__name__)

SYSTEM_PROMPT = "\n".join(
    [
        "You are DevMate, an AI coding assistant.",
        "",
        "Your job is to help users build and modify software projects.",
        "",
        "Important project rules:",
        "- Use uv for Python dependency and environment management.",
        "- Do not create or recommend requirements.txt.",
        "- Use pyproject.toml for Python dependencies.",
        "- Follow Python PEP 8.",
        "- Avoid Python print calls; use logging instead.",
        "- Prefer simple, readable project structures.",
        "",
        "Tool usage rules:",
        "- Use web search when the request may require current external knowledge.",
        "- Use the local knowledge base for project guidelines and templates.",
        "- Search saved skills before solving repeatable coding tasks.",
        "- Read relevant skills before generating or modifying project files.",
        "- Save a useful skill after completing a repeatable task pattern.",
        "- Use file tools to create project files in generated_projects/.",
        "",
        "Deep agent workflow:",
        "- Use planning for multi-step coding tasks.",
        "- Briefly explain the file plan before creating files.",
        "- After writing files, summarize what was created and how to run it.",
        "- In a follow-up conversation, reuse relevant saved skills instead of starting from scratch.",
        "",
        "When generating Python projects:",
        "- Include pyproject.toml.",
        "- Use uv commands in README.",
        "- Use logging instead of print.",
        "- Keep route handlers small.",
        "- Put business logic in separate modules when useful.",
        "",
        "FastAPI project generation rules:",
        "- The entry point must be src/main.py with a module-level `app = FastAPI(...)` variable.",
        "- Do NOT use `uv run start` anywhere — the correct start command is:",
        "  uv sync",
        "  uv run uvicorn src.main:app --host 127.0.0.1 --port 8000",
        "- Write this exact command in the README, not `uv run start`.",
        "- If index.html does not need Jinja template variables, serve it with HTMLResponse:",
        "  from pathlib import Path",
        "  from fastapi.responses import HTMLResponse",
        "  INDEX_HTML = Path(__file__).resolve().parent / 'templates' / 'index.html'",
        "  @router.get('/', response_class=HTMLResponse)",
        "  async def index() -> HTMLResponse:",
        "      return HTMLResponse(INDEX_HTML.read_text(encoding='utf-8'))",
        "- If Jinja2 templates are truly needed, use current Starlette-compatible TemplateResponse syntax.",
        "",
        "Preview rules:",
        "- After creating a runnable FastAPI web app under generated_projects, call start_fastapi_preview",
        "  with the generated project path so the user can access it immediately.",
        "- Do NOT tell the user to run `uv run start`.",
        "- If preview startup fails, show the error and log path, then fix the generated project",
        "  instead of asking the user to exit DevMate.",
        "- If you cannot auto-start the preview, tell the user the manual fallback:",
        "  cd generated_projects/<project-name>",
        "  uv sync",
        "  uv run uvicorn src.main:app --host 127.0.0.1 --port 8000",
    ],
)


def create_knowledge_base_tool(config: AppConfig) -> BaseTool:
    @tool(
        "search_knowledge_base",
        description="Search local project documents and guidelines.",
    )
    def search_local_docs(query: str) -> str:
        return search_knowledge_base(query=query, config=config)

    return search_local_docs


async def create_devmate_agent(config: AppConfig) -> Any:
    configure_langsmith(config)
    model = create_chat_model(config)

    try:
        mcp_tools = await load_mcp_tools(config)
    except Exception as exc:
        if config.mcp.required:
            raise RuntimeError(
                "MCP server is required but search_web tool could not be loaded. "
                "Start the MCP server or set mcp.required=false for local fallback mode."
            ) from exc
        LOGGER.warning("MCP tools unavailable; running without web search: %s", exc)
        mcp_tools = []

    local_tools = [
        create_knowledge_base_tool(config),
        *create_file_tools(),
        *create_skill_tools(config),
        *create_preview_tools(config),
    ]

    # Explicitly disable virtual mode so the backend performs real filesystem
    # operations rooted at the project directory (suppresses the ambiguous
    # root_dir/virtual_mode warning).
    backend = FilesystemBackend(root_dir=str(Path.cwd()), virtual_mode=False)
    skills_path = _normalise_skills_path(config.skills.skills_dir)

    return create_deep_agent(
        model=model,
        tools=[*local_tools, *mcp_tools],
        system_prompt=SYSTEM_PROMPT,
        backend=backend,
        skills=[skills_path],
    )


async def run_agent_once(
    user_input: str,
    config_path: str = "config.toml",
) -> str:
    config = load_config(config_path)
    agent = await create_devmate_agent(config)

    result = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": user_input,
                },
            ],
        },
    )

    return extract_last_message_content(result)


def extract_last_message_content(result: dict[str, Any]) -> str:
    messages = result.get("messages", [])
    if not messages:
        return ""

    last_message = messages[-1]

    if isinstance(last_message, BaseMessage):
        content = last_message.content
    elif isinstance(last_message, dict):
        content = last_message.get("content", "")
    else:
        content = getattr(last_message, "content", "")

    if isinstance(content, str):
        return content

    return str(content)


def _normalise_skills_path(skills_dir: str) -> str:
    path = Path(skills_dir).as_posix().strip("/")
    if not path:
        return ".skills/"
    return f"{path}/"
