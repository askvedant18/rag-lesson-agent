"""
Generator Agent: Drafts and refines the lesson content in simple English.
Implements targeted regeneration based on evaluator feedback and injects
accumulated learned rules into prompts with semantic prompt versioning.
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Optional
from llm import get_llm_client

logger = logging.getLogger("rag_lesson_agent.generator")

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")
MEMORY_DIR = os.path.join(os.path.dirname(__file__), "..", "memory")
ATTEMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "output", "attempts")
LEARNED_RULES_PATH = os.path.join(MEMORY_DIR, "learned_rules.json")


def load_file_content(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_learned_rules() -> List[Dict[str, Any]]:
    if not os.path.exists(LEARNED_RULES_PATH):
        return []
    try:
        with open(LEARNED_RULES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


class GeneratorAgent:
    def __init__(self, llm_client=None):
        self.llm = llm_client or get_llm_client()
        self.prompt_version = "generator_v1"
        self._ensure_prompt_version()

    def _ensure_prompt_version(self):
        """
        Determines current generator prompt version based on stored learned rules.
        If rules exist that aren't baked into base v1, updates or logs prompt version.
        """
        rules = load_learned_rules()
        active_rules = [r for r in rules if r.get("approved", True)]
        if len(active_rules) > 0:
            self.prompt_version = f"generator_v{1 + (len(active_rules) // 3)}"
            # Ensure versioned prompt file exists
            version_path = os.path.join(PROMPTS_DIR, f"{self.prompt_version}.md")
            if not os.path.exists(version_path):
                base_content = load_file_content(os.path.join(PROMPTS_DIR, "generator_v1.md"))
                rules_block = "\n\n## Dynamically Injected Learned Rules\n" + "\n".join(
                    f"- [{r.get('id', 'R')}] {r.get('rule_text')}" for r in active_rules
                )
                with open(version_path, "w", encoding="utf-8") as f:
                    f.write(base_content + rules_block)
        else:
            self.prompt_version = "generator_v1"

    def generate(
        self,
        lesson_spec: Dict[str, Any],
        attempt_number: int = 1,
        previous_lesson: Optional[str] = None,
        failed_checks: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Generates or regenerates a lesson.
        """
        os.makedirs(ATTEMPTS_DIR, exist_ok=True)
        self._ensure_prompt_version()

        rules = load_learned_rules()
        active_rules = [r for r in rules if r.get("approved", True)]
        rules_text = "\n".join(f"- {r.get('rule_text')}" for r in active_rules) if active_rules else "None yet."

        base_system_prompt = load_file_content(os.path.join(PROMPTS_DIR, "generator_v1.md"))

        if attempt_number == 1 or not previous_lesson:
            logger.info(f"Generating initial lesson draft (Attempt {attempt_number})...")
            user_prompt = f"""
Lesson Specification:
\"\"\"
{json.dumps(lesson_spec, indent=2)}
\"\"\"

Active Rules from System Memory:
\"\"\"
{rules_text}
\"\"\"

Write the complete beginner lesson now in Markdown.
Follow all word count, sentence length, and vocabulary constraints strictly.
"""
        else:
            logger.info(f"Regenerating lesson (Attempt {attempt_number}) targeting {len(failed_checks or [])} failed check(s)...")
            failures_summary = []
            for fc in (failed_checks or []):
                snippet = f"- Check [{fc.get('id')} - {fc.get('name')}]: {fc.get('reason')}"
                if fc.get("evidence"):
                    snippet += f"\n  Evidence from text: \"{fc.get('evidence')}\""
                if fc.get("fix_suggestion"):
                    snippet += f"\n  Suggested Fix: {fc.get('fix_suggestion')}"
                failures_summary.append(snippet)

            failures_formatted = "\n".join(failures_summary)

            user_prompt = f"""
PREVIOUS LESSON DRAFT:
\"\"\"
{previous_lesson}
\"\"\"

THE FOLLOWING EVALUATION CHECKS FAILED:
\"\"\"
{failures_formatted}
\"\"\"

ACTIVE SYSTEM RULES TO ENFORCE:
\"\"\"
{rules_text}
\"\"\"

TASK:
Rewrite the lesson to fix ONLY the failed checks above.
Preserve all sections and facts that already passed.
Ensure sentence length average remains <= 15 words and max sentence <= 25 words.
Return the complete revised lesson in Markdown.
"""

        lesson_markdown = self.llm.generate_text(
            prompt=user_prompt,
            system_instruction=base_system_prompt,
            temperature=0.7
        )

        # Clean markdown formatting if model output wrapped in ```markdown
        cleaned = lesson_markdown.strip()
        if cleaned.startswith("```markdown"):
            cleaned = cleaned[11:].strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:].strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

        # Save this attempt to output/attempts/attempt_N.md
        attempt_file = os.path.join(ATTEMPTS_DIR, f"attempt_{attempt_number}.md")
        with open(attempt_file, "w", encoding="utf-8") as f:
            f.write(cleaned)

        logger.info(f"Attempt {attempt_number} saved to {attempt_file}")
        return cleaned

    def explain_changes(
        self,
        previous_lesson: str,
        new_lesson: str,
        failed_checks: List[Dict[str, Any]]
    ) -> str:
        """
        Asks LLM to explain what changed on retry in 2-3 plain sentences against the failed checks.
        Detects if no progress was made between drafts.
        """
        if previous_lesson.strip() == new_lesson.strip():
            logger.warning("No progress: regenerated lesson is character-for-character identical.")
            return "No progress made: regenerated draft is identical to previous attempt."

        check_summaries = [
            f"Check [{c.get('id')}]: {c.get('name', '')} (Reason: {c.get('reason', '')})"
            for c in failed_checks
        ]
        checks_text = "\n".join(check_summaries)

        prompt = f"""
Compare the previous lesson against the new lesson regarding these failed checks:
{checks_text}

In 2-3 plain sentences, summarize exactly what changed in the new lesson to resolve the failed checks above.
Be specific about what was added, removed, or rewritten.

PREVIOUS LESSON:
\"\"\"
{previous_lesson}
\"\"\"

NEW LESSON:
\"\"\"
{new_lesson}
\"\"\"
"""
        explanation = self.llm.generate_text(prompt=prompt, temperature=0.2)
        return explanation.strip()

