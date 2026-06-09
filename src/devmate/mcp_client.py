from __future__ import annotations

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from devmate.config import AppConfig


def build_mcp_url(config: AppConfig) -> str:
    endpoint = config.mcp.endpoint

    if not endpoint.startswith("/"):
        endpoint = f"/{endpoint}"

    if not endpoint.endswith("/"):
        endpoint = f"{endpoint}/"

    return f"http://{config.mcp.host}:{config.mcp.port}{endpoint}"


def create_mcp_client(config: AppConfig) -> MultiServerMCPClient:
    return MultiServerMCPClient(
        {
            "devmate_search": {
                "transport": "streamable_http",
                "url": build_mcp_url(config),
                "headers": {
                    "Accept": "application/json, text/event-stream",
                },
            },
        },
    )


async def load_mcp_tools(config: AppConfig) -> list[BaseTool]:
    client = create_mcp_client(config)
    return await client.get_tools()
