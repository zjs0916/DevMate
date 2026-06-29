from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


def _load_eval_module() -> ModuleType:
    script_path = (
        Path(__file__).resolve().parents[1] / "scripts" / "test_rag_retrieval.py"
    )
    spec = importlib.util.spec_from_file_location("test_rag_retrieval", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {script_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


rag_eval = _load_eval_module()


def test_eval_cases_parsing(tmp_path: Path) -> None:
    path = tmp_path / "eval_cases.json"
    path.write_text(
        json.dumps(
            [
                {
                    "question": "What is alpha?",
                    "expected_source": "alpha.txt",
                    "expected_keywords_all": ["alpha"],
                    "expected_keywords_any": ["first", "primary"],
                    "expected_keyword_groups": [["one", "1"], ["two"]],
                }
            ]
        ),
        encoding="utf-8",
    )

    [case] = rag_eval.load_eval_cases(path)

    assert case.question == "What is alpha?"
    assert case.expected_source == "alpha.txt"
    assert case.expected_keywords_all == ("alpha",)
    assert case.expected_keywords_any == ("first", "primary")
    assert case.expected_keyword_groups == (("one", "1"), ("two",))


def test_keyword_groups_are_and_of_ors() -> None:
    case = rag_eval.RagEvalCase(
        question="q",
        expected_keyword_groups=(("green bottle", "vial"), ("herbs", "medicine")),
    )
    matches = rag_eval.match_keywords(
        "The vial helps mature herbs quickly.",
        case,
    )

    result = rag_eval.QuestionResult(
        case=case,
        retrieved=True,
        top_source="source.txt",
        preview="",
        group_matches=matches["group_matches"],
    )

    assert result.groups_ok


def test_expected_source_contains_matches_top_source_filename() -> None:
    case = rag_eval.RagEvalCase(
        question="q",
        expected_source_contains="Reference",
    )
    result = rag_eval.QuestionResult(
        case=case,
        retrieved=True,
        top_source="Rules Reference.txt",
        preview="",
    )

    assert result.source_ok


def test_strict_vs_non_strict_keyword_exit_behavior() -> None:
    case = rag_eval.RagEvalCase(
        question="q",
        expected_source="source.txt",
        expected_keywords_all=("missing",),
    )
    result = rag_eval.QuestionResult(
        case=case,
        retrieved=True,
        top_source="source.txt",
        preview="",
        missing_all=["missing"],
    )

    assert not rag_eval.should_exit_with_failure([result], strict_keywords=False)
    assert rag_eval.should_exit_with_failure([result], strict_keywords=True)


def test_source_mismatch_fails_even_without_strict_keywords() -> None:
    case = rag_eval.RagEvalCase(question="q", expected_source="expected.txt")
    result = rag_eval.QuestionResult(
        case=case,
        retrieved=True,
        top_source="other.txt",
        preview="",
    )

    assert rag_eval.should_exit_with_failure([result], strict_keywords=False)
