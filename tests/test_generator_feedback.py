"""
Unit test verifying that the retry loop passes the judge's exact failure reasons,
evidence quotes, and fix suggestions into the generator's subsequent prompt at the boundary.
"""

from typing import Optional, Dict, Any, List
from agents.generator import GeneratorAgent


class MockRecordingLLMClient:
    """Records prompts sent to it at the network boundary."""
    def __init__(self):
        self.recorded_prompts: List[str] = []
        self.api_call_count = 0
        self.is_mock = True

    def generate_text(self, prompt: str, system_instruction: Optional[str] = None, **kwargs) -> str:
        self.api_call_count += 1
        self.recorded_prompts.append(prompt)
        return "# Revised Lesson\n\nFixed content based on feedback."

    def generate_json(self, *args, **kwargs) -> Dict[str, Any]:
        return {}


def test_generator_receives_failed_check_reasons_and_evidence():
    """
    Verifies that on retry (attempt > 1), the generator's prompt contains:
    1. The exact failed check IDs
    2. The exact failure reason from the judge
    3. The exact evidence quote
    4. The exact fix suggestion
    """
    mock_llm = MockRecordingLLMClient()
    generator = GeneratorAgent(llm_client=mock_llm)

    spec = {"topic": "Introduction to RAG", "must_cover_concepts": []}
    previous_lesson = "# Draft 1\nSome imperfect text."
    failed_checks = [
        {
            "id": "A2",
            "name": "Grounding Integrity",
            "reason": "Claims RAG retrains neural weights on every query.",
            "evidence": "retrains neural weights",
            "fix_suggestion": "Clarify that model weights are never changed."
        },
        {
            "id": "B1",
            "name": "Average Sentence Length <= 15 Words",
            "reason": "Average sentence length is 19.4 words, exceeding 15 words limit.",
            "evidence": "Very long convoluted sentence...",
            "fix_suggestion": "Break long sentences into shorter clauses."
        }
    ]

    # Trigger generation for Attempt 2
    revised = generator.generate(
        lesson_spec=spec,
        attempt_number=2,
        previous_lesson=previous_lesson,
        failed_checks=failed_checks
    )

    assert len(mock_llm.recorded_prompts) == 1
    sent_prompt = mock_llm.recorded_prompts[0]

    # Verify previous draft was provided
    assert previous_lesson in sent_prompt

    # Verify check A2 details were passed into the prompt
    assert "[A2 - Grounding Integrity]" in sent_prompt
    assert "Claims RAG retrains neural weights on every query." in sent_prompt
    assert 'Evidence from text: "retrains neural weights"' in sent_prompt
    assert "Clarify that model weights are never changed." in sent_prompt

    # Verify check B1 details were passed into the prompt
    assert "[B1 - Average Sentence Length <= 15 Words]" in sent_prompt
    assert "Average sentence length is 19.4 words" in sent_prompt
    assert "Break long sentences into shorter clauses." in sent_prompt
