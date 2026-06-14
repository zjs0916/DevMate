from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from typing import Any

from devmate.agent import create_devmate_agent
from devmate.agent import extract_last_message_content
from devmate.agent import run_agent_once
from devmate.config import load_config

LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run DevMate AI coding assistant.",
    )
    parser.add_argument(
        "prompt",
        nargs="*",
        help="Optional single-turn user request for DevMate.",
    )
    parser.add_argument(
        "--config",
        default="config.toml",
        help="Path to config TOML file.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Start a multi-turn interactive DevMate session.",
    )
    return parser.parse_args()


async def async_main() -> int:
    logging.basicConfig(level=logging.INFO)

    args = parse_args()
    user_input = " ".join(args.prompt).strip()

    if args.interactive or not user_input:
        return await run_interactive_session(args.config)

    response = await run_agent_once(
        user_input=user_input,
        config_path=args.config,
    )
    sys.stdout.write(f"{response}\n")
    return 0


async def run_interactive_session(config_path: str) -> int:
    """Run DevMate as a multi-turn command line assistant."""
    config = load_config(config_path)
    agent = await create_devmate_agent(config)
    messages: list[Any] = []

    sys.stdout.write(
        "DevMate interactive mode. Type /exit or /quit to stop.\n",
    )

    while True:
        sys.stdout.write("\nYou: ")
        sys.stdout.flush()

        user_input = sys.stdin.readline()
        if not user_input:
            sys.stdout.write("\n")
            return 0

        user_input = user_input.strip()
        if user_input in {"/exit", "/quit"}:
            return 0

        if not user_input:
            continue

        messages.append(
            {
                "role": "user",
                "content": user_input,
            },
        )

        try:
            result = await agent.ainvoke({"messages": messages})
        except Exception:
            LOGGER.exception("DevMate agent failed.")
            return 1

        messages = list(result.get("messages", []))
        response = extract_last_message_content(result)

        sys.stdout.write(f"\nDevMate:\n{response}\n")


def normalise_messages(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert agent messages into a serialisable message history."""
    messages = result.get("messages", [])
    normalised: list[dict[str, Any]] = []

    for message in messages:
        if isinstance(message, dict):
            normalised.append(message)
            continue

        role = getattr(message, "type", "assistant")
        content = getattr(message, "content", "")
        normalised.append(
            {
                "role": role,
                "content": content,
            },
        )

    return normalised


def main() -> None:
    exit_code = asyncio.run(async_main())
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()