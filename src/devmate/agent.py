from __future__ import annotations

from typing import Any

from langchain.agents import create_agent
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
- Do not recommend pip install -r requirements.txt.
- Use pyproject.toml for Python dependencies.
- Follow Python PEP 8.
- Do not use print() in Python code; use logging instead.
- Prefer simple, readable project structures.

Tool usage rules:
- Use web search when the request may require current external knowledge.
- Use the local knowledge base when the request may relate to project
  guidelines, templates, or internal documentation.
- Use file tools to actually create project files in generated_projects.
- Search saved skills before solving repeatable coding tasks.
- Save a useful skill after completing a repeatable task pattern.
- Before generating files, explain the file plan briefly.
- After writing files, summarize what was created and how to run it.

When generating Python projects:
- Include pyproject.toml.
- Use uv commands in README.
- Use logging instead of print.
- Keep route handlers small.
- Put business logic in separate modules when useful.
"""


def create_knowledge_base_tool(config: AppConfig) -> BaseTool:
    @tool("search_knowledge_base")
    def search_local_docs(query: str) -> str:
        """Search local project documents and guidelines."""
        return search_knowledge_base(query=query, config=config)

    return search_local_docs


async def create_devmate_agent(config: AppConfig) -> Any:
    configure_langsmith(config)

    model = create_chat_model(config)
    mcp_tools = await load_mcp_tools(config)
    local_tools = [
        create_knowledge_base_tool(config),
        *create_file_tools(),
        *create_skill_tools(config),
    ]
    tools = [*local_tools, *mcp_tools]

    return create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
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

    return _extract_last_message_content(result)


def _extract_last_message_content(result: dict[str, Any]) -> str:
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
