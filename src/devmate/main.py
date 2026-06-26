from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from typing import Any

from langchain_core.messages import BaseMessage

from devmate.agent import (
    build_langsmith_run_config,
    create_devmate_agent,
    run_agent_once,
)
from devmate.config import load_config

LOGGER = logging.getLogger(__name__)

EXIT_COMMANDS = {"exit", "quit", "q", ":q"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run DevMate AI coding assistant.",
    )
    parser.add_argument(
        "prompt",
        nargs="*",
        help="User request for DevMate.",
    )
    parser.add_argument(
        "--config",
        default="config.toml",
        help="Path to config TOML file.",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Start an interactive DevMate chat session.",
    )
    return parser.parse_args()


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


async def invoke_agent_turn(
    agent: Any,
    messages: list[Any],
    user_input: str,
    config_path: str,
) -> list[Any]:
    request_messages = [
        *messages,
        {
            "role": "user",
            "content": user_input,
        },
    ]

    result = await agent.ainvoke(
        {"messages": request_messages},
        config=build_langsmith_run_config(config_path),
    )
    response = extract_last_message_content(result)

    if response:
        sys.stdout.write(f"\n{response}\n\n")
    else:
        sys.stdout.write("\n[DevMate returned no visible response.]\n\n")

    sys.stdout.flush()
    return list(result.get("messages", request_messages))


async def run_interactive(
    config_path: str,
    initial_prompt: str = "",
) -> int:
    config = load_config(config_path)
    agent = await create_devmate_agent(config)

    messages: list[Any] = []

    sys.stdout.write(
        "DevMate interactive mode. Type 'exit' or 'quit' to stop.\n",
    )
    sys.stdout.flush()

    if initial_prompt:
        try:
            messages = await invoke_agent_turn(
                agent=agent,
                messages=messages,
                user_input=initial_prompt,
                config_path=config_path,
            )
        except Exception:
            LOGGER.exception("Initial DevMate request failed.")
            return 1

    while True:
        try:
            user_input = input("DevMate> ").strip()
        except (EOFError, KeyboardInterrupt):
            sys.stdout.write("\n")
            return 0

        if not user_input:
            continue

        if user_input.lower() in EXIT_COMMANDS:
            return 0

        try:
            messages = await invoke_agent_turn(
                agent=agent,
                messages=messages,
                user_input=user_input,
                config_path=config_path,
            )
        except Exception:
            LOGGER.exception("DevMate request failed.")


async def async_main() -> int:
    logging.basicConfig(level=logging.INFO)

    args = parse_args()
    user_input = " ".join(args.prompt).strip()

    if args.interactive:
        return await run_interactive(
            config_path=args.config,
            initial_prompt=user_input,
        )

    if not user_input:
        sys.stdout.write("Enter your request for DevMate:\n")
        sys.stdout.flush()
        user_input = sys.stdin.readline().strip()

    if not user_input:
        LOGGER.error("No user request provided.")
        return 1

    response = await run_agent_once(
        user_input=user_input,
        config_path=args.config,
    )
    sys.stdout.write(f"{response}\n")
    return 0


def main() -> None:
    exit_code = asyncio.run(async_main())
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
