from __future__ import annotations

import os
from typing import Any

from fastmcp import FastMCP
from tavily import TavilyClient

from devmate.config import load_config

CONFIG_PATH_ENV = "DEVMATE_CONFIG"

mcp = FastMCP(name="DevMateSearch")


@mcp.tool
def search_web(query: str, max_results: int = 5) -> str:
    """Search the web using Tavily and return concise results."""
    config = load_config(_get_config_path())
    client = TavilyClient(api_key=config.search.tavily_api_key)

    response = client.search(
        query=query,
        max_results=max_results,
        include_answer=True,
        search_depth="basic",
    )

    return _format_search_results(response)


def _format_search_results(response: dict[str, Any]) -> str:
    lines: list[str] = []
    answer = response.get("answer")

    if answer:
        lines.append(f"Answer: {answer}")

    results = response.get("results", [])

    if not results:
        return "No web search results found."

    for index, result in enumerate(results, start=1):
        title = result.get("title", "Untitled")
        url = result.get("url", "")
        content = result.get("content", "")

        lines.append(
            f"{index}. {title}\nURL: {url}\nSnippet: {content}",
        )

    return "\n\n".join(lines)


def _get_config_path() -> str:
    return os.environ.get(CONFIG_PATH_ENV, "config.toml")


def main() -> None:
    config = load_config(_get_config_path())
    mcp.run(
        transport="http",
        host=config.mcp.host,
        port=config.mcp.port,
        path=config.mcp.endpoint,
        log_level="debug",
    )


if __name__ == "__main__":
    main()
