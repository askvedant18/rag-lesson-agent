"""
Deterministic code checks for beginner lesson generator.
Evaluates structural, grammatical, and formatting constraints without LLM calls.
All checks return:
    {
        "id": str,
        "name": str,
        "type": "code",
        "passed": bool,
        "reason": str,
        "evidence": str
    }
"""

import re
from typing import List, Dict, Any, Optional

DEFAULT_JARGON_LIST = [
    "llm",
    "large language model",
    "embedding",
    "vector",
    "chunk",
    "retrieval",
    "hallucination",
    "knowledge base",
    "prompt",
    "vector database"
]

DEFINITION_PATTERNS = [
    r"\bis\b",
    r"\bmeans\b",
    r"\bcalled\b",
    r"\brefers to\b",
    r"\bstands for\b",
    r"\bknown as\b",
    r"\bdefined as\b",
    r"\(.*?\)",      # Parenthetical explanation
    r"\s+-\s+",      # Dash explanation
    r":\s+",         # Colon explanation
]


def clean_markdown_for_sentences(text: str) -> List[str]:
    """
    Strips code blocks, headings, markdown links, list markers, and tables,
    then splits the body text into individual sentences.
    """
    # 1. Strip code blocks
    cleaned = re.sub(r"```[\s\S]*?```", " ", text)
    cleaned = re.sub(r"`[^`]+`", " ", cleaned)

    # 2. Strip images and links [text](url) -> text
    cleaned = re.sub(r"!\[.*?\]\(.*?\)", " ", cleaned)
    cleaned = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", cleaned)

    # 3. Strip table borders and headers
    cleaned = re.sub(r"\|[^\n]+\|", " ", cleaned)

    # 4. Process line by line: drop headings, horizontal rules, and treat list bullets cleanly
    body_lines = []
    for line in cleaned.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if re.match(r"^(\-{3,}|\*{3,}|_{3,})$", stripped):
            continue
        # Remove bullet marks (e.g., "- ", "* ", "1. ")
        stripped = re.sub(r"^(\*|\-|\+|\d+\.)\s+", "", stripped)
        # If line ends with colon or does not end with punctuation, append period if it looks like a list item
        if stripped.endswith(":"):
            stripped = stripped[:-1] + "."
        elif not re.search(r"[.!?\"'”’]$", stripped):
            stripped = stripped + "."
        body_lines.append(stripped)

    full_body = " ".join(body_lines)

    # Split into sentences by '.', '!', '?', accounting for optional closing quotes
    normalized = re.sub(r"\b(e\.g\.|i\.e\.|vs\.|dr\.|mr\.|mrs\.)", r"\1_", full_body, flags=re.I)
    marked = re.sub(r'([.!?]["\'”’]?)\s+', r"\1<SENT_SPLIT>", normalized)
    raw_sentences = marked.split("<SENT_SPLIT>")

    sentences = []
    for s in raw_sentences:
        clean_s = s.replace("_", "").strip()
        # Remove leftover quotes, parentheses, bullets
        clean_s = re.sub(r"^[\s\"'“”‘’\(\)\[\]\-]+", "", clean_s)
        clean_s = re.sub(r"[\s\"'“”‘’\(\)\[\]\-]+$", "", clean_s)
        # Discard very short fragments (< 3 words)
        words = [w for w in re.split(r"\s+", clean_s) if w]
        if len(words) >= 3:
            sentences.append(clean_s)

    return sentences


def check_b1_avg_sentence_length(text: str, max_avg: float = 15.0) -> Dict[str, Any]:
    """
    B1: Average sentence length <= 15 words.
    """
    sentences = clean_markdown_for_sentences(text)
    if not sentences:
        return {
            "id": "B1",
            "name": "Average Sentence Length <= 15 Words",
            "type": "code",
            "passed": False,
            "reason": "No readable body sentences found in the lesson.",
            "evidence": "Total sentences: 0"
        }

    word_counts = [len(s.split()) for s in sentences]
    avg_len = sum(word_counts) / len(word_counts)
    passed = avg_len <= max_avg

    if passed:
        reason = f"Average sentence length is {avg_len:.1f} words (target <= {max_avg})."
    else:
        reason = f"Average sentence length is {avg_len:.1f} words, which exceeds the limit of {max_avg} words."

    evidence = f"Analyzed {len(sentences)} sentences. Total words: {sum(word_counts)}. Average: {avg_len:.1f} words/sentence."

    return {
        "id": "B1",
        "name": "Average Sentence Length <= 15 Words",
        "type": "code",
        "passed": passed,
        "reason": reason,
        "evidence": evidence
    }


def check_b2_max_sentence_length(text: str, max_words: int = 25) -> Dict[str, Any]:
    """
    B2: No sentence longer than 25 words.
    """
    sentences = clean_markdown_for_sentences(text)
    offenders = []

    for s in sentences:
        words = s.split()
        if len(words) > max_words:
            offenders.append((s, len(words)))

    passed = len(offenders) == 0

    if passed:
        reason = f"All sentences have {max_words} words or fewer."
        evidence = f"Checked {len(sentences)} sentences; longest sentence had {max((len(s.split()) for s in sentences), default=0)} words."
    else:
        reason = f"Found {len(offenders)} sentence(s) exceeding {max_words} words."
        evidence_lines = [f"[{count} words] \"{s}\"" for s, count in offenders[:3]]
        evidence = " | ".join(evidence_lines)

    return {
        "id": "B2",
        "name": "Max Sentence Length <= 25 Words",
        "type": "code",
        "passed": passed,
        "reason": reason,
        "evidence": evidence
    }


def check_b3a_jargon_defined_at_first_use(
    text: str,
    jargon_list: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    B3a: Every term in jargon_list is defined at first use.
    Heuristic: first occurrence must appear in a sentence with a definition pattern
    or have a definition within the same or next sentence.
    """
    if jargon_list is None:
        jargon_list = DEFAULT_JARGON_LIST

    sentences = clean_markdown_for_sentences(text)
    combined_def_regex = re.compile("|".join(DEFINITION_PATTERNS), re.IGNORECASE)

    unexplained = []

    for term in jargon_list:
        term_pattern = re.compile(rf"\b{re.escape(term)}(?:s|es|ing|ed)?\b", re.IGNORECASE)
        # Find first sentence index where term occurs
        first_idx = None
        first_sentence = ""
        for idx, s in enumerate(sentences):
            if term_pattern.search(s):
                first_idx = idx
                first_sentence = s
                break

        if first_idx is None:
            # Term was not used in the text
            continue

        # Check if first sentence has a definition pattern
        has_def_in_first = bool(combined_def_regex.search(first_sentence))
        has_def_in_next = False
        if not has_def_in_first and first_idx + 1 < len(sentences):
            next_s = sentences[first_idx + 1]
            has_def_in_next = bool(combined_def_regex.search(next_s))

        if not (has_def_in_first or has_def_in_next):
            unexplained.append({
                "term": term,
                "sentence": first_sentence
            })

    passed = len(unexplained) == 0

    if passed:
        reason = "All detected technical jargon terms are introduced with clear definitions."
        evidence = f"Checked {len(jargon_list)} jargon terms. All present terms defined at first use."
    else:
        failed_terms = [u["term"] for u in unexplained]
        reason = f"Jargon term(s) introduced without definition at first use: {', '.join(failed_terms)}."
        evidence_snippets = [f"Term '{u['term']}' in: \"{u['sentence']}\"" for u in unexplained[:2]]
        evidence = " | ".join(evidence_snippets)

    return {
        "id": "B3a",
        "name": "Jargon Defined at First Use (Code Heuristic)",
        "type": "code",
        "passed": passed,
        "reason": reason,
        "evidence": evidence
    }


def check_d1_required_headings(text: str) -> Dict[str, Any]:
    """
    D1: Headings present for What, Why, How.
    """
    headings = re.findall(r"^#{1,6}\s*(.+)$", text, flags=re.MULTILINE)
    headings_lower = [h.lower() for h in headings]

    has_what = any("what" in h for h in headings_lower)
    has_why = any("why" in h for h in headings_lower)
    has_how = any("how" in h for h in headings_lower)

    missing = []
    if not has_what:
        missing.append("What")
    if not has_why:
        missing.append("Why")
    if not has_how:
        missing.append("How")

    passed = len(missing) == 0

    if passed:
        reason = "Markdown contains required headings for What, Why, and How."
        evidence = f"Detected headings: {', '.join(headings[:5])}"
    else:
        reason = f"Missing required section heading(s): {', '.join(missing)}."
        evidence = f"Found headings: {', '.join(headings) if headings else 'None'}"

    return {
        "id": "D1",
        "name": "Required Headings (What, Why, How)",
        "type": "code",
        "passed": passed,
        "reason": reason,
        "evidence": evidence
    }


def check_e2a_recap_and_quiz(text: str) -> Dict[str, Any]:
    """
    E2a: Recap section exists and exactly 3 quick-check quiz questions exist.
    """
    headings = re.findall(r"^#{1,6}\s*(.+)$", text, flags=re.MULTILINE)
    headings_lower = [h.lower() for h in headings]

    has_recap = any(
        ("recap" in h or "summary" in h or "quick review" in h)
        for h in headings_lower
    )

    # Find Quiz or Quick Check section
    quiz_section_match = re.search(
        r"(?:^#{1,6}\s*.*(?:quiz|quick check|check your understanding|questions).*$)([\s\S]*)",
        text,
        flags=re.MULTILINE | re.IGNORECASE
    )

    question_count = 0
    if quiz_section_match:
        quiz_text = quiz_section_match.group(1)
        # Strip out answer key blocks or <details> so answers are not counted as questions
        quiz_text_clean = re.sub(r"<details[\s\S]*?</details>", "", quiz_text, flags=re.IGNORECASE)
        quiz_text_clean = re.split(r"(?i)#+\s*(?:answers?|answer key)", quiz_text_clean)[0]

        # Count questions: numbered items with a question mark
        numbered_questions = [
            l.strip()
            for l in quiz_text_clean.splitlines()
            if re.match(r"^(\d+\.|\bQ\d+[:\.\)])\s+.+", l.strip()) and "?" in l
        ]
        if not numbered_questions:
            # Fallback: numbered items even if question mark omitted
            numbered_questions = [
                l.strip()
                for l in quiz_text_clean.splitlines()
                if re.match(r"^(\d+\.|\bQ\d+[:\.\)])\s+.+", l.strip())
            ]
        question_count = len(numbered_questions)
    else:
        # Check global questions count in text
        q_lines = [
            line.strip()
            for line in text.splitlines()
            if re.match(r"^(\d+\.|\bQ\d+[:\.\)])\s+.+", line.strip()) and "?" in line
        ]
        question_count = len(q_lines)

    recap_passed = has_recap
    quiz_passed = (question_count == 3)
    passed = recap_passed and quiz_passed

    reasons = []
    if not recap_passed:
        reasons.append("Recap/Summary section is missing")
    if not quiz_passed:
        reasons.append(f"Expected exactly 3 quiz questions, found {question_count}")

    if passed:
        reason = "Recap section present and exactly 3 quiz questions detected."
        evidence = f"Recap found: Yes. Quiz question count: {question_count}."
    else:
        reason = "; ".join(reasons) + "."
        evidence = f"Recap heading present: {has_recap}. Quiz question count: {question_count}."

    return {
        "id": "E2a",
        "name": "Recap Section and Exactly 3 Quiz Questions",
        "type": "code",
        "passed": passed,
        "reason": reason,
        "evidence": evidence
    }


def run_all_code_checks(
    lesson_text: str,
    jargon_list: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Executes all deterministic code checks on the lesson text.
    """
    return [
        check_b1_avg_sentence_length(lesson_text),
        check_b2_max_sentence_length(lesson_text),
        check_b3a_jargon_defined_at_first_use(lesson_text, jargon_list),
        check_d1_required_headings(lesson_text),
        check_e2a_recap_and_quiz(lesson_text),
    ]
