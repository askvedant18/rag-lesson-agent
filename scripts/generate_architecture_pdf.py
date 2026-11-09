"""
Generates a publication-grade, professional PDF documentation for rag-lesson-agent:
- Full System Architecture
- Detailed Component Breakdown (Agents, Rubric, State Machine, Security)
- Strategic Future Improvements Roadmap
"""

import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """Adds 'Page X of Y' footers and professional headers to all pages."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Don't draw running header on cover/page 1
        if self._pageNumber > 1:
            self.drawString(54, 11 * inch - 36, "rag-lesson-agent | System Architecture & Comprehensive Engineering Report")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 11 * inch - 42, 8.5 * inch - 54, 11 * inch - 42)
        
        # Footer
        text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 54, 36, text)
        self.drawString(54, 36, "rag-lesson-agent | System Architecture & Engineering Documentation")
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 48, 8.5 * inch - 54, 48)
        self.restoreState()


def build_pdf(filename="rag_lesson_agent_architecture_guide.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Custom Palette
    c_primary = colors.HexColor("#0F172A")    # Slate 900
    c_secondary = colors.HexColor("#1E3A8A")  # Blue 900
    c_accent = colors.HexColor("#2563EB")     # Blue 600
    c_dark = colors.HexColor("#1E293B")       # Slate 800
    c_muted = colors.HexColor("#64748B")      # Slate 500
    c_light_bg = colors.HexColor("#F8FAFC")   # Slate 50
    c_border = colors.HexColor("#E2E8F0")     # Slate 200
    c_pass = colors.HexColor("#059669")       # Emerald 600
    c_fail = colors.HexColor("#DC2626")       # Red 600

    # Typography styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=c_primary,
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=c_accent,
        spaceAfter=15
    )
    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=c_secondary,
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    )
    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=c_dark,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )
    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=c_dark,
        spaceAfter=6
    )
    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=c_dark,
        leftIndent=12,
        spaceAfter=3
    )
    code_block_style = ParagraphStyle(
        'Code_Custom',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=6
    )
    callout_style = ParagraphStyle(
        'Callout_Text',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1E293B")
    )
    th_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white
    )
    td_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=c_dark
    )

    story = []

    # ---------------------------------------------------------
    # COVER / TITLE BLOCK
    # ---------------------------------------------------------
    story.append(Paragraph("rag-lesson-agent", title_style))
    story.append(Paragraph("Self-Evaluating Content Generation System | Architecture & Engineering Specification", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=c_accent, spaceBefore=0, spaceAfter=12))

    meta_table_data = [
        [
            Paragraph("<b>Target Role:</b> GenAI Engineer - Content Systems", body_style),
            Paragraph("<b>Author:</b> Vedant Tiwari (Full Stack / Security)", body_style)
        ],
        [
            Paragraph("<b>Production Models:</b> Generator (Gemini 3.5 Flash) | Judge (Gemini 3.1 Flash Lite @ T=0)", body_style),
            Paragraph("<b>Audit Checkpoints:</b> 16 Binary Checks (5 Deterministic Code + 11 LLM)", body_style)
        ]
    ]
    meta_table = Table(meta_table_data, colWidths=[270, 234])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_light_bg),
        ('BOX', (0,0), (-1,-1), 1, c_border),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # ---------------------------------------------------------
    # SECTION 1: ARCHITECTURAL BLUEPRINT
    # ---------------------------------------------------------
    story.append(Paragraph("1. System Architecture & Lifecycle Blueprint", h1_style))
    story.append(Paragraph(
        "The system executes an explicit, bounded <b>Finite State Machine (FSM)</b> designed to autonomously draft, "
        "audit, and regenerate educational materials for 12th-grade graduates from India with non-English backgrounds. "
        "Unlike unconstrained conversational chains, our pipeline isolates authoring authority from evaluation authority, "
        "enforces hard PASS/FAIL gates, and maintains deterministic human-in-the-loop (HITL) memory safety.",
        body_style
    ))

    # Visual Pipeline Architecture Table
    arch_flow_data = [
        [
            Paragraph("<b>Lifecycle Phase</b>", th_style),
            Paragraph("<b>Agent & Operational Logic</b>", th_style),
            Paragraph("<b>I/O & Boundary Contracts</b>", th_style)
        ],
        [
            Paragraph("<font color='#2563EB'><b>Phase 1: Planning</b></font><br/><font size='7' color='#64748B'>agents/planner.py</font>", td_style),
            Paragraph("Analyzes topic, ingests grounding facts, profiles Indian 12th-pass learner, and selects single pedagogical analogy (The Open-Book Exam).", td_style),
            Paragraph("<b>Input:</b> <code>knowledge/rag_facts.md</code><br/><b>Output:</b> <code>output/lesson_spec.json</code>", td_style)
        ],
        [
            Paragraph("<font color='#2563EB'><b>Phase 2: Drafting</b></font><br/><font size='7' color='#64748B'>agents/generator.py</font>", td_style),
            Paragraph("Drafts lesson in simple English with short sentences (avg &le; 15 words, max 25 words). Explains jargon inline at first use. Integrates plain English glossary.", td_style),
            Paragraph("<b>Model:</b> <code>gemini-3.5-flash</code> (T=0.7)<br/><b>Output:</b> <code>output/attempts/attempt_N.md</code>", td_style)
        ],
        [
            Paragraph("<font color='#2563EB'><b>Phase 3: Dual Audit</b></font><br/><font size='7' color='#64748B'>agents/evaluator.py</font>", td_style),
            Paragraph("Executes 16 hard PASS/FAIL checks across 2 layers:<br/>• <b>Layer 1 (Code):</b> Words (B1,B2), Jargon (B3a), Headings (D1), Quiz (E2a)<br/>• <b>Layer 2 (LLM):</b> 11 semantic checks (A1..E2b) with verbatim evidence validation.", td_style),
            Paragraph("<b>Model:</b> <code>gemini-3.1-flash-lite</code> (T=0)<br/><b>Rubric:</b> <code>rubric/rubric.yaml</code><br/><b>Result:</b> 16/16 Binary Array", td_style)
        ],
        [
            Paragraph("<font color='#059669'><b>Phase 4a: Shipped</b></font><br/><font size='7' color='#64748B'>main.py (Router)</font>", td_style),
            Paragraph("Triggered when all 16 checks PASS. Marks run as SHIPPED, logs summary metrics, and notifies the client.", td_style),
            Paragraph("<b>Destination:</b><br/><code>output/final_lesson.md</code><br/><code>output/run_summary.json</code>", td_style)
        ],
        [
            Paragraph("<font color='#DC2626'><b>Phase 4b: Retry Loop</b></font><br/><font size='7' color='#64748B'>Bounded Retries (&lt; 3)</font>", td_style),
            Paragraph("Packages failed check IDs, exact failure reasons, verbatim quotes, and actionable fix suggestions directly back to Generator.", td_style),
            Paragraph("<b>Feedback:</b> Surgical revision payload.<br/><b>Log:</b> <code>logs/rejection_log.jsonl</code>", td_style)
        ],
        [
            Paragraph("<font color='#DC2626'><b>Phase 4c: Quarantine</b></font><br/><font size='7' color='#64748B'>Exhausted Retries (= 3)</font>", td_style),
            Paragraph("Halts pipeline without shipping flawed content. Persists diagnostic failure report for human inspection.", td_style),
            Paragraph("<b>Quarantine:</b><br/><code>output/NEEDS_HUMAN_REVIEW.md</code>", td_style)
        ],
        [
            Paragraph("<font color='#2563EB'><b>Phase 5: Reflection</b></font><br/><font size='7' color='#64748B'>agents/reflector.py</font>", td_style),
            Paragraph("Aggregates failure metrics across runs. Synthesizes operational generator rules after &ge; 2 failures. Quarantines rubric modifications for human authorization.", td_style),
            Paragraph("<b>Memory:</b> <code>failure_stats.json</code><br/><b>Rules:</b> <code>learned_rules.json</code><br/><b>Rubric:</b> <code>proposed_rubric_changes.json</code>", td_style)
        ]
    ]

    t_box = Table(arch_flow_data, colWidths=[120, 240, 144])
    t_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_secondary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_light_bg]),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_box)
    story.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # SECTION 2: CORE SUBSYSTEMS & COMPONENT DEEP-DIVE
    # ---------------------------------------------------------
    story.append(Paragraph("2. Deep Dive: Component Architectures", h1_style))

    story.append(Paragraph("A. Planner Agent (Curriculum Architecture)", h2_style))
    story.append(Paragraph(
        "The Planner anchors the session before drafting begins. It ingests strict grounding facts from "
        "<code>knowledge/rag_facts.md</code>, defines essential core concepts (Retrieval, Augmented, Generation, "
        "Two-Phase Execution, Model Weights Immutability), and selects a single pedagogical analogy. "
        "For RAG, it mandates <i>The Open-Book Exam</i> (LLM = student, retrieval = browsing notes, generation = writing answer). "
        "It outputs a machine-readable JSON specification to <code>output/lesson_spec.json</code>.",
        body_style
    ))

    story.append(Paragraph("B. Generator Agent (Constrained Drafting & Targeted Revision)", h2_style))
    story.append(Paragraph(
        "Powered by <code>gemini-3.5-flash</code> (T=0.7), the generator adheres to strict lexical and pedagogical rules: "
        "1) Sentences must average &le; 15 words with a hard ceiling of 25 words; "
        "2) Every technical jargon term (LLM, chunk, embedding, vector database) must be defined inline on first occurrence; "
        "3) Explicit prohibition against claiming RAG stops or eliminates hallucinations 100% (it only reduces them); "
        "4) Surgical retry feedback loop: On Attempt &gt; 1, it receives only failed check IDs, reasons, and quotes, "
        "revising failing blocks while leaving validated sections untouched.",
        body_style
    ))

    story.append(Paragraph("C. Dual-Layer Evaluator (16 Hard PASS/FAIL Checks)", h2_style))
    story.append(Paragraph(
        "The evaluator combines deterministic code verification with zero-temperature LLM reasoning to ensure zero tolerance for errors:",
        body_style
    ))

    checks_data = [
        [Paragraph("<b>Check ID</b>", th_style), Paragraph("<b>Type</b>", th_style), Paragraph("<b>Target Quality Criteria</b>", th_style), Paragraph("<b>Enforcement Layer</b>", th_style)],
        [Paragraph("<b>A1</b>", td_style), Paragraph("LLM", td_style), Paragraph("Correct RAG definition as retrieval + prompt augmentation + LLM generation", td_style), Paragraph("gemini-3.1-flash-lite (T=0)", td_style)],
        [Paragraph("<b>A2</b>", td_style), Paragraph("LLM", td_style), Paragraph("Grounding Integrity: Zero fact contradictions (e.g. weights never change, no 100% hallucination elimination claims)", td_style), Paragraph("Grounding Fact Sheet Auditor", td_style)],
        [Paragraph("<b>A3</b>", td_style), Paragraph("LLM", td_style), Paragraph("Mandatory Limitations: Retrieval misses, latency overhead, bad notes risk", td_style), Paragraph("Zero-Temp LLM Judge", td_style)],
        [Paragraph("<b>B1</b>", td_style), Paragraph("CODE", td_style), Paragraph("Average sentence length &le; 15 words across full markdown text", td_style), Paragraph("Python regex sentence tokenizer", td_style)],
        [Paragraph("<b>B2</b>", td_style), Paragraph("CODE", td_style), Paragraph("Hard maximum sentence ceiling &le; 25 words (zero runaway sentences)", td_style), Paragraph("Python sentence length validator", td_style)],
        [Paragraph("<b>B3a</b>", td_style), Paragraph("CODE", td_style), Paragraph("Jargon defined at first occurrence using is/means/(...) heuristics", td_style), Paragraph("Deterministic Regex Lexicon", td_style)],
        [Paragraph("<b>B3b</b>", td_style), Paragraph("LLM", td_style), Paragraph("Jargon explanations use plain, accessible beginner terminology", td_style), Paragraph("Zero-Temp LLM Judge", td_style)],
        [Paragraph("<b>B4</b>", td_style), Paragraph("LLM", td_style), Paragraph("Absence of confusing Western idioms, slang, or academic posturing", td_style), Paragraph("Vocabulary Auditor", td_style)],
        [Paragraph("<b>C1</b>", td_style), Paragraph("LLM", td_style), Paragraph("Single consistent analogy sustained from hook to recap", td_style), Paragraph("Analogy Continuity Judge", td_style)],
        [Paragraph("<b>C2</b>", td_style), Paragraph("LLM", td_style), Paragraph("Concrete worked example (User Question, Numbers/Vectors, Retrieved Chunk, Final Answer)", td_style), Paragraph("Pedagogical Example Auditor", td_style)],
        [Paragraph("<b>D1</b>", td_style), Paragraph("CODE", td_style), Paragraph("Required H2 structural headings: What, Why, and How", td_style), Paragraph("Markdown AST Parser", td_style)],
        [Paragraph("<b>D2</b>", td_style), Paragraph("LLM", td_style), Paragraph("Two-Phase Pipeline: Phase 1 (Prep: chunk + embed documents in advance) vs Phase 2 (Query time: embed question + retrieve + answer)", td_style), Paragraph("Two-Phase Pipeline Enforcer", td_style)],
        [Paragraph("<b>D3</b>", td_style), Paragraph("LLM", td_style), Paragraph("Why-it-matters core benefits: Hallucination mitigation + Outdated cutoff + Private data", td_style), Paragraph("Concept Coverage Judge", td_style)],
        [Paragraph("<b>E1</b>", td_style), Paragraph("LLM", td_style), Paragraph("Logical teaching flow: What -> Why -> Two-Phase How -> Worked Example -> Limits -> Recap", td_style), Paragraph("Pedagogical Flow Judge", td_style)],
        [Paragraph("<b>E2a</b>", td_style), Paragraph("CODE", td_style), Paragraph("Recap section present and exactly 3 numbered quiz questions (Q1, Q2, Q3)", td_style), Paragraph("Regex Quiz Parser (<details> excluded)", td_style)],
        [Paragraph("<b>E2b</b>", td_style), Paragraph("LLM", td_style), Paragraph("All 3 quiz questions unambiguously answerable from the lesson text alone", td_style), Paragraph("Quiz Grounding Judge", td_style)],
    ]
    t_checks = Table(checks_data, colWidths=[40, 36, 310, 118])
    t_checks.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_secondary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_light_bg]),
        ('PADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_checks)
    story.append(Spacer(1, 12))

    story.append(Paragraph("D. Memory, Self-Reflection & Human Guardrails", h2_style))
    story.append(Paragraph(
        "<b>Asymmetric Learning Security:</b> An autonomous agent must never possess write access to its own examination rubric. "
        "The Reflector (<code>agents/reflector.py</code>) tracks cumulative failures in <code>memory/failure_stats.json</code>. "
        "When a check fails repeatedly (&ge; 2 times), it synthesizes an operational rule for the Generator. "
        "However, rules are marked with an <code>approved: false</code> flag until explicitly validated by a human operator (HITL). "
        "Any suggestion to modify the rubric is quarantined into <code>memory/proposed_rubric_changes.json</code> and never executed automatically.",
        body_style
    ))

    # Page Break for clean reading
    story.append(PageBreak())

    # ---------------------------------------------------------
    # SECTION 3: ENTERPRISE SECURITY ARCHITECTURE
    # ---------------------------------------------------------
    story.append(Paragraph("3. Enterprise Security & Web Architecture", h1_style))
    story.append(Paragraph(
        "To satisfy production security standards, the FastAPI web layer (<code>web/app.py</code>, <code>web/security.py</code>) "
        "implements 13 defense-in-depth security mitigations documented in <code>SECURITY.md</code>:",
        body_style
    ))

    sec_data = [
        [Paragraph("<b>Threat Vector</b>", th_style), Paragraph("<b>Engineering Defense Mechanism</b>", th_style), Paragraph("<b>Implementation File</b>", th_style)],
        [Paragraph("<b>CSRF Attacks</b>", td_style), Paragraph("Double-submit cookie pattern with cryptographic HMAC constant-time matching and automatic cookie/header resync.", td_style), Paragraph("<code>web/security.py</code>", td_style)],
        [Paragraph("<b>XSS (Cross-Site Scripting)</b>", td_style), Paragraph("Server-side tag stripping combined with client-side DOMPurify sanitization before rendering marked.js markdown.", td_style), Paragraph("<code>web/static/app.js</code>", td_style)],
        [Paragraph("<b>Content Security Policy (CSP)</b>", td_style), Paragraph("Strict CSP headers: <code>default-src 'self'</code>, zero external CDN scripts, vendored marked/purify assets.", td_style), Paragraph("<code>SecurityHeadersMiddleware</code>", td_style)],
        [Paragraph("<b>Rate Limiting & DoS</b>", td_style), Paragraph("Sliding-window IP rate limiting (120 req/min, 20 runs/hour, max 3 concurrent background generation tasks).", td_style), Paragraph("<code>RateLimiter</code>", td_style)],
        [Paragraph("<b>Prompt Injection</b>", td_style), Paragraph("User topics and drafts wrapped in strict structural delimiters (<code>&lt;UNTRUSTED_CONTENT&gt;</code>); instructions ignored.", td_style), Paragraph("<code>prompts/judge_v1.md</code>", td_style)],
        [Paragraph("<b>Credential Leaks</b>", td_style), Paragraph("Automated regex secret redactor scrubbing <code>AIza[0-9A-Za-z_-]{30,45}</code> and GEMINI_API_KEY from logs & traces.", td_style), Paragraph("<code>llm.py (redact_secrets)</code>", td_style)],
    ]
    t_sec = Table(sec_data, colWidths=[110, 270, 124])
    t_sec.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_secondary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_light_bg]),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_sec)
    story.append(Spacer(1, 14))

    # ---------------------------------------------------------
    # SECTION 4: STRATEGIC IMPROVEMENTS ROADMAP (WHAT NEXT?)
    # ---------------------------------------------------------
    story.append(Paragraph("4. Strategic System Enhancements & Future Roadmap", h1_style))
    story.append(Paragraph(
        "To evolve rag-lesson-agent from a single-node assessment system into an enterprise-scale content generation engine, "
        "the following architectural expansions are planned:",
        body_style
    ))

    story.append(Paragraph("1. Cross-Family Multi-Model Jury (Eliminating Family Bias)", h2_style))
    story.append(Paragraph(
        "<b>Current State:</b> Both generator (Gemini 3.5 Flash) and judge (Gemini 3.1 Flash Lite) share Google's underlying model architecture and training priors.<br/>"
        "<b>Roadmap:</b> Implement a multi-model jury voting protocol. For critical checks (A1 Definition, A2 Grounding, D2 Pipeline Order), "
        "the system queries an ensemble: Gemini 3.1, Anthropic Claude 3.5 Haiku, and an open-weights model (e.g. Llama-3.3-70B via Ollama/vLLM). "
        "A 2-out-of-3 consensus determines the verdict, eliminating shared cognitive blind spots.",
        body_style
    ))

    story.append(Paragraph("2. Vector Database & Live Dynamic Retrieval Grounding", h2_style))
    story.append(Paragraph(
        "<b>Current State:</b> Facts are loaded from a static markdown file (<code>knowledge/rag_facts.md</code>).<br/>"
        "<b>Roadmap:</b> Integrate an embedded vector database (e.g. ChromaDB or Qdrant). Grounding facts, recent curriculum guidelines, "
        "and pedagogical research papers will be embedded dynamically using <code>gemini-embedding-001</code>. The planner can query "
        "authoritative educational repositories dynamically based on the requested subject.",
        body_style
    ))

    story.append(Paragraph("3. Automated EvalOps & Precision/Recall Benchmark Harness", h2_style))
    story.append(Paragraph(
        "<b>Current State:</b> Evaluator quality is validated against 5 deliberate bad lessons in <code>tests/bad_lessons/</code>.<br/>"
        "<b>Roadmap:</b> Build a synthetic benchmark harness generating 100+ annotated good and bad lessons spanning subtle flaws "
        "(e.g. subtle order inversion, mild jargon leaks, borderline sentence length). Automatically compute <b>Precision, Recall, "
        "and F1-Score</b> for every rubric check on each git commit, alerting if prompt drift impairs error-catching recall.",
        body_style
    ))

    story.append(Paragraph("4. Direct Preference Optimization (DPO) Dataset Curation", h2_style))
    story.append(Paragraph(
        "<b>Current State:</b> Lessons are drafted and rejected in <code>logs/rejection_log.jsonl</code>.<br/>"
        "<b>Roadmap:</b> Utilize the rejection logs as an automated source of paired preference data: <i>rejected draft</i> (Attempt 1) "
        "vs <i>accepted draft</i> (Attempt 2). Export this data to standard DPO (Direct Preference Optimization) format to fine-tune "
        "smaller, cost-effective edge models (e.g. Gemma-2-9B) to draft compliant educational content on Attempt 1 with zero retries.",
        body_style
    ))

    story.append(Paragraph("5. Multilingual Indian Vernacular Translation Engine", h2_style))
    story.append(Paragraph(
        "<b>Current State:</b> The lesson is drafted in simple English with an English glossary.<br/>"
        "<b>Roadmap:</b> Add a downstream localization agent that takes the validated, shipped lesson and translates it into "
        "Hindi, Tamil, Telugu, Marathi, and Bengali while preserving code blocks, ASCII diagrams, and interactive quiz formatting.",
        body_style
    ))

    story.append(Paragraph("6. Production Observability & Distributed Tracing", h2_style))
    story.append(Paragraph(
        "<b>Current State:</b> Logs are stored in local JSON Lines (<code>logs/rejection_log.jsonl</code>) and console streams.<br/>"
        "<b>Roadmap:</b> Integrate OpenTelemetry instrumentation connected to Langfuse, Arize Phoenix, or Datadog. Track token usage, "
        "per-check LLM latency, cost per shipped lesson, and time-to-ship across thousands of concurrent student sessions.",
        body_style
    ))

    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=c_border, spaceBefore=4, spaceAfter=8))
    story.append(Paragraph(
        "<b>Document Status:</b> Verified & Finalized | <b>Repository:</b> github.com/askvedant18/rag-lesson-agent | <b>Branch:</b> main",
        ParagraphStyle('FooterNotice', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, textColor=c_muted, alignment=1)
    ))

    try:
        doc.build(story, canvasmaker=NumberedCanvas)
        print(f"Successfully generated architecture PDF: {filename}")
    except PermissionError:
        fallback_pdf = "rag_lesson_agent_architecture.pdf"
        print(f"Notice: '{filename}' is currently locked/opened in a viewer. Writing to '{fallback_pdf}' instead...")
        doc = SimpleDocTemplate(
            fallback_pdf,
            pagesize=letter,
            leftMargin=54,
            rightMargin=54,
            topMargin=54,
            bottomMargin=54
        )
        doc.build(story, canvasmaker=NumberedCanvas)
        print(f"Successfully generated architecture PDF: {fallback_pdf}")


if __name__ == "__main__":
    out_pdf = "rag_lesson_agent_architecture_guide.pdf"
    if len(sys.argv) > 1:
        out_pdf = sys.argv[1]
    build_pdf(out_pdf)

