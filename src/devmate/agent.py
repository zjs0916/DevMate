from __future__ import annotations

from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from langchain_core.messages import BaseMessage
from langchain_core.tools import BaseTool
from langchain_core.tools import tool

from devmate.config import AppConfig
from devmate.config import load_config
from devmate.file_tools import create_file_tools
from devmate.mcp_client import load_mcp_tools
from devmate.model import configure_langsmith
from devmate.model import create_chat_model
from devmate.rag import search_knowledge_base
from devmate.skills import create_skill_tools

SYSTEM_PROMPT = """
You are DevMate, an AI coding assistant.

Your job is to help users build and modify software projects.

Important project rules:
- Use uv for Python dependency and environment management.
- Do not create or recommend requirements.txt.
- Use pyproject.toml for Python dependencies.
- Follow Python PEP 8.
- Avoid Python print calls; use logging instead.
- Prefer simple, readable project structures.

Tool usage rules:
- Use web search when the request may require current external knowledge.
- Use the local knowledge base for project guidelines and templates.
- Search saved skills before solving repeatable coding tasks.
- Read relevant skills before generating or modifying project files.
- Save a useful skill after completing a repeatable task pattern.
- Use file tools to create project files in generated_projects/.

Deep agent workflow:
- Use planning for multi-step coding tasks.
- Briefly explain the file plan before creating files.
- After writing files, summarize what was created and how to run it.
- In a follow-up conversation, reuse relevant saved skills instead of starting
  from scratch.

When generating Python projects:
- Include pyproject.toml.
- Use uv commands in README.
- Use logging instead of print.
- Keep route handlers small.
- Put business logic in separate modules when useful.
"""


def create_knowledge_base_tool(config: AppConfig) -> BaseTool:
    """Create a tool for searching local project documents."""

    @tool("search_knowledge_base")
    def search_local_docs(query: str) -> str:
        """Search local project documents and guidelines."""
        return search_knowledge_base(query=query, config=config)

    return search_local_docs


async def create_devmate_agent(config: AppConfig) -> Any:
    """Create the DevMate Deep Agent with MCP, RAG, files, and Skills."""
    configure_langsmith(config)

    model = create_chat_model(config)
    mcp_tools = await load_mcp_tools(config)
    local_tools = [
        create_knowledge_base_tool(config),
        *create_file_tools(),
        *create_skill_tools(config),
    ]

    backend = FilesystemBackend(root_dir=str(Path.cwd()))
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
    """Run a single DevMate turn."""
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
    """Extract the final assistant message from an agent result."""
    messages = result.get("messages", [])
    if not messages:
        return ""

    last_message = messages[-1]
    if isinstance(last_message, BaseMessage):
        content = last_message.content
    else:
        content = last_message.get("content", "")

    if isinstance(content, str):
        return content
    return str(content)


def _normalise_skills_path(skills_dir: str) -> str:
    path = Path(skills_dir).as_posix().strip("/")
    if not path:
        return ".skills/"
    return f"{path}/"