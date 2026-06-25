"""RAG-only smoke / quality test for DevMate's local knowledge base.

This script proves that local RAG retrieval works against the Chroma index
built from ``rag_eval/corpus``. It calls ``search_knowledge_base`` from
``devmate.rag`` directly:

* it does NOT build a full agent,
* it does NOT start the MCP server,
* it does NOT call ``search_web`` / Tavily.

Beyond a plain "did we retrieve something" check, each question also asserts:

1. retrieval returned context at all,
2. the top retrieved chunk comes from the expected source file,
3. the retrieved text satisfies the keyword expectations — every
   ``expected_keywords_all`` keyword present AND at least one
   ``expected_keywords_any`` keyword present — so a source-file hit that does
   not answer the question is reported instead of silently passing. Splitting
   into ``_all`` (narrow anchor) and ``_any`` (discriminating terms) avoids
   false positives from a broad word that matches almost any chunk in the file.

Retrieval + source-file checks are always hard requirements (non-zero exit on
failure). Keyword checks are reported and counted; by default a keyword miss is
a loud WARNING (so the lightweight FastEmbed path still completes), and
``--strict-keywords`` escalates keyword misses to failures — useful when
evaluating a multilingual embedding such as Ollama ``bge-m3``.

Run after indexing the corpus::

    PYTHONPATH=src uv run python -m devmate.index_docs \
        --config config.local.toml --docs-dir rag_eval/corpus \
        --persist-dir .chroma_rag_eval

    PYTHONPATH=src uv run python scripts/test_rag_retrieval.py \
        --config config.local.toml --persist-dir .chroma_rag_eval --k 4
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass, field
from pathlib import Path

from devmate.config import load_config
from devmate.rag import search_knowledge_base

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class RagQuestion:
    """A single retrieval test case with content-quality expectations."""

    question: str
    expected_source: str
    # Three complementary, optional keyword rules, combined with AND:
    # * ``_all``    — every keyword must appear.
    # * ``_any``    — at least one keyword must appear.
    # * ``_groups`` — AND-of-ORs: each group must contribute at least one hit.
    # ``_groups`` is the most flexible: one group per concept, listing the
    # synonyms the corpus might actually use (e.g. 小绿瓶/小瓶/瓶子/瓶). This keeps
    # the check strict about *which concepts* are present without hard-binding a
    # single exact phrase, and stops a broad word (e.g. 韩立) from passing alone.
    expected_keywords_all: tuple[str, ...] = ()
    expected_keywords_any: tuple[str, ...] = ()
    expected_keyword_groups: tuple[tuple[str, ...], ...] = ()


DEFAULT_QUESTIONS: list[RagQuestion] = [
    RagQuestion(
        question="韩立是谁引荐进入七玄门考验的？",
        expected_source="fanren.txt",
        expected_keyword_groups=(
            ("韩立",),
            # 语料实际用「举荐」表达"引荐"，补上这个同义词（只加确实出现的词）。
            ("引荐", "推荐", "介绍", "举荐"),
            ("七玄门", "考验"),
        ),
    ),
    RagQuestion(
        question="韩立的小绿瓶有什么作用？",
        expected_source="fanren.txt",
        expected_keyword_groups=(
            ("小绿瓶", "小瓶", "瓶子", "瓶"),
            ("药草", "催熟", "灵药", "药材", "成熟"),
        ),
    ),
    RagQuestion(
        question="D&D 中 advantage and disadvantage 是什么意思？",
        expected_source="players_handbook.txt",
        expected_keywords_any=("advantage", "disadvantage", "higher", "lower", "d20"),
    ),
    RagQuestion(
        question="D&D ability modifier 怎么计算？",
        expected_source="players_handbook.txt",
        expected_keywords_any=("ability modifier", "ability score", "modifier", "scores"),
    ),
    RagQuestion(
        question="D&D 1级角色的 proficiency bonus 是多少？",
        expected_source="players_handbook.txt",
        expected_keywords_any=("proficiency bonus", "+2", "1st level", "1st"),
    ),
]

PREVIEW_CHARS = 200
NO_RESULT_MARKER = "No relevant local documents found."


@dataclass
class QuestionResult:
    question: RagQuestion
    retrieved: bool
    top_source: str | None
    preview: str
    covered_sources: set[str] = field(default_factory=set)
    matched_all: list[str] = field(default_factory=list)
    missing_all: list[str] = field(default_factory=list)
    matched_any: list[str] = field(default_factory=list)
    group_matches: list[list[str]] = field(default_factory=list)

    @property
    def source_ok(self) -> bool:
        return self.top_source == self.question.expected_source

    @property
    def keyword_applicable(self) -> bool:
        question = self.question
        return bool(
            question.expected_keywords_all
            or question.expected_keywords_any
            or question.expected_keyword_groups
        )

    @property
    def all_ok(self) -> bool:
        # Every required keyword must be present (vacuously true when unset).
        return not self.question.expected_keywords_all or not self.missing_all

    @property
    def any_ok(self) -> bool:
        # At least one keyword must be present (vacuously true when unset).
        return not self.question.expected_keywords_any or bool(self.matched_any)

    @property
    def groups_ok(self) -> bool:
        # AND-of-ORs: every group must contribute at least one matched keyword.
        groups = self.question.expected_keyword_groups
        if not groups:
            return True
        if len(self.group_matches) != len(groups):
            return False
        return all(bool(matched) for matched in self.group_matches)

    @property
    def keyword_ok(self) -> bool:
        return self.all_ok and self.any_ok and self.groups_ok

    @property
    def passed(self) -> bool:
        return self.retrieved and self.source_ok and self.keyword_ok


def expected_sources(questions: list[RagQuestion]) -> list[str]:
    """Unique expected source files, preserving first-seen order."""
    ordered: list[str] = []
    for question in questions:
        if question.expected_source not in ordered:
            ordered.append(question.expected_source)
    return ordered


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="RAG-only smoke / quality test for DevMate's local knowledge base.",
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
    parser.add_argument(
        "--strict-keywords",
        action="store_true",
        help=(
            "Treat a missing keyword (right source but no expected keyword in "
            "the retrieved text) as a failure instead of a warning."
        ),
    )
    return parser.parse_args()


def _parse_documents(context: str) -> list[tuple[str | None, str]]:
    """Split RAG output into ``(source_file, body)`` blocks.

    ``search_knowledge_base`` returns documents formatted as::

        Source: <path>, chunk: <n>
        <content>

        ---

        Source: ...
    """
    parsed: list[tuple[str | None, str]] = []
    for block in context.split("\n\n---\n\n"):
        lines = block.split("\n", 1)
        header = lines[0]
        body = lines[1] if len(lines) > 1 else ""

        source_file: str | None = None
        if header.startswith("Source:"):
            raw_source = header[len("Source:"):].split(", chunk:", 1)[0].strip()
            source_file = Path(raw_source).name

        parsed.append((source_file, body))
    return parsed


def run_question(
    question: RagQuestion,
    config,
    persist_dir: str,
    k: int,
) -> QuestionResult:
    context = search_knowledge_base(
        query=question.question,
        config=config,
        persist_dir=persist_dir,
        k=k,
    )

    if not context or context.strip() == NO_RESULT_MARKER:
        return QuestionResult(
            question,
            retrieved=False,
            top_source=None,
            preview="",
            missing_all=list(question.expected_keywords_all),
        )

    documents = _parse_documents(context)
    top_source = documents[0][0] if documents else None
    preview = " ".join(documents[0][1].split())[:PREVIEW_CHARS] if documents else ""
    covered = {source for source, _ in documents if source}

    combined = "\n".join(body for _, body in documents).lower()
    matched_all = [kw for kw in question.expected_keywords_all if kw.lower() in combined]
    missing_all = [kw for kw in question.expected_keywords_all if kw.lower() not in combined]
    matched_any = [kw for kw in question.expected_keywords_any if kw.lower() in combined]
    group_matches = [
        [kw for kw in group if kw.lower() in combined]
        for group in question.expected_keyword_groups
    ]

    return QuestionResult(
        question,
        retrieved=True,
        top_source=top_source,
        preview=preview,
        covered_sources=covered,
        matched_all=matched_all,
        missing_all=missing_all,
        matched_any=matched_any,
        group_matches=group_matches,
    )


def log_result(index: int, result: QuestionResult) -> None:
    question = result.question
    LOGGER.info("[%d] question: %s", index, question.question)
    LOGGER.info("    retrieved: %s", "yes" if result.retrieved else "no")
    LOGGER.info("    expected source: %s", question.expected_source)
    LOGGER.info(
        "    top source file: %s  (%s)",
        result.top_source or "(none)",
        "match" if result.source_ok else "MISMATCH",
    )
    if question.expected_keywords_all:
        if result.all_ok:
            LOGGER.info(
                "    keywords (all): PASS (matched: %s)",
                ", ".join(question.expected_keywords_all),
            )
        else:
            LOGGER.warning(
                "    keywords (all): WARN — missing required %s in retrieved text",
                result.missing_all,
            )
    if question.expected_keywords_any:
        if result.any_ok:
            LOGGER.info(
                "    keywords (any): PASS (matched: %s)",
                ", ".join(result.matched_any),
            )
        else:
            LOGGER.warning(
                "    keywords (any): WARN — none of %s found in retrieved text",
                list(question.expected_keywords_any),
            )
    for number, group in enumerate(question.expected_keyword_groups, start=1):
        matched = result.group_matches[number - 1] if number - 1 < len(result.group_matches) else []
        if matched:
            LOGGER.info(
                "    keyword group %d: PASS (matched: %s)",
                number,
                ", ".join(matched),
            )
        else:
            LOGGER.warning(
                "    keyword group %d: WARN — none of %s found in retrieved text",
                number,
                list(group),
            )
    LOGGER.info("    chunk preview: %s", result.preview or "(none)")
    LOGGER.info("")


def log_summary(results: list[QuestionResult], *, strict_keywords: bool) -> None:
    total = len(results)
    with_context = sum(1 for r in results if r.retrieved)
    source_passed = sum(1 for r in results if r.source_ok)
    keyword_total = sum(1 for r in results if r.keyword_applicable)
    keyword_passed = sum(1 for r in results if r.keyword_applicable and r.keyword_ok)
    covered: set[str] = set()
    for result in results:
        covered |= result.covered_sources

    LOGGER.info("=" * 60)
    LOGGER.info("Summary")
    LOGGER.info("=" * 60)
    LOGGER.info("total questions:           %d", total)
    LOGGER.info("questions with context:    %d / %d", with_context, total)
    LOGGER.info("source checks passed:      %d / %d", source_passed, total)
    LOGGER.info("keyword checks passed:     %d / %d", keyword_passed, keyword_total)
    LOGGER.info("sources covered:")
    for source in expected_sources([r.question for r in results]):
        mark = "yes" if source in covered else "no"
        LOGGER.info("    %s: %s", source, mark)

    if keyword_passed < keyword_total:
        missed = keyword_total - keyword_passed
        LOGGER.warning("")
        LOGGER.warning(
            "%d question(s) failed the keyword check "
            "(missing a required keyword, or no expected keyword matched).",
            missed,
        )
        if strict_keywords:
            LOGGER.warning("--strict-keywords is set: these count as failures.")
        else:
            LOGGER.warning(
                "Re-run with --strict-keywords to fail on low retrieval quality, or "
                "use a multilingual embedding (Ollama bge-m3) for CJK corpora.",
            )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    args = parse_args()

    persist_path = Path(args.persist_dir)
    if not persist_path.exists():
        LOGGER.error("Chroma index not found at: %s", persist_path)
        LOGGER.error("Build it first by running:")
        LOGGER.error(
            "  PYTHONPATH=src uv run python -m devmate.index_docs "
            "--config %s --docs-dir rag_eval/corpus --persist-dir %s",
            args.config,
            args.persist_dir,
        )
        raise SystemExit(1)

    config = load_config(args.config)

    LOGGER.info(
        "Running RAG-only smoke / quality test (k=%d, persist_dir=%s)",
        args.k,
        args.persist_dir,
    )
    LOGGER.info("config: %s", args.config)
    LOGGER.info("strict keywords: %s", "yes" if args.strict_keywords else "no")
    LOGGER.info("=" * 60)
    LOGGER.info("")

    results: list[QuestionResult] = []
    for index, question in enumerate(DEFAULT_QUESTIONS, start=1):
        result = run_question(question, config, args.persist_dir, args.k)
        results.append(result)
        log_result(index, result)

    log_summary(results, strict_keywords=args.strict_keywords)

    structural_ok = all(r.retrieved and r.source_ok for r in results)
    keywords_ok = all(r.keyword_ok for r in results)

    if not structural_ok or (args.strict_keywords and not keywords_ok):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
