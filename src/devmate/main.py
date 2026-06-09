from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from devmate.agent import run_agent_once

LOGGER = logging.getLogger(__name__)


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

    return parser.parse_args()


async def async_main() -> int:
    logging.basicConfig(level=logging.INFO)
    args = parse_args()
    user_input = " ".join(args.prompt).strip()

    if not user_input:
        sys.stdout.write("Enter your request for DevMate:\n")
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
