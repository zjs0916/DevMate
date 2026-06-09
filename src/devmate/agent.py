from __future__ import annotations

from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import BaseMessage
from langchain_core.tools import BaseTool
from langchain_core.tools import tool

from devmate.config import AppConfig
from devmate.config import load_config
from devmate.mcp_client import load_mcp_tools
from devmate.model import configure_langsmith
from devmate.model import create_chat_model
from devmate.rag import search_knowledge_base

SYSTEM_PROMPT = """
You are DevMate, an AI coding assistant.

Your job is to help users build and modify software projects.

Important rules:
- Use web search when the request may require current external knowledge.
- Use the local knowledge base when the request may relate to project
  guidelines, templates, or internal documentation.
- Before generating a project, explain the file plan briefly.
- Generate clear, runnable code.
- Do not invent tool results.
- Prefer simple project structures unless the user asks otherwise.
- Follow Python PEP 8.
- Do not use print() in Python code; use logging instead.
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
    local_tools = [create_knowledge_base_tool(config)]
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
