"""
Planner Agent: Analyzes the topic, references the grounding facts,
and generates a structured lesson specification tailored for the learner profile.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from llm import get_llm_client

logger = logging.getLogger("rag_lesson_agent.planner")

PLANNER_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "planner_v1.md")
FACTS_PATH = os.path.join(os.path.dirname(__file__), "..", "knowledge", "rag_facts.md")
OUTPUT_SPEC_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "lesson_spec.json")


def load_file_content(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class PlannerAgent:
    def __init__(self, llm_client=None):
        self.llm = llm_client or get_llm_client()
        self.system_prompt = load_file_content(PLANNER_PROMPT_PATH)
        self.facts = load_file_content(FACTS_PATH)

    def plan_lesson(self, topic: str = "Introduction to RAG (Retrieval-Augmented Generation)") -> Dict[str, Any]:
        """
        Generates a comprehensive lesson specification for the given topic.
        """
        logger.info(f"Planning curriculum for topic: {topic}")

        user_prompt = f"""
Grounding Fact Sheet:
\"\"\"
{self.facts}
\"\"\"

Topic to plan:
\"\"\"
{topic}
\"\"\"

Produce the complete JSON lesson specification following the schema instructions.
"""
        spec = self.llm.generate_json(
            prompt=user_prompt,
            system_instruction=self.system_prompt,
            temperature=0.0
        )

        # Fallback defaults if any key missing
        if "topic" not in spec:
            spec["topic"] = topic
        if "jargon_list" not in spec:
            spec["jargon_list"] = [
                "llm", "large language model", "embedding", "vector",
                "chunk", "retrieval", "hallucination", "knowledge base",
                "prompt", "vector database"
            ]

        # Persist spec to output directory
        os.makedirs(os.path.dirname(OUTPUT_SPEC_PATH), exist_ok=True)
        with open(OUTPUT_SPEC_PATH, "w", encoding="utf-8") as f:
            json.dump(spec, f, indent=2)

        logger.info(f"Lesson plan generated successfully with {len(spec.get('must_cover_concepts', []))} key concepts.")
        return spec

