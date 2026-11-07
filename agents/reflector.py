"""
Reflector Agent & Memory Manager:
Tracks persistent failure statistics across runs and synthesizes new generator rules
when failure thresholds are reached. Strictly guards the evaluator from self-modification.
"""

import os
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from llm import get_llm_client

logger = logging.getLogger("rag_lesson_agent.reflector")

MEMORY_DIR = os.path.join(os.path.dirname(__file__), "..", "memory")
FAILURE_STATS_PATH = os.path.join(MEMORY_DIR, "failure_stats.json")
LEARNED_RULES_PATH = os.path.join(MEMORY_DIR, "learned_rules.json")
PROPOSED_RUBRIC_PATH = os.path.join(MEMORY_DIR, "proposed_rubric_changes.json")


def atomic_write_json(file_path: str, data: Any):
    """Safely writes JSON data atomically using a temporary file and os.replace."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    temp_file = f"{file_path}.tmp.{uuid.uuid4().hex}"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(temp_file, file_path)


def atomic_read_json(file_path: str, default: Any) -> Any:
    """Reads JSON safely, returning default if file doesn't exist or is invalid."""
    if not os.path.exists(file_path):
        return default
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Error reading {file_path}: {e}. Returning default.")
        return default


class ReflectorAgent:
    def __init__(self, failure_threshold: Optional[int] = None, llm_client=None):
        env_threshold = int(os.getenv("FAILURE_THRESHOLD", "2"))
        self.failure_threshold = failure_threshold if failure_threshold is not None else env_threshold
        self.llm = llm_client or get_llm_client()

    def record_run(
        self,
        attempts: int,
        passed: bool,
        all_failed_check_ids: List[str],
        source: str = "generator"
    ) -> Dict[str, Any]:
        """
        Updates persistent memory stats after a run completes.
        """
        stats = atomic_read_json(FAILURE_STATS_PATH, {
            "total_runs": 0,
            "successful_runs": 0,
            "human_review_runs": 0,
            "attempts_history": [],
            "check_failures": {}
        })

        stats["total_runs"] = stats.get("total_runs", 0) + 1
        if passed:
            stats["successful_runs"] = stats.get("successful_runs", 0) + 1
        else:
            stats["human_review_runs"] = stats.get("human_review_runs", 0) + 1

        history = stats.get("attempts_history", [])
        history.append(attempts)
        stats["attempts_history"] = history[-100:]  # Keep last 100

        check_failures = stats.get("check_failures", {})
        for cid in all_failed_check_ids:
            check_failures[cid] = check_failures.get(cid, 0) + 1
        stats["check_failures"] = check_failures

        atomic_write_json(FAILURE_STATS_PATH, stats)
        logger.info(f"Recorded run in memory: Run #{stats['total_runs']}, Status={'PASS' if passed else 'REVIEW'}")

        # Check if any failure crossed the threshold for auto-learning (strictly for generator errors)
        if source == "generator":
            self._check_and_synthesize_rules(check_failures)
        return stats

    def _check_and_synthesize_rules(self, check_failures: Dict[str, int]):
        """
        Analyzes check failure counts and proposes targeted rules for frequent failures.
        """
        learned_rules = atomic_read_json(LEARNED_RULES_PATH, [])
        existing_rule_sources = {r.get("created_from_check") for r in learned_rules if "created_from_check" in r}

        for check_id, count in check_failures.items():
            if count >= self.failure_threshold and check_id not in existing_rule_sources:
                logger.info(
                    f"Check {check_id} failed {count} times (>= threshold {self.failure_threshold}). "
                    f"Synthesizing new generator rule..."
                )
                self._propose_rule_for_check(check_id, count, learned_rules)

    def _propose_rule_for_check(self, check_id: str, count: int, existing_rules: List[Dict[str, Any]]):
        """
        Queries the LLM for a single concise rule to prevent this check failure in future generations.
        """
        prompt = f"""
The lesson generator has failed rubric check '{check_id}' {count} times across previous runs.
Propose ONE concise, actionable generator rule (maximum 25 words) that instructs the lesson generator
how to strictly avoid failing check '{check_id}' in future drafts.

Return valid JSON with:
{{
  "rule_proposal": "Concise imperative instruction for generator",
  "target_check": "{check_id}",
  "rubric_feedback": null
}}
"""
        response = self.llm.generate_json(
            prompt=prompt,
            system_instruction="You are a meta-learning curriculum reflector. Propose tight, effective rules for AI generation.",
            temperature=0.0
        )

        rule_text = response.get("rule_proposal")
        if rule_text:
            new_rule = {
                "id": f"RULE-{len(existing_rules) + 1:03d}",
                "rule_text": rule_text.strip(),
                "created_from_check": check_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "times_used": 0,
                "approved": True
            }
            existing_rules.append(new_rule)
            atomic_write_json(LEARNED_RULES_PATH, existing_rules)
            logger.info(f"Adopted new learned rule: [{new_rule['id']}] {new_rule['rule_text']}")

        # IMPORTANT GUARDRAIL: Rubric feedback is strictly logged for human review only.
        rubric_feedback = response.get("rubric_feedback")
        if rubric_feedback:
            self.propose_rubric_change(
                check_id=check_id,
                proposal=rubric_feedback,
                reason="Reflector flagged potential ambiguity during failure analysis"
            )

    def propose_rubric_change(self, check_id: str, proposal: str, reason: str):
        """
        CRITICAL GUARDRAIL: Rubric changes CANNOT be executed autonomously by the AI.
        Any proposed changes to the rubric or judge prompts are quarantined into
        memory/proposed_rubric_changes.json for human review and approval.
        """
        proposals = atomic_read_json(PROPOSED_RUBRIC_PATH, [])
        proposal_entry = {
            "id": f"PR-{len(proposals) + 1:03d}",
            "check_id": check_id,
            "proposal": proposal,
            "reason": reason,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending_human_review"
        }
        proposals.append(proposal_entry)
        atomic_write_json(PROPOSED_RUBRIC_PATH, proposals)
        logger.warning(
            f"GUARDRAIL: Proposed rubric change for {check_id} quarantined in memory for human review: {proposal}"
        )

