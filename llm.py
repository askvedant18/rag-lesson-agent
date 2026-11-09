"""
LLM abstraction layer using the official google-genai SDK.
Handles authentication, exponential backoff retries, JSON mode enforcement,
temperature control, secret redaction, and an offline mock fallback for hermetic testing.
"""

import os
import re
import json
import time
import logging
from typing import Any, Dict, List, Optional, Type
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables
load_dotenv()

logger = logging.getLogger("rag_lesson_agent.llm")

# Model configuration from environment
DEFAULT_GENERATOR_MODEL = os.getenv("GENERATOR_MODEL", "gemini-3.8-flash")
DEFAULT_JUDGE_MODEL = os.getenv("JUDGE_MODEL", "gemini-3.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# Priority cascade pool of active Gemini models
AVAILABLE_FALLBACK_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
]


def _get_model_candidates(requested_model: Optional[str], default_model: str) -> List[str]:
    """Builds an ordered list of candidate models starting with the target model."""
    target = requested_model or default_model
    candidates = [target]
    for m in AVAILABLE_FALLBACK_MODELS:
        if m != target and m not in candidates:
            candidates.append(m)
    return candidates


def redact_secrets(text: str) -> str:
    """Removes sensitive API key patterns from strings before logging or raising."""
    if not text:
        return text
    # Standard Google AI Studio API key pattern is AIza...
    redacted = re.sub(r"AIza[0-9A-Za-z_\-]{30,45}", "[REDACTED_GEMINI_KEY]", text)
    if GEMINI_API_KEY and len(GEMINI_API_KEY) > 6:
        redacted = redacted.replace(GEMINI_API_KEY, "[REDACTED_GEMINI_KEY]")
    return redacted


class LLMClient:
    """
    Wrapper for Gemini API calls with exponential backoff and JSON extraction.
    Ensures strict transparency: never silently falls back to mocks if an API key is configured.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key if api_key is not None else GEMINI_API_KEY
        self.client = None
        self.api_call_count = 0
        self.is_mock = False

        if self.api_key and self.api_key != "your_gemini_api_key_here":
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                self.is_mock = False
                logger.info(f"Initialized live Google GenAI client with key: {redact_secrets(self.api_key)}")
            except Exception as e:
                raise RuntimeError(f"Failed to initialize google-genai client with provided key: {redact_secrets(str(e))}")
        else:
            self.is_mock = True
            logger.warning("No valid GEMINI_API_KEY provided; operating in offline simulation mode.")

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_retries: int = 3,
        base_delay: float = 1.5,
    ) -> str:
        """
        Generates freeform text with exponential backoff and automatic multi-model failover.
        Raises an error if all model candidates fail; NEVER silently falls back to mock.
        """
        self.api_call_count += 1

        # Offline simulation only if no key was configured
        if self.is_mock or not self.client:
            return self._offline_generate_text(prompt, system_instruction)

        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction,
        )

        candidates = _get_model_candidates(model, DEFAULT_GENERATOR_MODEL)
        last_error = None

        for model_name in candidates:
            for attempt in range(max_retries):
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=config,
                    )
                    if response and response.text:
                        return response.text
                    return ""
                except Exception as e:
                    last_error = e
                    err_str = str(e)
                    # If model not found (404), immediately cascade to next model candidate
                    if "404" in err_str or "not found" in err_str.lower():
                        logger.warning(f"Model '{model_name}' not available (404). Cascading to next model...")
                        break
                    # If high demand (503) on 2nd attempt, cascade to next available model
                    if "503" in err_str and attempt >= 1:
                        logger.warning(f"Model '{model_name}' experiencing high demand (503). Cascading to next model...")
                        break

                    import random
                    delay = (base_delay * (2 ** attempt)) + random.uniform(0.3, 1.0)
                    logger.warning(
                        f"Gemini API call on [{model_name}] attempt {attempt + 1}/{max_retries}: {redact_secrets(err_str)}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)

        # STRICT GUARDRAIL: Do NOT silently return mock if user supplied an API key
        raise RuntimeError(
            f"Gemini API call failed across all candidate models. Last error: {redact_secrets(str(last_error))}."
        )

    def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.0,
        schema: Optional[Type[BaseModel]] = None,
        max_retries: int = 3,
        base_delay: float = 1.5,
    ) -> Dict[str, Any]:
        """
        Forces valid JSON output with schema enforcement and automatic multi-model failover.
        Raises an error if all model candidates fail; NEVER silently falls back to mock.
        """
        self.api_call_count += 1

        # Offline simulation only if no key was configured
        if self.is_mock or not self.client:
            return self._offline_generate_json(prompt, system_instruction, schema)

        from google.genai import types

        config_kwargs: Dict[str, Any] = {
            "temperature": temperature,
            "response_mime_type": "application/json",
        }
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if schema:
            config_kwargs["response_schema"] = schema

        config = types.GenerateContentConfig(**config_kwargs)

        candidates = _get_model_candidates(model, DEFAULT_JUDGE_MODEL)
        last_error = None

        for model_name in candidates:
            for attempt in range(max_retries):
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=config,
                    )
                    raw_text = response.text or ""
                    parsed = self._extract_and_parse_json(raw_text)
                    if parsed is not None:
                        return parsed
                    raise ValueError(f"Failed to parse valid JSON from response: {raw_text[:200]}")
                except Exception as e:
                    last_error = e
                    err_str = str(e)
                    # If model not found (404), immediately cascade to next model candidate
                    if "404" in err_str or "not found" in err_str.lower():
                        logger.warning(f"Model '{model_name}' not available (404). Cascading to next model...")
                        break
                    # If high demand (503) on 2nd attempt, cascade to next available model
                    if "503" in err_str and attempt >= 1:
                        logger.warning(f"Model '{model_name}' experiencing high demand (503). Cascading to next model...")
                        break

                    import random
                    delay = (base_delay * (2 ** attempt)) + random.uniform(0.3, 1.0)
                    logger.warning(
                        f"Gemini JSON API on [{model_name}] attempt {attempt + 1}/{max_retries}: {redact_secrets(err_str)}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)

        # STRICT GUARDRAIL: Do NOT silently return mock if user supplied an API key
        raise RuntimeError(
            f"Gemini JSON API call failed across all candidate models. Last error: {redact_secrets(str(last_error))}."
        )

    def _extract_and_parse_json(self, raw: str) -> Optional[Dict[str, Any]]:
        """Cleans and extracts JSON even if markdown-wrapped (```json ... ```)."""
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            text = text.strip()

        try:
            return json.loads(text)
        except Exception:
            # Match outermost {...}
            match = re.search(r"(\{[\s\S]*\})", text)
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    return None
            return None

    # -------------------------------------------------------------------------
    # OFFLINE / TEST MOCKS
    # Enables complete local testing, continuous integration, and demo verification
    # without requiring an active paid Gemini API key.
    # -------------------------------------------------------------------------
    def _offline_generate_text(self, prompt: str, system_instruction: Optional[str]) -> str:
        """Deterministic high-quality beginner lesson generator for testing and offline runs."""
        # Check if this is a diff / what_changed_on_retry request
        if "what changed" in prompt.lower() or "compare the previous lesson" in prompt.lower():
            return "On retry, we fixed the sentence length and clarified the technical definitions. The everyday library analogy was preserved and grounded strictly in the grounding fact sheet."

        # High-quality lesson complying with all beginner constraints:
        # <= 15 words avg sentence, <= 25 words max sentence, jargon defined at first use,
        # open-book exam analogy, worked example, Hinglish glossary, recap, exactly 3 quiz questions.
        return """# Introduction to RAG (Retrieval-Augmented Generation)

Imagine you are sitting in a difficult final exam.
In a normal closed-book test, you must memorize every fact.
If your memory fails, you might guess or write wrong answers.
Now imagine your teacher allows an open-book exam.
You have your trusted textbooks right beside your desk.
When a question appears, you flip open the correct textbook page.
You read the exact sentence, and then you write a correct answer.
This open-book strategy is exactly how **RAG** works for artificial intelligence.

## 1. What is RAG?

**RAG** stands for **Retrieval-Augmented Generation**.
It is a smart technique used with an **LLM** (Large Language Model).
An **LLM** is an AI computer program that reads and writes human text.
Normally, an LLM only knows information from its past training.
With RAG, the AI first searches an outside **knowledge base**.
A **knowledge base** means a safe library of trusted documents or notes.
The AI finds the best matching text facts.
Next, it pastes those facts into its **prompt**.
A **prompt** refers to the question and instructions given to the AI.
Finally, the model writes a grounded, truthful answer.
Crucially, RAG does not retrain or alter the model's weights.
The AI model stays exactly the same.
It simply reads your reference notes before answering.

## 2. Why Does RAG Matter?

Regular AI models have three major limitations:
First, models suffer from **hallucination**.
**Hallucination** is when an AI invents false facts with high confidence.
Second, models suffer from knowledge cutoffs.
They cannot know news or events that happened after their training date.
Third, models do not know your private or company data.
For example, an AI has never seen your personal college syllabus notes.
RAG solves all three problems at once.
It gives the model current facts.
It stops wild guessing by providing proof.
It allows businesses to chat with their secret internal documents safely.

## 3. How Does RAG Work? (The 4 Steps)

RAG operates like a helpful student preparing college notes.
It follows four clean steps:

1. **Chunking**:
Long PDF files or books are split into small pieces called a **chunk**.
A **chunk** is a short paragraph of text.

2. **Embedding**:
Each chunk is converted into an **embedding**.
An **embedding** is a list of numbers that captures text meaning.
These number lists are stored inside a **vector database**.
A **vector database** refers to a fast storage system built for numbers.

3. **Retrieval**:
When you ask a question, the system turns your question into numbers.
It searches the vector database for matching chunks with similar meaning.
This step is called **retrieval**.

4. **Generation**:
The system hands the top retrieved notes to the LLM.
The LLM reads the notes and generates a clear answer.

## 4. Worked Step-by-Step Example

Let us see RAG in action for an Indian college student:

- **User Question**: "What is the deadline for submitting the BCA project report?"
- **Retrieved Text**: "Notice Board: All BCA final year project reports must be submitted to Room 302 by Friday, 5 PM."
- **Final LLM Answer**: "The submission deadline for your BCA project report is this Friday by 5:00 PM at Room 302."

The AI did not guess. It answered strictly from the retrieved notice.

## 5. Limitations of RAG

RAG is powerful, but it is not magic:
1. **Garbage In, Garbage Out**: If your stored notes contain mistakes, the AI will repeat those mistakes.
2. **Retrieval Misses**: If the search fails to find the right chunk, the AI cannot answer well.
3. **Extra Time and Cost**: Searching a database takes extra seconds and costs server money.

## 6. Hinglish Glossary

- **RAG**: Kitab khol kar dekh kar answer likhna (Open-book exam approach).
- **Chunk**: Badi file ka ek chhota tukda ya paragraph.
- **Embedding**: Words ka mathematical number format jo meaning batata hai.
- **Hallucination**: AI ka bina proof ke jhooth bolna.
- **Knowledge Base**: Aapki documents ya notes ki digital library.

## 7. Recap and Quick Check

### Recap
RAG connects an LLM to an external knowledge base.
It divides data into chunks, converts them to embeddings, retrieves facts, and generates answers.
It stops hallucinations without retraining model weights.

### Quick Check Questions
1. What does the letter 'R' stand for in the acronym RAG?
2. Does RAG retrain or change the internal weights of the AI model?
3. What is the name of a small piece of a larger document?
"""

    def _offline_generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str],
        schema: Optional[Type[BaseModel]]
    ) -> Dict[str, Any]:
        """Provides accurate offline mock responses for evaluator, planner, and reflector."""
        # 1. Planner request
        if "lesson spec" in prompt.lower() or "planner" in (system_instruction or "").lower():
            return {
                "topic": "Introduction to RAG (Retrieval-Augmented Generation)",
                "learner_profile": "12th-grade graduate from India, limited English vocabulary, non-English-medium background, zero AI knowledge",
                "must_cover_concepts": [
                    "What is RAG (Retrieval-Augmented Generation)",
                    "Why RAG matters (hallucination, outdated knowledge, private company data)",
                    "How RAG works (chunk, embed, retrieve, generate)",
                    "Difference between RAG and fine-tuning (weights never change)",
                    "Limitations of RAG (garbage in garbage out, retrieval failure, extra latency)"
                ],
                "jargon_list": [
                    "llm", "large language model", "embedding", "vector",
                    "chunk", "retrieval", "hallucination", "knowledge base",
                    "prompt", "vector database"
                ],
                "analogy": "Open-book examination with textbook lookup",
                "everyday_examples": [
                    "Checking college notice board before answering",
                    "Searching past WhatsApp chat history for exam dates",
                    "A student using library reference books during an open-book exam"
                ],
                "outline": [
                    "Hook & Analogy (Open-book exam)",
                    "1. What is RAG?",
                    "2. Why Does RAG Matter?",
                    "3. How Does RAG Work? (Chunk, Embed, Retrieve, Generate)",
                    "4. Worked Step-by-Step Example",
                    "5. Limitations of RAG",
                    "6. Hinglish Glossary",
                    "7. Recap and Quick Check (3 questions)"
                ]
            }

        # 2. Reflector request
        if "reflector" in (system_instruction or "").lower() or "propose" in prompt.lower():
            target_check = "B3a"
            rule_text = "Always introduce any technical term with a short definition in parentheses or right after the word 'is'."
            if "E2a" in prompt:
                target_check = "E2a"
                rule_text = "Ensure the final section has a clear 'Recap' heading followed by exactly 3 numbered quiz questions."
            elif "A2" in prompt:
                target_check = "A2"
                rule_text = "Explicitly emphasize that RAG never retrains or alters neural network model weights."
            elif "B1" in prompt or "B2" in prompt:
                target_check = "B1"
                rule_text = "Break long compound sentences into short, direct sentences with 15 or fewer words."
            elif "E1" in prompt:
                target_check = "E1"
                rule_text = "Always define what the core concept is before introducing worked examples."
            return {
                "rule_proposal": rule_text,
                "target_check": target_check,
                "rubric_feedback": None
            }

        # 3. Judge / Evaluator request
        # Extract candidate lesson from prompt to isolate from rubric criteria
        candidate_lesson = prompt
        if "CANDIDATE LESSON TEXT" in prompt:
            parts = prompt.split("CANDIDATE LESSON TEXT")
            if len(parts) > 1:
                candidate_lesson = parts[1]

        is_factual_error = (
            "retrains the model's weights" in candidate_lesson or
            "retrains the weights" in candidate_lesson or
            "modifies the neural network parameters directly" in candidate_lesson
        )
        is_jargon_dump = (
            "cosine similarity" in candidate_lesson or
            "Euclidean latent space" in candidate_lesson
        )
        is_bad_flow = (
            "here is an example first" in candidate_lesson.lower() or
            "worked example before explanation" in candidate_lesson.lower()
        )
        is_images_only = (
            "exclusively designed for creating digital jpeg photographs" in candidate_lesson.lower() or
            "nothing to do with written text" in candidate_lesson.lower() or
            "photo editing tool" in candidate_lesson.lower()
        )
        is_wrong_pipeline = (
            "user asks question ] ➡️ 1. chunk" in candidate_lesson.lower() or
            "takes your company documents and cuts them into chunks" in candidate_lesson.lower() or
            "user question is never embedded" in candidate_lesson.lower()
        )
        is_overclaim = (
            "completely eliminates 100% of ai hallucinations" in candidate_lesson.lower() or
            "guaranteed to never produce false information" in candidate_lesson.lower()
        )

        # Default all passing
        results = {
            "A1": {"passed": True, "reason": "Accurately defines RAG as retrieval from external knowledge.", "evidence": "", "fix_suggestion": ""},
            "A2": {"passed": True, "reason": "No claims contradict the fact sheet. Confirms weights do not change.", "evidence": "", "fix_suggestion": ""},
            "A3": {"passed": True, "reason": "Mentions limitations including latency and garbage in garbage out.", "evidence": "", "fix_suggestion": ""},
            "B3b": {"passed": True, "reason": "Jargon explained in simple everyday language.", "evidence": "", "fix_suggestion": ""},
            "B4": {"passed": True, "reason": "No confusing idioms or complex Western slang found.", "evidence": "", "fix_suggestion": ""},
            "C1": {"passed": True, "reason": "Uses one consistent everyday analogy (open-book exam).", "evidence": "", "fix_suggestion": ""},
            "C2": {"passed": True, "reason": "Step-by-step example with question, retrieved text, and answer present.", "evidence": "", "fix_suggestion": ""},
            "D2": {"passed": True, "reason": "All 4 steps (chunk, embed, retrieve, generate) clearly explained.", "evidence": "", "fix_suggestion": ""},
            "D3": {"passed": True, "reason": "Covers hallucination, outdated info, and private data.", "evidence": "", "fix_suggestion": ""},
            "E1": {"passed": True, "reason": "Logical teaching flow from basics to advanced.", "evidence": "", "fix_suggestion": ""},
            "E2b": {"passed": True, "reason": "All 3 quiz questions can be answered directly from the text.", "evidence": "", "fix_suggestion": ""}
        }

        # Inject deliberate failures when inspecting bad lessons
        if is_factual_error:
            results["A2"] = {
                "passed": False,
                "reason": "Lesson falsely claims that RAG retrains the model's weights on every query.",
                "evidence": "retrains the model's weights",
                "fix_suggestion": "Clarify that RAG does NOT modify or retrain model weights; it only retrieves text for the prompt."
            }

        if is_jargon_dump:
            results["B3b"] = {
                "passed": False,
                "reason": "Technical jargon is presented without simple everyday explanations.",
                "evidence": "cosine similarity",
                "fix_suggestion": "Explain technical terms like embeddings and similarity in plain words with everyday analogies."
            }

        if is_bad_flow:
            results["E1"] = {
                "passed": False,
                "reason": "Teaching flow is inverted: presents a complex example before explaining what RAG is.",
                "evidence": "Worked Example Before Explanation",
                "fix_suggestion": "Introduce the concept and everyday analogy first before jumping into specific examples."
            }

        if is_images_only:
            results["A1"] = {
                "passed": False,
                "reason": "Falsely defines RAG as a digital JPEG photography tool, completely omitting text and LLM grounding.",
                "evidence": "exclusively designed for creating digital JPEG photographs",
                "fix_suggestion": "Define RAG accurately as an AI technique that retrieves text documents from a knowledge base to ground LLM generation."
            }
            results["A2"] = {
                "passed": False,
                "reason": "Directly contradicts the grounding fact sheet: RAG retrieves text documents for LLMs, not JPEG photographs.",
                "evidence": "It has nothing to do with written text",
                "fix_suggestion": "Remove false claims regarding camera images and ground the lesson in external document retrieval."
            }

        if is_wrong_pipeline:
            results["D2"] = {
                "passed": False,
                "reason": "Pipeline incorrectly shows document chunking happening after the question is asked, and fails to state that the user question is also embedded.",
                "evidence": "Every time you type a question, the AI takes your company documents and cuts them into chunks.",
                "fix_suggestion": "Explain that preparation (chunking and embedding documents into a vector database) is done in advance, and the user question is also embedded at query time."
            }
            results["E1"] = {
                "passed": False,
                "reason": "Inverted pipeline order: depicts document preparation as triggered per query rather than in advance.",
                "evidence": "[ User Asks Question ] ➡️ 1. Chunk Documents",
                "fix_suggestion": "Clearly separate Phase 1 (Preparation in advance) from Phase 2 (Query time)."
            }

        if is_overclaim:
            results["A2"] = {
                "passed": False,
                "reason": "Lesson overclaims that RAG completely eliminates 100% of hallucinations. RAG reduces hallucinations, but cannot guarantee zero hallucinations.",
                "evidence": "RAG completely eliminates 100% of AI hallucinations and mistakes.",
                "fix_suggestion": "State that RAG reduces hallucinations, rather than claiming 100% elimination."
            }

        return {"checks": results}


# Singleton client instance
_default_client: Optional[LLMClient] = None

def get_llm_client() -> LLMClient:
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client
