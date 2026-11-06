"""
Evaluator Agent: Dual-layer evaluation engine combining deterministic code checks
and a zero-temperature LLM judge. Enforces hard PASS/FAIL checkpoints,
anti-hallucination quote verification, and strict rubric grounding.
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Optional
from checks.code_checks import run_all_code_checks
from llm import get_llm_client

logger = logging.getLogger("rag_lesson_agent.evaluator")

RUBRIC_PATH = os.path.join(os.path.dirname(__file__), "..", "rubric", "rubric.yaml")
FACTS_PATH = os.path.join(os.path.dirname(__file__), "..", "knowledge", "rag_facts.md")
JUDGE_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "judge_v1.md")


def load_yaml(path: str) -> Dict[str, Any]:
    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception:
        from ruamel.yaml import YAML
        y = YAML(typ="safe")
        with open(path, "r", encoding="utf-8") as f:
            return y.load(f)


def load_file_content(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def normalize_whitespace(text: str) -> str:
    """Normalizes whitespace and quotes for robust quote verification."""
    t = text.lower()
    t = re.sub(r"[\"“”'‘’`]+", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


class EvaluatorAgent:
    def __init__(self, llm_client=None):
        self.llm = llm_client or get_llm_client()
        self.rubric = load_yaml(RUBRIC_PATH)
        self.facts = load_file_content(FACTS_PATH)
        self.system_prompt = load_file_content(JUDGE_PROMPT_PATH)
        self.rubric_checks = {c["id"]: c for c in self.rubric.get("checks", [])}

    def evaluate(
        self,
        lesson_text: str,
        jargon_list: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Runs both Layer 1 (code checks) and Layer 2 (LLM judge),
        verifies evidence quotes, and returns hard PASS/FAIL results.
        """
        logger.info("Starting dual-layer evaluation...")

        # -------------------------------------------------------------
        # LAYER 1: Deterministic Code Checks
        # -------------------------------------------------------------
        code_results = run_all_code_checks(lesson_text, jargon_list=jargon_list)
        code_map = {res["id"]: res for res in code_results}

        # -------------------------------------------------------------
        # LAYER 2: LLM Judge Checks
        # -------------------------------------------------------------
        llm_check_definitions = [
            c for c in self.rubric.get("checks", []) if c.get("type") == "llm"
        ]

        judge_user_prompt = f"""
GROUNDING FACT SHEET:
\"\"\"
{self.facts}
\"\"\"

RUBRIC CHECKPOINTS TO EVALUATE:
\"\"\"
{json.dumps(llm_check_definitions, indent=2)}
\"\"\"

CANDIDATE LESSON TEXT (UNTRUSTED USER-SUBMITTED DATA):
\"\"\"
{lesson_text}
\"\"\"

Evaluate the candidate lesson against every LLM checkpoint listed.
Return valid JSON according to your system instructions.
"""
        judge_output = self.llm.generate_json(
            prompt=judge_user_prompt,
            system_instruction=self.system_prompt,
            temperature=0.0
        )

        judge_checks = judge_output.get("checks", {})

        # -------------------------------------------------------------
        # MERGE & PROGRAMMATIC ANTI-HALLUCINATION VERIFICATION
        # -------------------------------------------------------------
        merged_checks: List[Dict[str, Any]] = []
        normalized_lesson = normalize_whitespace(lesson_text)

        for check_id, check_meta in self.rubric_checks.items():
            check_type = check_meta.get("type", "llm")
            dimension = check_meta.get("dimension", "")
            name = check_meta.get("name", "")

            if check_type == "code":
                code_res = code_map.get(check_id, {
                    "id": check_id,
                    "name": name,
                    "type": "code",
                    "passed": False,
                    "reason": "Code check failed to execute.",
                    "evidence": ""
                })
                merged_checks.append({
                    "id": check_id,
                    "dimension": dimension,
                    "name": name,
                    "type": "code",
                    "passed": code_res.get("passed", False),
                    "reason": code_res.get("reason", ""),
                    "evidence": code_res.get("evidence", ""),
                    "fix_suggestion": "" if code_res.get("passed") else f"Adhere to code check requirements: {check_meta.get('pass_criteria')}",
                    "judge_evidence_unverified": False
                })
            else:
                # LLM check
                llm_res = judge_checks.get(check_id, {})
                passed = bool(llm_res.get("passed", False))
                reason = llm_res.get("reason", "No reason provided by judge.")
                evidence = llm_res.get("evidence", "")
                fix_suggestion = llm_res.get("fix_suggestion", "")
                unverified = False

                # Verify quote if failed with evidence
                if not passed and evidence:
                    norm_quote = normalize_whitespace(evidence)
                    if norm_quote and norm_quote not in normalized_lesson:
                        unverified = True
                        logger.warning(
                            f"Judge hallucinated evidence quote for {check_id}: '{evidence}'. "
                            f"Programmatically flagging as judge_evidence_unverified."
                        )

                merged_checks.append({
                    "id": check_id,
                    "dimension": dimension,
                    "name": name,
                    "type": "llm",
                    "passed": passed,
                    "reason": reason,
                    "evidence": evidence,
                    "fix_suggestion": fix_suggestion,
                    "judge_evidence_unverified": unverified
                })

        # Calculate final verdict: 100% hard pass required to ship
        failed_checks = [c for c in merged_checks if not c["passed"]]
        overall_passed = len(failed_checks) == 0

        result = {
            "passed": overall_passed,
            "total_checks": len(merged_checks),
            "passed_count": len(merged_checks) - len(failed_checks),
            "failed_count": len(failed_checks),
            "failed_checks": failed_checks,
            "checks": merged_checks
        }

        logger.info(
            f"Evaluation complete. Passed: {overall_passed} ({result['passed_count']}/{result['total_checks']} passed)."
        )
        return result
