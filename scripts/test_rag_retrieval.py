"""RAG-only smoke test for DevMate's local knowledge base.

This script proves that local RAG retrieval works against the Chroma index
built from ``rag_eval/corpus``. It calls ``search_knowledge_base`` from
``devmate.rag`` directly:

* it does NOT build a full agent,
* it does NOT start the MCP server,
* it does NOT call ``search_web`` / Tavily.

Run after indexing the corpus::

    PYTHONPATH=src uv run python -m devmate.index_docs \
        --config config.local.toml --docs-dir rag_eval/corpus --persist-dir .chroma

    PYTHONPATH=src uv run python scripts/test_rag_retrieval.py \
        --config config.local.toml --k 4
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from pathlib import Path

from devmate.config import load_config
from devmate.rag import search_knowledge_base

LOGGER = logging.getLogger(__name__)

DEFAULT_QUESTIONS = [
    "韩立是谁引荐进入七玄门相关考验的？",
    "韩立的小绿瓶有什么作用？",
    "D&D 中 advantage and disadvantage 是什么意思？",
    "D&D 中 ability modifier 怎么计算？",
    "D&D 中 1 级角色的 proficiency bonus 是多少？",
]

EXPECTED_SOURCES = ["fanren.txt", "players_handbook.txt"]

PREVIEW_CHARS = 200
NO_RESULT_MARKER = "No relevant local documents found."


@dataclass
class QuestionResult:
    question: str
    source_file: str | None
    preview: str
    retrieved: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="RAG-only smoke test for DevMate's local knowledge base.",
    )
    parser.add_argument(
        "--config",
        default="config.local.toml",
        help="Path to config TOML file.",
    )
    parser.add_argument(
        "--persist-dir",
        default=".chroma",
        help="Directory for the local Chroma vector database.",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=4,
        help="Number of chunks to retrieve per question.",
    )
    return parser.parse_args()


def _parse_first_document(context: str) -> tuple[str | None, str]:
    """Extract the source file and a content preview from RAG output.

    ``search_knowledge_base`` returns documents formatted as::

        Source: <path>, chunk: <n>
        <content>

        ---

        Source: ...

    We only inspect the top (most relevant) document for the report.
    """
    first_block = context.split("\n\n---\n\n", 1)[0]
    lines = first_block.split("\n", 1)
    header = lines[0]
    body = lines[1] if len(lines) > 1 else ""

    source_file: str | None = None
    if header.startswith("Source:"):
        raw_source = header[len("Source:"):].split(", chunk:", 1)[0].strip()
        source_file = Path(raw_source).name

    preview = " ".join(body.split())[:PREVIEW_CHARS]
    return source_file, preview


def run_question(question: str, config, persist_dir: str, k: int) -> QuestionResult:
    context = search_knowledge_base(
        query=question,
        config=config,
        persist_dir=persist_dir,
        k=k,
    )

    if not context or context.strip() == NO_RESULT_MARKER:
        return QuestionResult(question, None, "", retrieved=False)

    source_file, preview = _parse_first_document(context)
    return QuestionResult(question, source_file, preview, retrieved=True)


def log_result(index: int, result: QuestionResult) -> None:
    LOGGER.info("[%d] question: %s", index, result.question)
    LOGGER.info("    retrieved: %s", "yes" if result.retrieved else "no")
    LOGGER.info("    source file: %s", result.source_file or "(none)")
    LOGGER.info("    chunk preview: %s", result.preview or "(none)")
    LOGGER.info("")


def log_summary(results: list[QuestionResult]) -> None:
    total = len(results)
    with_context = sum(1 for r in results if r.retrieved)
    covered = {r.source_file for r in results if r.source_file}

    LOGGER.info("=" * 60)
    LOGGER.info("Summary")
    LOGGER.info("=" * 60)
    LOGGER.info("total questions:            %d", total)
    LOGGER.info("questions with context:     %d", with_context)
    LOGGER.info("sources covered:")
    for source in EXPECTED_SOURCES:
        mark = "yes" if source in covered else "no"
        LOGGER.info("    %s: %s", source, mark)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    args = parse_args()

    persist_path = Path(args.persist_dir)
    if not persist_path.exists():
        LOGGER.error("Chroma index not found at: %s", persist_path)
        LOGGER.error("Build it first by running:")
        LOGGER.error(
            "  PYTHONPATH=src uv run python -m devmate.index_docs "
            "--config config.local.toml --docs-dir rag_eval/corpus "
            "--persist-dir .chroma",
        )
        raise SystemExit(1)

    config = load_config(args.config)

    LOGGER.info(
        "Running RAG-only smoke test (k=%d, persist_dir=%s)",
        args.k,
        args.persist_dir,
    )
    LOGGER.info("config: %s", args.config)
    LOGGER.info("=" * 60)
    LOGGER.info("")

    results: list[QuestionResult] = []
    for index, question in enumerate(DEFAULT_QUESTIONS, start=1):
        result = run_question(question, config, args.persist_dir, args.k)
        results.append(result)
        log_result(index, result)

    log_summary(results)

    if not all(r.retrieved for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
