# rag-lesson-agent | Self-Evaluating Content Generation System

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![Google GenAI](https://img.shields.io/badge/Google_GenAI-Official_SDK-orange.svg)](https://ai.google.dev/)
[![Tests Passing](https://img.shields.io/badge/pytest-27%2F27%20passed-brightgreen.svg)]()

An agentic, self-evaluating lesson generator designed for the **GenAI Engineer - Content Systems** role. The system plans, drafts, rigorously evaluates, and autonomously regenerates educational content for 12th-grade graduates from India with zero AI background and non-English-medium schooling. It operates an explicit **Generate → Evaluate → Regenerate** state machine loop with hard PASS/FAIL checkpoints and memory-driven self-evolution.

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
Tested with Python 3.12. Use a virtual environment:
```bash
python -m venv .venv
# On Windows PowerShell: .venv\Scripts\Activate.ps1
# On macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Configure Environment
```bash
cp .env.example .env
# Edit .env and paste your GEMINI_API_KEY from https://aistudio.google.com/
```
> **A real Gemini API key is required for real runs.** Without a key, the system starts in a clearly labelled **OFFLINE MOCK MODE**. It exists only for running the test suite without network access. Mock outputs are marked `is_mock: true` in every log and are never real lesson content.  
> *Tip: Keep the judge model (`gemini-3.1-flash-lite`) separate from the generator model (`gemini-3.5-flash`) to prevent self-reinforcing stylistic bias.*

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

The project includes an interactive web interface featuring a modern **Bento-grid minimalist editorial design system** with dark/light themes, card layouts, and real-time Server-Sent Events (SSE).

### Starting the Server
```bash
python main.py --serve
# or: uvicorn web.app:app --host 127.0.0.1 --port 8000
```
Open **`http://127.0.0.1:8000`** in your browser.

### Key Web Features
1. **Live Pipeline Visualizer**: Animated state machine nodes (Planner → Generator → Evaluator → Decision) with glowing indicators and retry loop-back animation.
2. **Evaluator Board**: Bento-grid of all 16 rubric check tiles with pass/fail badges. Clicking any tile opens a **side inspection drawer** revealing the criteria, exact quote from the lesson text, and fix suggestions.
3. **Deliberate-Error Lab (Video Demo Centerpiece)**: Instant presets for `factual_error`, `jargon_dump`, and `bad_flow` with a live evaluator button.
4. **Lesson Reader**: 18px+ typography designed for Indian students, reading progress bar, Plain-English glossary box, and interactive reveal cards for quiz questions.
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
│   │   ├── bad_flow.md                 # Example before definition (fails E1)
│   │   └── rag_is_images_only.md       # Custom error: claims RAG is photos only (fails A1/A2)
│   ├── test_code_checks.py             # Unit tests for deterministic checks
│   ├── test_evaluator_catches_errors.py# Asserts evaluator catches deliberate flaws
│   ├── test_generator_feedback.py      # Verifies retry passes failure feedback
│   └── test_security.py                # Tests CSRF, XSS, headers, path traversal, injection
├── web/
│   ├── app.py                          # FastAPI SSE endpoints & static mount
│   ├── security.py                     # Security middleware, CSRF & rate limiters
│   └── static/                         # Frontend assets (Vanilla ES Modules)
│       ├── index.html                  # Bento-grid UI template
│       ├── style.css                   # Modern minimalist stylesheet
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

## Design Decisions and Trade-offs

**1. Hybrid evaluator (code checks + LLM judge)**  
Some quality checks can be measured exactly: sentence length, headings, number of quiz questions, and technical jargon defined at first use. These are executed via deterministic Python code (`checks/code_checks.py`). They are free, instantaneous, and 100% repeatable. Other dimensions require semantic comprehension: logical pedagogical flow, clear analogies, and factual grounding against the fact sheet. These are evaluated by an LLM judge (`gemini-3.1-flash-lite`). Combining them reduces judge hallucination while ensuring objective constraints are strictly enforced.

**2. Hard PASS/FAIL checkpoints, zero partial credit**  
Numerical scores like "8/10" obscure critical failures and incentivize prompt gaming via averaging. Each of the 16 checks either passes or fails. A lesson ships only when every single check clears. This guarantees unambiguous quality standards and actionable diagnostic feedback.

**3. Distinct models & temperature 0 for evaluation**  
The generator uses `gemini-3.5-flash` at temperature 0.7 for creative pedagogical analogies, while the evaluator uses `gemini-3.1-flash-lite` at temperature 0.0 for strict compliance checking. Using a separate model prevents self-reinforcing stylistic biases. Furthermore, the evaluator must cite exact verbatim evidence quotes from the lesson text, and the Python harness verifies quote presence programmatically to reduce judge hallucination (`judge_evidence_unverified`).

**4. Finite 3-attempt state machine with human-review fallback**  
Endless retry loops waste tokens, increase latency, and can spiral into degraded generation. The system bounds retries to a maximum of 3 attempts. If criteria remain unsatisfied after 3 attempts, the system refuses to silently ship substandard material; it persists the draft and diagnostic failure report to `output/NEEDS_HUMAN_REVIEW.md`.

**5. Rubric as declarative data (`rubric/rubric.yaml`) & changelog**  
Rubric checkpoints live in an external YAML file, decoupled from application logic. Every human modification is formally logged in `rubric/CHANGELOG.md` with timestamps and pedagogical rationales.

**6. Asymmetric self-evolution guardrail (Generator vs Rubric)**  
The Reflector agent (`agents/reflector.py`) can synthesize new generator rules after repeated failures, but is **strictly prohibited from altering the evaluation rubric or judge prompts**. An autonomous agent that can lower its own examination bar would inevitably reward-hack. Rubric change suggestions are quarantined in `memory/proposed_rubric_changes.json` for human authorization. All learned rules also carry an `approved` flag for human governance (`RULE-001` was rejected as too vague).

**7. Targeted, surgical retry feedback**  
On retry, the generator does not receive generic critique; it receives only the specific failed check IDs, reasons, exact quotes, and fix suggestions. It is instructed to preserve passing sections and rewrite only the failing regions.

**8. Full-stack defense-in-depth security**  
Untrusted LLM outputs are rendered via marked.js and strictly sanitized with DOMPurify. The FastAPI backend implements double-submit CSRF cookies with auto-resynchronization, strict Content-Security-Policy, memory sliding-window rate limiting, input size whitelist constraints, and prompt injection defenses.

---

## Results from Real Runs (Live Gemini)

| Run | Attempts to Pass | Failed on Attempt 1 | Status |
|:---:|:---:|:---|:---:|
| 1 | 2 | B2 (sentence length), E2a (quiz count) | SHIPPED |
| 2 | 2 | E2a (quiz count) | SHIPPED |
| 3 | 1 | None (all 16 passed on first try) | SHIPPED |

> **Note on evaluation logs:**
> - Check **E2a** failed initially due to a regex limitation in my own Python checker (it required a `?` on every quiz line, missing True/False statements). Once the checker was fixed, Run 3 passed on Attempt 1.
> - The failures on **A2, B3a, D2, and E1** in `memory/failure_stats.json` come from my injected test lessons (`--inject-bad`), not from the generator drafting.
> - **Auto-learned rules:** The Reflector agent is implemented and tested, but no auto-learned rule is currently active (`RULE-001` was rejected during human review as too vague).

---

## Real Bugs Found by Reading My Own Logs (HITL Engineering)

- **Symptom**: `explain_changes()` reported that the draft was "identical and cut off mid-sentence at Section 2", even though the new attempt cleared all checks.  
  **Root Cause**: The function sliced input texts to `[:1200]`, starving the LLM of Section 8 (Quiz) where the actual modifications occurred.  
  **Fix**: Passed the complete text and added programmatic `no_progress` detection.
- **Symptom**: Check `E2a` failed on Attempt 1 across multiple runs (`found 2 questions instead of 3`).  
  **Root Cause**: Question 2 was phrased as a True/False statement ending with a period (`.`), but the regex heuristic required a question mark (`?`).  
  **Fix**: Made `check_e2a_recap_and_quiz()` tolerant of `1.`, `1)`, `Q1.`, and True/False statements, while stripping `<details>` answers from question counts.
- **Symptom**: The first synthesized rule (`RULE-001`) was too vague ("map every learning objective to an assessment task").  
  **Root Cause**: The Reflector prompt only passed `{check_id}` (`E2a`) without its name or pass criteria, forcing the model to guess what E2a meant.  
  **Fix**: Injected the check's exact name and pass criteria into the Reflector prompt, and marked `RULE-001` as `"approved": false` in `learned_rules.json` with reason *"Too vague: did not enforce quiz numbering format"*.
- **Symptom:** The judge passed a lesson that showed the wrong pipeline order (question first, then chunking and embedding).  
  **Root Cause:** Check `D2` only checked that the four terms appeared, not the execution order of the two phases.  
  **Fix:** Updated `D2` and `E1` pass criteria in `rubric/rubric.yaml` (human change, logged in `rubric/CHANGELOG.md`), added `tests/bad_lessons/wrong_pipeline_order.md`, and added an automated regression test.

---

## Deliberate-Error Testing (For Video Demonstration)

The test suite includes 5 deliberately flawed lessons in `tests/bad_lessons/`:

1. **`factual_error.md`**: Claims RAG retrains weights on query time $\to$ Fails **`A2`** (`Grounding Integrity`).
2. **`jargon_dump.md`**: Dumps unexplained terms ("cosine similarity", "latent space") $\to$ Fails **`B3a`** & **`B3b`**.
3. **`bad_flow.md`**: Presents a worked example before defining what RAG is $\to$ Fails **`E1`** (`Logical Teaching Flow`).
4. **`wrong_pipeline_order.md`**: Shows chunking triggered per query and omits question embedding $\to$ Fails **`D2`** & **`E1`**.
5. **`overclaim.md`**: Claims RAG eliminates 100% of hallucinations $\to$ Fails **`A2`**.

---

## Running the Automated Test Suite

Run all 27 unit, evaluator, and security tests hermetically:

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
tests/test_evaluator_catches_errors.py::test_custom_deliberate_error_images_only_fails_a1_and_a2 PASSED
tests/test_evaluator_catches_errors.py::test_wrong_pipeline_order_fails_d2_and_e1 PASSED
tests/test_evaluator_catches_errors.py::test_overclaim_fails_a2 PASSED
tests/test_evaluator_catches_errors.py::test_passing_lesson_clears_all_rubric_checks PASSED
tests/test_evaluator_catches_errors.py::test_judge_hallucinated_quote_flagged PASSED
tests/test_generator_feedback.py::test_generator_receives_failed_check_reasons_and_evidence PASSED
tests/test_security.py::test_csrf_rejection_without_token PASSED
tests/test_security.py::test_csrf_success_with_valid_token PASSED
tests/test_security.py::test_xss_payload_sanitization PASSED
tests/test_security.py::test_oversized_topic_rejected PASSED
tests/test_security.py::test_path_traversal_on_sample_key_rejected PASSED
tests/test_security.py::test_security_headers_present_on_all_responses PASSED
tests/test_security.py::test_cache_control_on_api_responses PASSED
tests/test_security.py::test_prompt_injection_defense PASSED
tests/test_security.py::test_secrets_redaction PASSED

======================= 27 passed in 1.76s =======================
```

---

## Known Limitations & Future Work

### Limitations
- **Shared LLM Architecture Family**: While different models (`gemini-3.5-flash` for generator, `gemini-3.1-flash-lite` for judge) are used, both come from Google's Gemini line, which may share minor underlying architectural priors.
- **Rule Threshold Latency**: Rules synthesize only after 2 repeated generator failures (`FAILURE_THRESHOLD=2`), so memory adapts iteratively rather than on single instances.
- **Approximate Readability Proxies**: Sentence length heuristics ($\le 15$ words avg, $\le 25$ words max) are effective proxies for 12th-grade learners, but do not capture regional vocabulary variations.

### Future Work
- **Multi-Lingual Glossaries**: Add Hindi, Tamil, and Telugu glossaries alongside plain English.
- **Multi-Model Jury Voting**: Add an optional second independent judge (e.g. Claude or GPT) to vote on disputed semantic checks.
- **Automated Human-in-the-Loop Web Interface**: Expand the memory dashboard to allow one-click human approval or editing of synthesized rules.

