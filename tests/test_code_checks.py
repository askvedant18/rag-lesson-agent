"""
Unit tests for deterministic code checks (Layer 1).
Runs 100% hermetically without requiring an API key.
"""

import pytest
from checks.code_checks import (
    clean_markdown_for_sentences,
    check_b1_avg_sentence_length,
    check_b2_max_sentence_length,
    check_b3a_jargon_defined_at_first_use,
    check_d1_required_headings,
    check_e2a_recap_and_quiz,
    run_all_code_checks
)

SAMPLE_PASSING_LESSON = """# Introduction to RAG

Imagine taking an open-book exam.
You have your textbooks on your desk.
You look up facts before writing your answers.
This is how RAG works for AI.

## 1. What is RAG?
**RAG** stands for **Retrieval-Augmented Generation**.
An **LLM** is an AI program that reads and writes text.
A **knowledge base** means a digital library of documents.
A **prompt** refers to the question given to the AI.
RAG does not change the model weights.

## 2. Why Does RAG Matter?
Regular models suffer from **hallucination**.
**Hallucination** is when an AI invents false facts.
RAG provides factual source text.
It also connects private notes.

## 3. How Does RAG Work?
First is **chunking**.
A **chunk** is a small piece of text.
Second is **embedding**.
An **embedding** is a list of numbers representing meaning.
Third is **retrieval**.
**Retrieval** means searching for matching chunks.
Fourth is generation.

## 4. Recap and Quick Check
### Recap
RAG searches external notes to answer questions.
### Questions
1. What does RAG stand for?
2. Does RAG change model weights?
3. What is a chunk?
"""

SAMPLE_LONG_SENTENCE = """# Introduction to AI
Whenever an artificial intelligence system encounters an extremely complicated user question that it has never seen before in its training data, it searches through millions of stored text documents to retrieve the most suitable pieces of text.
"""

def test_clean_markdown_for_sentences():
    text = "# Title\n\n- Bullet one.\n- Bullet two.\n\nHere is a normal sentence. And another one!"
    sentences = clean_markdown_for_sentences(text)
    assert len(sentences) >= 2
    assert "Title" not in sentences[0]
    assert not any(s.startswith("#") for s in sentences)

def test_check_b1_avg_sentence_length_passes():
    res = check_b1_avg_sentence_length(SAMPLE_PASSING_LESSON, max_avg=15.0)
    assert res["passed"] is True
    assert "Average sentence length" in res["reason"]

def test_check_b1_avg_sentence_length_fails_on_long():
    long_text = ("This is an extraordinarily verbose and unnecessarily convoluted sentence designed to push the average word count far above fifteen words per sentence. " * 5)
    res = check_b1_avg_sentence_length(long_text, max_avg=15.0)
    assert res["passed"] is False

def test_check_b2_max_sentence_length_detects_offender():
    res = check_b2_max_sentence_length(SAMPLE_LONG_SENTENCE, max_words=25)
    assert res["passed"] is False
    assert "exceeding 25 words" in res["reason"]
    assert len(res["evidence"]) > 0

def test_check_b2_max_sentence_length_passes_clean():
    res = check_b2_max_sentence_length(SAMPLE_PASSING_LESSON, max_words=25)
    assert res["passed"] is True

def test_check_b3a_jargon_defined_at_first_use():
    passing_res = check_b3a_jargon_defined_at_first_use(SAMPLE_PASSING_LESSON)
    assert passing_res["passed"] is True

    bad_text = "We converted the raw data into embeddings and computed similarity."
    failing_res = check_b3a_jargon_defined_at_first_use(bad_text, jargon_list=["embedding"])
    assert failing_res["passed"] is False
    assert "embedding" in failing_res["reason"].lower()

def test_check_d1_required_headings():
    passing_res = check_d1_required_headings(SAMPLE_PASSING_LESSON)
    assert passing_res["passed"] is True

    bad_text = "# Introduction\n\nJust some content without What, Why, How headings."
    failing_res = check_d1_required_headings(bad_text)
    assert failing_res["passed"] is False
    assert "Missing required section heading(s)" in failing_res["reason"]

def test_check_e2a_recap_and_quiz():
    passing_res = check_e2a_recap_and_quiz(SAMPLE_PASSING_LESSON)
    assert passing_res["passed"] is True

    # Missing recap
    no_recap = "## Quiz\n1. Question one?\n2. Question two?\n3. Question three?"
    assert check_e2a_recap_and_quiz(no_recap)["passed"] is False

    # Only 2 questions
    two_q = "## Recap\nSummary text.\n## Quiz\n1. Q one?\n2. Q two?"
    assert check_e2a_recap_and_quiz(two_q)["passed"] is False

def test_run_all_code_checks_returns_all_five():
    results = run_all_code_checks(SAMPLE_PASSING_LESSON)
    ids = {r["id"] for r in results}
    assert ids == {"B1", "B2", "B3a", "D1", "E2a"}
    assert all(r["passed"] for r in results)

