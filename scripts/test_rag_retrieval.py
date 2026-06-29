"""RAG-only retrieval evaluation against an existing Chroma index.

The script calls ``search_knowledge_base`` directly. It does not build an
agent, start MCP, or call Tavily.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from devmate.config import AppConfig, load_config
from devmate.rag import search_knowledge_base

LOGGER = logging.getLogger(__name__)

DEFAULT_EVAL_CASES = Path("rag_eval/eval_cases.example.json")
NO_RESULT_MARKER = "No relevant local documents found."
PREVIEW_CHARS = 200


@dataclass(frozen=True)
class RagEvalCase:
    question: str
    expected_source: str | None = None
    expected_source_contains: str | None = None
    expected_keywords_all: tuple[str, ...] = ()
    expected_keywords_any: tuple[str, ...] = ()
    expected_keyword_groups: tuple[tuple[str, ...], ...] = ()


@dataclass
class QuestionResult:
    case: RagEvalCase
    retrieved: bool
    top_source: str | None
    preview: str
    covered_sources: set[str] = field(default_factory=set)
    matched_all: list[str] = field(default_factory=list)
    missing_all: list[str] = field(default_factory=list)
    matched_any: list[str] = field(default_factory=list)
    group_matches: list[list[str]] = field(default_factory=list)

    @property
    def source_applicable(self) -> bool:
        return bool(self.case.expected_source or self.case.expected_source_contains)

    @property
    def source_ok(self) -> bool:
        if not self.source_applicable:
            return True
        if self.top_source is None:
            return False
        if self.case.expected_source is not None:
            return self.top_source == self.case.expected_source
        if self.case.expected_source_contains is not None:
            return self.case.expected_source_contains in self.top_source
        return True

    @property
    def keyword_applicable(self) -> bool:
        case = self.case
        return bool(
            case.expected_keywords_all
            or case.expected_keywords_any
            or case.expected_keyword_groups
        )

    @property
    def all_ok(self) -> bool:
        return not self.case.expected_keywords_all or not self.missing_all

    @property
    def any_ok(self) -> bool:
        return not self.case.expected_keywords_any or bool(self.matched_any)

    @property
    def groups_ok(self) -> bool:
        groups = self.case.expected_keyword_groups
        return not groups or (
            len(self.group_matches) == len(groups)
            and all(bool(matches) for matches in self.group_matches)
        )

    @property
    def keyword_ok(self) -> bool:
        return self.all_ok and self.any_ok and self.groups_ok


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate local RAG retrieval against external JSON cases.",
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
        "--eval-cases",
        default=str(DEFAULT_EVAL_CASES),
        help="JSON file containing retrieval evaluation cases.",
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
        help="Treat missing expected keywords as failures instead of warnings.",
    )
    return parser.parse_args()


def load_eval_cases(path: str | Path) -> list[RagEvalCase]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Eval cases JSON must be a list.")

    cases = [_parse_eval_case(item, index) for index, item in enumerate(data, start=1)]
    if not cases:
        raise ValueError("Eval cases JSON must contain at least one case.")
    return cases


def _parse_eval_case(item: Any, index: int) -> RagEvalCase:
    if not isinstance(item, dict):
        raise ValueError(f"Eval case {index} must be an object.")

    question = item.get("question")
    if not isinstance(question, str) or not question.strip():
        raise ValueError(f"Eval case {index} must include a non-empty question.")

    expected_source = _optional_string(item, "expected_source", index)
    expected_source_contains = _optional_string(
        item,
        "expected_source_contains",
        index,
    )
    return RagEvalCase(
        question=question,
        expected_source=expected_source,
        expected_source_contains=expected_source_contains,
        expected_keywords_all=_string_tuple(item, "expected_keywords_all", index),
        expected_keywords_any=_string_tuple(item, "expected_keywords_any", index),
        expected_keyword_groups=_keyword_groups(item, index),
    )


def _optional_string(item: dict[str, Any], key: str, index: int) -> str | None:
    value = item.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Eval case {index} field {key!r} must be a non-empty string.")
    return value


def _string_tuple(item: dict[str, Any], key: str, index: int) -> tuple[str, ...]:
    value = item.get(key, [])
    if not isinstance(value, list) or not all(
        isinstance(entry, str) for entry in value
    ):
        raise ValueError(f"Eval case {index} field {key!r} must be a list of strings.")
    return tuple(entry for entry in value if entry)


def _keyword_groups(
    item: dict[str, Any],
    index: int,
) -> tuple[tuple[str, ...], ...]:
    value = item.get("expected_keyword_groups", [])
    if not isinstance(value, list):
        raise ValueError(
            f"Eval case {index} field 'expected_keyword_groups' must be a list."
        )

    groups: list[tuple[str, ...]] = []
    for group_index, group in enumerate(value, start=1):
        if not isinstance(group, list) or not all(
            isinstance(entry, str) for entry in group
        ):
            raise ValueError(
                f"Eval case {index} keyword group {group_index} must be a list of strings."
            )
        cleaned = tuple(entry for entry in group if entry)
        if cleaned:
            groups.append(cleaned)
    return tuple(groups)


def run_question(
    case: RagEvalCase,
    config: AppConfig,
    persist_dir: str | Path,
    k: int,
) -> QuestionResult:
    context = search_knowledge_base(
        query=case.question,
        config=config,
        persist_dir=persist_dir,
        k=k,
    )

    if not context or context.strip() == NO_RESULT_MARKER:
        return QuestionResult(
            case=case,
            retrieved=False,
            top_source=None,
            preview="",
            missing_all=list(case.expected_keywords_all),
        )

    documents = parse_documents(context)
    top_source = documents[0][0] if documents else None
    preview = " ".join(documents[0][1].split())[:PREVIEW_CHARS] if documents else ""
    covered = {source for source, _ in documents if source}
    keyword_result = match_keywords(
        "\n".join(body for _, body in documents),
        case,
    )

    return QuestionResult(
        case=case,
        retrieved=True,
        top_source=top_source,
        preview=preview,
        covered_sources=covered,
        matched_all=keyword_result["matched_all"],
        missing_all=keyword_result["missing_all"],
        matched_any=keyword_result["matched_any"],
        group_matches=keyword_result["group_matches"],
    )


def parse_documents(context: str) -> list[tuple[str | None, str]]:
    parsed: list[tuple[str | None, str]] = []
    for block in context.split("\n\n---\n\n"):
        lines = block.split("\n", 1)
        header = lines[0]
        body = lines[1] if len(lines) > 1 else ""

        source_file: str | None = None
        if header.startswith("Source:"):
            raw_source = header[len("Source:") :].split(", chunk:", 1)[0].strip()
            source_file = Path(raw_source).name

        parsed.append((source_file, body))
    return parsed


def match_keywords(text: str, case: RagEvalCase) -> dict[str, list[Any]]:
    haystack = text.casefold()
    matched_all = [
        keyword
        for keyword in case.expected_keywords_all
        if keyword.casefold() in haystack
    ]
    missing_all = [
        keyword
        for keyword in case.expected_keywords_all
        if keyword.casefold() not in haystack
    ]
    matched_any = [
        keyword
        for keyword in case.expected_keywords_any
        if keyword.casefold() in haystack
    ]
    group_matches = [
        [keyword for keyword in group if keyword.casefold() in haystack]
        for group in case.expected_keyword_groups
    ]
    return {
        "matched_all": matched_all,
        "missing_all": missing_all,
        "matched_any": matched_any,
        "group_matches": group_matches,
    }


def should_exit_with_failure(
    results: list[QuestionResult],
    *,
    strict_keywords: bool,
) -> bool:
    structural_ok = all(
        result.retrieved and (not result.source_applicable or result.source_ok)
        for result in results
    )
    keyword_ok = all(result.keyword_ok for result in results)
    return not structural_ok or (strict_keywords and not keyword_ok)


def log_result(index: int, result: QuestionResult) -> None:
    case = result.case
    LOGGER.info("[%d] question: %s", index, case.question)
    LOGGER.info("    retrieved: %s", "yes" if result.retrieved else "no")
    if result.source_applicable:
        LOGGER.info("    expected source: %s", _expected_source_label(case))
        LOGGER.info(
            "    top source file: %s  (%s)",
            result.top_source or "(none)",
            "match" if result.source_ok else "MISMATCH",
        )
    else:
        LOGGER.info("    source check: skipped")
    _log_keyword_result(result)
    LOGGER.info("    chunk preview: %s", result.preview or "(none)")
    LOGGER.info("")


def _log_keyword_result(result: QuestionResult) -> None:
    case = result.case
    if case.expected_keywords_all:
        if result.all_ok:
            LOGGER.info("    keywords (all): PASS (%s)", ", ".join(result.matched_all))
        else:
            LOGGER.warning("    keywords (all): WARN missing %s", result.missing_all)
    if case.expected_keywords_any:
        if result.any_ok:
            LOGGER.info("    keywords (any): PASS (%s)", ", ".join(result.matched_any))
        else:
            LOGGER.warning(
                "    keywords (any): WARN none of %s matched",
                list(case.expected_keywords_any),
            )
    for number, group in enumerate(case.expected_keyword_groups, start=1):
        matched = (
            result.group_matches[number - 1]
            if number - 1 < len(result.group_matches)
            else []
        )
        if matched:
            LOGGER.info("    keyword group %d: PASS (%s)", number, ", ".join(matched))
        else:
            LOGGER.warning(
                "    keyword group %d: WARN none of %s matched", number, list(group)
            )


def log_summary(results: list[QuestionResult], *, strict_keywords: bool) -> None:
    total = len(results)
    with_context = sum(1 for result in results if result.retrieved)
    source_total = sum(1 for result in results if result.source_applicable)
    source_passed = sum(
        1 for result in results if result.source_applicable and result.source_ok
    )
    keyword_total = sum(1 for result in results if result.keyword_applicable)
    keyword_passed = sum(
        1 for result in results if result.keyword_applicable and result.keyword_ok
    )
    covered_sources = sorted(
        source
        for result in results
        for source in result.covered_sources
        if source is not None
    )

    LOGGER.info("=" * 60)
    LOGGER.info("Summary")
    LOGGER.info("=" * 60)
    LOGGER.info("total questions:           %d", total)
    LOGGER.info("questions with context:    %d / %d", with_context, total)
    LOGGER.info("source checks passed:      %d / %d", source_passed, source_total)
    LOGGER.info("keyword checks passed:     %d / %d", keyword_passed, keyword_total)
    LOGGER.info("covered sources:")
    for source in dict.fromkeys(covered_sources):
        LOGGER.info("    %s", source)

    failures = failed_case_details(results, strict_keywords=strict_keywords)
    if failures:
        LOGGER.warning("")
        LOGGER.warning("failed cases details:")
        for detail in failures:
            LOGGER.warning("    %s", detail)
        if not strict_keywords:
            LOGGER.warning(
                "keyword misses are warnings; add --strict-keywords to fail."
            )


def failed_case_details(
    results: list[QuestionResult],
    *,
    strict_keywords: bool,
) -> list[str]:
    details: list[str] = []
    for index, result in enumerate(results, start=1):
        if not result.retrieved:
            details.append(f"[{index}] no context: {result.case.question}")
            continue
        if result.source_applicable and not result.source_ok:
            details.append(
                f"[{index}] source mismatch: expected {_expected_source_label(result.case)}, "
                f"got {result.top_source or '(none)'}"
            )
        if result.keyword_applicable and not result.keyword_ok:
            label = "keyword failure" if strict_keywords else "keyword warning"
            details.append(f"[{index}] {label}: {result.case.question}")
    return details


def _expected_source_label(case: RagEvalCase) -> str:
    if case.expected_source is not None:
        return case.expected_source
    if case.expected_source_contains is not None:
        return f"*{case.expected_source_contains}*"
    return "(none)"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = parse_args()

    persist_path = Path(args.persist_dir)
    if not persist_path.exists():
        LOGGER.error("Chroma index not found at: %s", persist_path)
        LOGGER.error("Build it first with devmate.index_docs.")
        raise SystemExit(1)

    try:
        cases = load_eval_cases(args.eval_cases)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        LOGGER.error("Could not load eval cases from %s: %s", args.eval_cases, exc)
        raise SystemExit(1) from exc

    config = load_config(args.config)
    LOGGER.info(
        "Running RAG-only retrieval evaluation (cases=%s, k=%d, persist_dir=%s)",
        args.eval_cases,
        args.k,
        args.persist_dir,
    )
    LOGGER.info("config: %s", args.config)
    LOGGER.info("strict keywords: %s", "yes" if args.strict_keywords else "no")
    LOGGER.info("=" * 60)
    LOGGER.info("")

    results: list[QuestionResult] = []
    for index, case in enumerate(cases, start=1):
        result = run_question(case, config, args.persist_dir, args.k)
        results.append(result)
        log_result(index, result)

    log_summary(results, strict_keywords=args.strict_keywords)
    if should_exit_with_failure(results, strict_keywords=args.strict_keywords):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
