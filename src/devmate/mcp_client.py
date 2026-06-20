from __future__ import annotations

import os

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from devmate.config import AppConfig


LOCAL_NO_PROXY_HOSTS = ("127.0.0.1", "localhost", "::1")


def ensure_localhost_bypasses_proxy() -> None:
    existing_values = [
        os.environ.get("NO_PROXY", ""),
        os.environ.get("no_proxy", ""),
    ]
    parts = {
        item.strip()
        for value in existing_values
        for item in value.split(",")
        if item.strip()
    }
    parts.update(LOCAL_NO_PROXY_HOSTS)

    value = ",".join(sorted(parts))
    os.environ["NO_PROXY"] = value
    os.environ["no_proxy"] = value


def build_mcp_url(config: AppConfig) -> str:
    endpoint = config.mcp.endpoint or "/mcp"

    if not endpoint.startswith("/"):
        endpoint = f"/{endpoint}"

    endpoint = endpoint.rstrip("/") or "/"

    return f"http://{config.mcp.host}:{config.mcp.port}{endpoint}"


def create_mcp_client(config: AppConfig) -> MultiServerMCPClient:
    ensure_localhost_bypasses_proxy()

    return MultiServerMCPClient(
        {
            "devmate_search": {
                "transport": "http",
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