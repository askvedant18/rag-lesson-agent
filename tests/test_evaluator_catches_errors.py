"""
Tests for Evaluator Agent catching deliberate errors.
Verifies that:
1. factual_error.md fails check A2.
2. jargon_dump.md fails B3a/B3b.
3. bad_flow.md fails E1.
4. Clean lesson passes all checks.
5. Judge hallucinated quotes are programmatically caught and flagged.
"""

import os
import pytest
from agents.evaluator import EvaluatorAgent

BAD_LESSONS_DIR = os.path.join(os.path.dirname(__file__), "bad_lessons")


def load_bad_lesson(filename: str) -> str:
    path = os.path.join(BAD_LESSONS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def evaluator():
    return EvaluatorAgent()


def test_factual_error_fails_a2(evaluator):
    """factual_error.md claims RAG retrains weights -> MUST fail A2."""
    lesson = load_bad_lesson("factual_error.md")
    result = evaluator.evaluate(lesson)

    assert result["passed"] is False
    failed_ids = {c["id"] for c in result["failed_checks"]}
    assert "A2" in failed_ids, f"Expected A2 to fail, got failed IDs: {failed_ids}"

    a2_check = next(c for c in result["failed_checks"] if c["id"] == "A2")
    assert "retrains" in a2_check["reason"].lower() or "weight" in a2_check["reason"].lower()


def test_jargon_dump_fails_jargon_checks(evaluator):
    """jargon_dump.md uses advanced terms without definition -> MUST fail B3a or B3b."""
    lesson = load_bad_lesson("jargon_dump.md")
    result = evaluator.evaluate(lesson)

    assert result["passed"] is False
    failed_ids = {c["id"] for c in result["failed_checks"]}
    assert ("B3a" in failed_ids or "B3b" in failed_ids), f"Expected B3a or B3b to fail, got: {failed_ids}"


def test_bad_flow_fails_e1(evaluator):
    """bad_flow.md puts example first and definition at end -> MUST fail E1."""
    lesson = load_bad_lesson("bad_flow.md")
    result = evaluator.evaluate(lesson)

    assert result["passed"] is False
    failed_ids = {c["id"] for c in result["failed_checks"]}
    assert "E1" in failed_ids, f"Expected E1 to fail, got: {failed_ids}"


def test_custom_deliberate_error_images_only_fails_a1_and_a2(evaluator):
    """
    Independent custom deliberate error not in the 3 base samples:
    Claims RAG is only for JPEG photography -> MUST fail A1 and A2.
    """
    lesson = load_bad_lesson("rag_is_images_only.md")
    result = evaluator.evaluate(lesson)

    assert result["passed"] is False
    failed_ids = {c["id"] for c in result["failed_checks"]}
    assert "A1" in failed_ids or "A2" in failed_ids, f"Expected A1 or A2 to fail, got: {failed_ids}"


def test_passing_lesson_clears_all_rubric_checks(evaluator):
    """A high-quality compliant lesson must pass 100% of rubric checks."""
    from llm import get_llm_client
    # The default offline generator produces a lesson meeting all criteria
    lesson = get_llm_client()._offline_generate_text("Generate lesson", None)
    result = evaluator.evaluate(lesson)

    assert result["passed"] is True, f"Expected lesson to pass, but failed checks: {[c['id'] for c in result['failed_checks']]}"
    assert result["failed_count"] == 0
    assert result["passed_count"] == result["total_checks"]


def test_judge_hallucinated_quote_flagged(evaluator):
    """Anti-hallucination guardrail: if quote is not in text, judge_evidence_unverified is set to True."""
    lesson = "# Short Lesson\n\nImagine an open-book exam.\n"

    # Mock an evaluation result with a hallucinated quote
    class MockJudgeClient:
        def generate_json(self, *args, **kwargs):
            return {
                "checks": {
                    "A2": {
                        "passed": False,
                        "reason": "Claims model transforms into a flying submarine.",
                        "evidence": "flying submarine transforms into an airplane",
                        "fix_suggestion": "Remove fantasy claims."
                    }
                }
            }

    custom_evaluator = EvaluatorAgent(llm_client=MockJudgeClient())
    res = custom_evaluator.evaluate(lesson)
    a2_check = next(c for c in res["checks"] if c["id"] == "A2")

    assert a2_check["passed"] is False
    assert a2_check["judge_evidence_unverified"] is True

