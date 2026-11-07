# Rubric Changelog: Human-Governed Rubric Evolutions

This changelog records all human-reviewed and approved modifications to `rubric/rubric.yaml` and evaluator prompts.
In adherence to core security guardrails, autonomous LLM agents are strictly prohibited from modifying evaluation criteria. All changes listed below were reviewed, validated, and enacted by human curriculum engineers.

---

## [v1.3.0] - 2026-11-07
### Changed
- **Checkpoint A2 (`Grounding Integrity & Hallucination Overclaims`)**:
  - *Previous Criteria*: Only checked that weights are not modified.
  - *Human Revision*: Added strict requirement: `"does NOT claim RAG completely eliminates or stops hallucinations 100% (it only reduces them)." Flagging overclaims ensures technical honesty.`
  - *Pedagogical Rationale*: Beginners must learn that RAG dramatically grounds generation, but cannot mathematically guarantee zero hallucinations if source documents are contradictory or ambiguous.

---

## [v1.2.0] - 2026-11-07
### Changed
- **Checkpoint D2 (`Two-Phase Pipeline & Question Embedding`)**:
  - *Previous Criteria*: Merely required mentioning the 4 steps (chunk, embed, retrieve, generate).
  - *Human Revision*: Refined criteria to require explicit distinction between the **Preparation Phase** (documents chunked and embedded in advance into the vector database) and the **Query Phase** (user question is also embedded and compared to stored chunk numbers). Disallows misleading representations where documents are chunked *after* a user asks a question.
  - *Pedagogical Rationale*: Beginners must understand that database preparation is a one-time indexing cost, not an per-query operation.
- **Checkpoint E1 (`Logical Teaching Flow`)**:
  - *Human Revision*: Added requirement that the teaching flow must separate preparation/indexing from real-time question answering.
  - *Pedagogical Rationale*: Prevents inverted architectural mental models.

---

## [v1.1.0] - 2026-11-07
### Changed
- **Checkpoint B4 (`No Idioms, Slang, or Complex Vocabulary`)**:
  - *Previous Criteria*: Broadly flagged non-standard vocabulary.
  - *Human Revision*: Added explicit exclusion clause: `"Note: The Hinglish Glossary section is explicitly excluded from this check as it provides intentional vernacular translations."`
  - *Pedagogical Rationale*: Evaluator LLM was occasionally false-flagging bilingual Hindi/Hinglish translations (designed specifically for Indian 12th-graders from non-English backgrounds) as foreign slang. The glossary is an intentional scaffold, not ungrounded vocabulary.

---

## [v1.0.0] - 2026-11-06
### Initial Release
- Baseline rubric established with 16 binary PASS/FAIL checkpoints across 5 dimensions:
  - Dimension A: Accurate & Grounded (A1, A2, A3)
  - Dimension B: Beginner-Friendly Language (B1, B2, B3a, B3b, B4)
  - Dimension C: Teaches by Example (C1, C2)
  - Dimension D: Concept Coverage (D1, D2, D3)
  - Dimension E: Coherent Flow & Assessment (E1, E2a, E2b)

