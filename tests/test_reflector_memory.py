"""
Tests for the Reflector's memory and the human review of learned rules.
Verifies that:
1. Failures from injected demo lessons never trigger a learned rule.
2. A rule synthesized from real generator failures starts as pending.
3. The generator ignores pending and rejected rules and uses approved ones.
4. A rejected rule does not block a new proposal for the same check.
All memory files are redirected to a temporary folder, so the real memory/ is never touched.
"""

import json
import pytest

import agents.reflector as reflector
import agents.generator as generator
from agents.reflector import (
    ReflectorAgent,
    rule_status,
    set_rule_status,
    RULE_APPROVED,
    RULE_PENDING,
    RULE_REJECTED,
)
from agents.generator import GeneratorAgent


@pytest.fixture
def memory(tmp_path, monkeypatch):
    rules_path = tmp_path / "learned_rules.json"
    monkeypatch.setattr(reflector, "FAILURE_STATS_PATH", str(tmp_path / "failure_stats.json"))
    monkeypatch.setattr(reflector, "LEARNED_RULES_PATH", str(rules_path))
    monkeypatch.setattr(reflector, "PROPOSED_RUBRIC_PATH", str(tmp_path / "proposed_rubric_changes.json"))
    monkeypatch.setattr(generator, "LEARNED_RULES_PATH", str(rules_path))
    monkeypatch.setattr(generator, "ATTEMPTS_DIR", str(tmp_path / "attempts"))
    return tmp_path


def read_rules(memory):
    path = memory / "learned_rules.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


class CapturingLLM:
    """Stands in for the LLM client and records the generator's prompt."""

    is_mock = True
    api_call_count = 0

    def __init__(self):
        self.prompts = []

    def generate_text(self, prompt, system_instruction=None, temperature=0.7, **kwargs):
        self.prompts.append(prompt)
        return "# Lesson"


def test_injected_failures_never_create_rules(memory):
    agent = ReflectorAgent(failure_threshold=2)
    for _ in range(3):
        agent.record_run(attempts=2, passed=True, all_failed_check_ids=["A2", "D2"], source="injected_test")

    # A normal generator run afterwards must not turn the demo failures into rules.
    stats = agent.record_run(attempts=1, passed=True, all_failed_check_ids=[], source="generator")

    assert stats["check_failures"] == {"A2": 3, "D2": 3}
    assert stats["generator_check_failures"] == {}
    assert read_rules(memory) == []


def test_generator_failures_create_a_pending_rule(memory):
    agent = ReflectorAgent(failure_threshold=2)
    agent.record_run(attempts=2, passed=True, all_failed_check_ids=["E2a"], source="generator")
    agent.record_run(attempts=2, passed=True, all_failed_check_ids=["E2a"], source="generator")

    rules = read_rules(memory)
    assert len(rules) == 1
    assert rules[0]["created_from_check"] == "E2a"
    assert rules[0]["approved"] is False
    assert rule_status(rules[0]) == RULE_PENDING


def test_generator_uses_only_approved_rules(memory):
    (memory / "learned_rules.json").write_text(json.dumps([
        {"id": "RULE-001", "rule_text": "REJECTED RULE TEXT", "created_from_check": "E2a",
         "approved": False, "rejection_reason": "too vague"},
        {"id": "RULE-002", "rule_text": "PENDING RULE TEXT", "created_from_check": "B2",
         "approved": False, "status": RULE_PENDING},
    ]), encoding="utf-8")

    llm = CapturingLLM()
    GeneratorAgent(llm_client=llm).generate(lesson_spec={"topic": "RAG"})
    assert "PENDING RULE TEXT" not in llm.prompts[-1]
    assert "REJECTED RULE TEXT" not in llm.prompts[-1]

    set_rule_status("RULE-002", approve=True)
    GeneratorAgent(llm_client=llm).generate(lesson_spec={"topic": "RAG"})
    assert "PENDING RULE TEXT" in llm.prompts[-1]
    assert "REJECTED RULE TEXT" not in llm.prompts[-1]


def test_reject_records_reason_and_unknown_id_fails(memory):
    (memory / "learned_rules.json").write_text(json.dumps([
        {"id": "RULE-001", "rule_text": "x", "created_from_check": "B2", "approved": False, "status": RULE_PENDING},
    ]), encoding="utf-8")

    rule = set_rule_status("RULE-001", approve=False, reason="Not measurable")
    assert rule_status(rule) == RULE_REJECTED
    assert read_rules(memory)[0]["rejection_reason"] == "Not measurable"

    with pytest.raises(ValueError):
        set_rule_status("RULE-999", approve=True)


def test_rejected_rule_does_not_block_a_new_proposal(memory):
    # Same shape as the real RULE-001 in memory/learned_rules.json.
    (memory / "learned_rules.json").write_text(json.dumps([
        {"id": "RULE-001", "rule_text": "too vague", "created_from_check": "E2a",
         "approved": False, "rejection_reason": "too vague"},
    ]), encoding="utf-8")

    agent = ReflectorAgent(failure_threshold=2)
    agent.record_run(attempts=2, passed=True, all_failed_check_ids=["E2a"], source="generator")
    agent.record_run(attempts=2, passed=True, all_failed_check_ids=["E2a"], source="generator")

    rules = read_rules(memory)
    assert [rule_status(r) for r in rules] == [RULE_REJECTED, RULE_PENDING]

    # A pending rule does block a duplicate proposal for the same check.
    agent.record_run(attempts=2, passed=True, all_failed_check_ids=["E2a"], source="generator")
    assert len(read_rules(memory)) == 2


def test_legacy_rules_keep_their_meaning():
    assert rule_status({"rule_text": "old rule without flags"}) == RULE_APPROVED
    assert rule_status({"approved": True}) == RULE_APPROVED
    assert rule_status({"approved": False}) == RULE_PENDING
    assert rule_status({"approved": False, "rejection_reason": "no"}) == RULE_REJECTED


def test_main_module_defines_logger():
    # main.py used `logger` on the no-progress path without defining it.
    import main
    assert main.logger.name == "rag_lesson_agent.main"
