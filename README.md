# rag-lesson-agent | Self-Evaluating Content Generation System

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![Google GenAI](https://img.shields.io/badge/Google_GenAI-Official_SDK-orange.svg)](https://ai.google.dev/)
[![Tests Passing](https://img.shields.io/badge/pytest-23%2F23%20passed-brightgreen.svg)]()
[![Security Audited](https://img.shields.io/badge/Security-Hardened%20(XSS%2FCSRF%2FHeaders)-purple.svg)](SECURITY.md)

An agentic, self-evaluating lesson generator designed for the **GenAI Engineer - Content Systems** role. The system plans, drafts, rigorously evaluates, and autonomously regenerates educational content for 12th-grade graduates from India with zero AI background and non-English-medium schooling. It operates an explicit **Generate → Evaluate → Regenerate** state machine loop with hard PASS/FAIL checkpoints, memory-driven self-evolution, and an offline fallback for testing.

---

## Architecture Overview

```
                      +-----------------------------+
                      |         User Input          |
                      | (Topic / Deliberate Error)  |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |        Planner Agent        |
                      | (Grounding Facts + Spec)    |
                      +--------------+--------------+
                                     |
                                     v
               +------------> [Attempt 1 .. 3] <------------+
               |                     |                      |
               |                     v                      |
               |      +-----------------------------+       |
               |      |       Generator Agent       |       |
               |      | (Simple English + Analogies)|       |
               |      +--------------+--------------+       |
               |                     |                      |
               |                     v                      |
               |      +-----------------------------+       |
               |      |   Dual-Layer Evaluator      |       |
               |      | Layer 1: Deterministic Code |       |
               |      | Layer 2: Zero-Temp LLM Judge|       |
               |      +--------------+--------------+       |
               |                     |                      |
               |                     v                      |
               |            /-----------------\             |
  Fail + Retry |           /   All 16 Checks   \    Fail    |
  Feedback     +----------<       Passed?       >-----------+
                           \                   /   (Attempts < 3)
                            \-----------------/
                                     |
                          Pass       |       Fail (Attempts = 3)
                     +---------------+---------------+
                     |                               |
                     v                               v
       +---------------------------+   +---------------------------+
       |   output/final_lesson.md  |   | output/NEEDS_HUMAN_REVIEW |
       |     [STATUS: SHIPPED]     |   |   (Exhausted Retries)     |
       +-------------+-------------+   +-------------+-------------+
                     |                               |
                     +---------------+---------------+
                                     |
                                     v
                      +-----------------------------+
                      |       Reflector Agent       |
                      | (Learns Rules, Updates Memory|
                      +-----------------------------+
```

---

## 3-Step Setup & Run

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Configure Environment (Optional for Live Gemini)
```bash
cp .env.example .env
# Edit .env and paste your GEMINI_API_KEY from https://aistudio.google.com/
```
> **Note:** If no API key is supplied, the system operates in **deterministic offline fallback mode**. All tests, CLI runs, and the Web UI work out-of-the-box hermetically!

### Step 3: Run the Agent Loop
```bash
python main.py --topic "Introduction to RAG"
```

---

## CLI Usage & Flags

| Command | Purpose |
|---|---|
| `python main.py --topic "Introduction to RAG"` | Runs the end-to-end autonomous generation loop. |
| `python main.py --inject-bad tests/bad_lessons/factual_error.md` | **Loom Demo Flag**: Injects a bad lesson on Attempt 1, shows evaluator rejecting it with evidence, and generator self-correcting on retry. |
| `python main.py --evaluate-only <path_to_markdown>` | Evaluates any lesson file directly against the 16 rubric checks. |
| `python main.py --stats` | Displays cumulative memory failure counts, synthesized rules, and quarantined proposals. |
| `python main.py --serve` | Launches the modern FastAPI web interface on `http://127.0.0.1:8000`. |

---

## Web Application (UI + API)

The project includes an interactive web interface featuring a modern **Japanese/Korean minimalist editorial design system** with dark/light themes, Bento-grid layouts, and real-time Server-Sent Events (SSE).

### Starting the Server
```bash
python main.py --serve
# or: uvicorn web.app:app --host 127.0.0.1 --port 8000
```
Open **`http://127.0.0.1:8000`** in your browser.

### Key Web Features
1. **Live Pipeline Visualizer**: Animated state machine nodes (Planner 計画 → Generator 生成 → Evaluator 評価 → Decision 決定) with glowing indicators and retry loop-back animation.
2. **Evaluator Board**: Bento-grid of all 16 rubric check tiles with pass/fail badges. Clicking any tile opens a **side inspection drawer** revealing the criteria, exact quote from the lesson text, and fix suggestions.
3. **Deliberate-Error Lab (Video Demo Centerpiece)**: Instant presets for `factual_error`, `jargon_dump`, and `bad_flow` with a live evaluator button.
4. **Lesson Reader**: 18px+ typography designed for Indian students, reading progress bar, Hinglish glossary box, and interactive reveal cards for quiz questions.
5. **Memory & Reflection Dashboard**: Plain SVG bar chart showing cumulative check failures across runs, synthesized generator rules, and quarantined rubric change proposals.
6. **Rejection Log Viewer**: Filterable historical log of rejected drafts.

---

## Repository Structure

```
rag-lesson-agent/
├── README.md                           # Documentation, setup & architectural rationales
├── SECURITY.md                         # Security matrix (Threat -> Mitigation -> Code Location)
├── main.py                             # CLI orchestrator & reusable state machine loop
├── requirements.txt                    # Pinned Python dependencies
├── .env.example                        # Example environment configuration
├── .gitignore                          # Ignored secrets, virtualenv, and build artifacts
├── llm.py                              # Gemini wrapper (google-genai, retry, JSON mode, mock)
├── knowledge/
│   └── rag_facts.md                    # Canonical grounding fact sheet (strict facts)
├── rubric/
│   └── rubric.yaml                     # Rubric as data (16 hard pass/fail checkpoints)
├── checks/
│   └── code_checks.py                  # Deterministic code checks (B1, B2, B3a, D1, E2a)
├── agents/
│   ├── planner.py                      # Curriculum architect grounded in facts
│   ├── generator.py                    # Simple English drafting & targeted revision
│   ├── evaluator.py                    # Dual-layer evaluator & quote verification
│   └── reflector.py                    # Memory tracking & autonomous rule proposal
├── memory/
│   ├── failure_stats.json              # Cumulative check failure counts across runs
│   ├── learned_rules.json              # Active synthesized generator rules
│   └── proposed_rubric_changes.json    # Quarantined rubric proposals for human review
├── prompts/
│   ├── planner_v1.md                   # Versioned planner system prompt
│   ├── generator_v1.md                 # Versioned generator system prompt
│   └── judge_v1.md                     # Zero-temp judge prompt with anti-injection defense
├── logs/
│   └── rejection_log.jsonl             # Rejection audit trail with diff summaries
├── tests/
│   ├── bad_lessons/                    # Deliberately flawed test lessons
│   │   ├── factual_error.md            # Claims RAG retrains model weights (fails A2)
│   │   ├── jargon_dump.md              # Unexplained cosine similarity (fails B3a/B3b)
│   │   └── bad_flow.md                 # Example before definition (fails E1)
│   ├── test_code_checks.py             # Unit tests for deterministic checks
│   ├── test_evaluator_catches_errors.py# Asserts evaluator catches deliberate flaws
│   └── test_security.py                # Tests CSRF, XSS, headers, path traversal, injection
├── web/
│   ├── app.py                          # FastAPI SSE endpoints & static mount
│   ├── security.py                     # Security middleware, CSRF & rate limiters
│   └── static/                         # Frontend assets (Vanilla ES Modules)
│       ├── index.html                  # Bento-grid UI template
│       ├── style.css                   # Japanese/Korean editorial minimalist stylesheet
│       ├── app.js                      # SSE client, rubric board & interactive quiz
│       └── vendor/                     # Locally vendored libraries (zero external CDN)
│           ├── marked.min.js           # Markdown parser
│           └── purify.min.js           # DOMPurify XSS sanitizer
└── output/
    ├── final_lesson.md                 # Successfully cleared lesson (shipped)
    ├── NEEDS_HUMAN_REVIEW.md           # Fallback diagnostic report on failed retries
    ├── lesson_spec.json                # Latest curriculum specification
    ├── run_summary.json                # Run execution metrics
    └── attempts/                       # Saved attempt drafts (attempt_1.md, etc.)
```

---

## Design Decisions & Trade-Offs

### 1. Why a Hybrid Evaluator (Code Checks + LLM Judge)?
- **Deterministic Code Checks** are cheap, sub-millisecond, objective, and predictable. Grammatical constraints like sentence length ($\le 15$ words avg, $\le 25$ words max), presence of required headings, and quiz question counts do not require probabilistic inference.
- **LLM Judge (Temperature 0)** excels at semantic understanding: detecting whether a lesson contradicts grounding facts, whether an everyday analogy is sustained, or whether technical jargon is explained in accessible language.
- **Combining Them Eliminates Hallucination**: If the LLM judge claims a lesson failed and quotes an evidence string, the evaluator programmatically verifies whether that quote actually exists in the lesson text. If it does not, it is flagged as `judge_evidence_unverified`.

### 2. Why Hard PASS/FAIL Instead of Numerical Scores?
- Numerical scores (e.g. 7.5/10) encourage **gaming through averaging**: a lesson with great grammar (10/10) but a critical factual falsehood (5/10) could receive an 8/10 and mistakenly ship.
- In content generation for beginner students, a single factual error (e.g. telling a student that RAG retrains neural weights) is catastrophic. **Hard pass/fail with zero partial credit** ensures that every standard must clear before shipping.

### 3. Why Max 2 Retries (3 Attempts Total) + Human Review Fallback?
- Autonomous agent loops without termination bounds risk infinite loops, spiraling API bills, and runaway hallucinations.
- Bounding execution to 3 attempts guarantees termination. If the lesson still fails after Attempt 3, the system does **NOT** silently ship flawed content; it halts and produces `output/NEEDS_HUMAN_REVIEW.md` containing the diagnostic failure audit.

### 4. Why Rubric as Data (`rubric/rubric.yaml`)?
- Decouples evaluation logic from application code. Content architects can adjust pass criteria, add new dimensions, or update fail examples in a declarative YAML file without modifying Python logic or redeploying the backend.

### 5. Why Can the Reflector Only Propose Generator Rules and NOT Modify the Rubric?
- **Architectural Guardrail against Quality Degradation**: If an AI system could autonomously weaken its own evaluation rubric, it would inevitably lower the bar to make tests pass ("reward hacking").
- The Reflector can only synthesize instructions for the *Generator* (`memory/learned_rules.json`). Any suggested modifications to the *Rubric* are quarantined into `memory/proposed_rubric_changes.json` and require human authorization.

### 6. Why a Separate Judge Model at Temperature 0?
- Generators require creative variance ($\sim 0.7$ temperature) to craft natural analogies and relatable examples.
- Judges require strict determinism ($0.0$ temperature) to act as reliable, repeatable compliance checkers.

---

## Deliberate-Error Testing (For Video Demonstration)

The test suite includes 3 deliberately flawed lessons in `tests/bad_lessons/`:

1. **`factual_error.md`**: Falsely claims that RAG retrains neural network weights on every query.
   - Evaluator catches: Check **`A2`** (`Grounding Integrity`).
   - CLI Demo: `python main.py --inject-bad tests/bad_lessons/factual_error.md`
2. **`jargon_dump.md`**: Dumps high-level jargon ("cosine similarity", "Euclidean latent space") without explanation.
   - Evaluator catches: Check **`B3a`** & **`B3b`** (`Jargon Defined at First Use`).
   - CLI Demo: `python main.py --evaluate-only tests/bad_lessons/jargon_dump.md`
3. **`bad_flow.md`**: Inverts pedagogical order by presenting a worked example before explaining what RAG is.
   - Evaluator catches: Check **`E1`** (`Logical Teaching Flow`).
   - CLI Demo: `python main.py --evaluate-only tests/bad_lessons/bad_flow.md`

---

## Running the Automated Test Suite

Run all 23 unit, evaluator, and security tests:

```bash
python -m pytest -v
```

Output:
```
tests/test_code_checks.py::test_clean_markdown_for_sentences PASSED
tests/test_code_checks.py::test_check_b1_avg_sentence_length_passes PASSED
tests/test_code_checks.py::test_check_b1_avg_sentence_length_fails_on_long PASSED
tests/test_code_checks.py::test_check_b2_max_sentence_length_detects_offender PASSED
tests/test_code_checks.py::test_check_b2_max_sentence_length_passes_clean PASSED
tests/test_code_checks.py::test_check_b3a_jargon_defined_at_first_use PASSED
tests/test_code_checks.py::test_check_d1_required_headings PASSED
tests/test_code_checks.py::test_check_e2a_recap_and_quiz PASSED
tests/test_code_checks.py::test_run_all_code_checks_returns_all_five PASSED
tests/test_evaluator_catches_errors.py::test_factual_error_fails_a2 PASSED
tests/test_evaluator_catches_errors.py::test_jargon_dump_fails_jargon_checks PASSED
tests/test_evaluator_catches_errors.py::test_bad_flow_fails_e1 PASSED
tests/test_evaluator_catches_errors.py::test_passing_lesson_clears_all_rubric_checks PASSED
tests/test_evaluator_catches_errors.py::test_judge_hallucinated_quote_flagged PASSED
tests/test_security.py::test_csrf_rejection_without_token PASSED
tests/test_security.py::test_csrf_success_with_valid_token PASSED
tests/test_security.py::test_xss_payload_sanitization PASSED
tests/test_security.py::test_oversized_topic_rejected PASSED
tests/test_security.py::test_path_traversal_on_sample_key_rejected PASSED
tests/test_security.py::test_security_headers_present_on_all_responses PASSED
tests/test_security.py::test_cache_control_on_api_responses PASSED
tests/test_security.py::test_prompt_injection_defense PASSED
tests/test_security.py::test_secrets_redaction PASSED

======================= 23 passed in 0.93s =======================
```

---

## Known Limitations & Future Work

### Limitations
- **Heuristic Jargon Detection**: The code check verifies definition patterns (`is`, `means`, parentheses) near the term's first occurrence; subtle conceptual explanations spanning multiple paragraphs may occasionally trigger false positives.
- **Readability Proxies**: Sentence length ($\le 15$ words) is an effective proxy for 12th-grade readability, but does not capture all nuances of vocabulary familiarity across Indian regional backgrounds.

### Future Work
- **Multi-Lingual Glossaries**: Support Tamil, Telugu, Marathi, and Bengali regional glossaries alongside Hinglish.
- **Automated Human-in-the-Loop Approval UI**: Add an interactive dashboard for curriculum editors to approve quarantined rubric modifications with a single click.
- **Multimodal Visual Analogies**: Integrate automated diagram generation (e.g. SVG / Mermaid diagrams) illustrating the indexing vs query phases.

