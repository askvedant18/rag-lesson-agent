/**
 * rag-lesson-agent Frontend Client Application (ES Modules)
 * Handles CSRF management, SSE streaming, rubric board updates,
 * Deliberate-Error Lab, Markdown rendering via DOMPurify, and memory analytics.
 */

// Global State
let csrfToken = "";
let currentRunId = null;
let eventSource = null;
let rubricData = [];
let checkResultsMap = {};
let attemptsHistoryData = [];

// Sample bad lessons pre-loaded for the lab
const SAMPLE_LESSONS = {
  factual_error: `# Introduction to RAG (Retrieval-Augmented Generation)

Imagine preparing for an exam with reference notes.

## 1. What is RAG?
RAG stands for Retrieval-Augmented Generation.
It retrieves text from external documents.
Then, during query time, RAG retrains the model's weights on every query so the model learns permanently.
This process modifies the neural network parameters directly before writing the answer.

## 2. Why Does RAG Matter?
Regular models hallucinate. RAG provides factual text.

## 3. How Does RAG Work?
1. Chunking splits documents.
2. Embeddings are created.
3. Relevant text is retrieved.
4. Final answer is generated.

## 4. Worked Step-by-Step Example
- Question: "When is the test?"
- Retrieved: "The test is on Friday."
- Answer: "The test is on Friday."

## 5. Limitations of RAG
RAG can be slow and expensive.

## 6. Hinglish Glossary
- RAG: Kitab dekh kar answer likhna.

## 7. Recap and Quick Check
### Recap
RAG searches external notes and retrains model weights.
### Questions
1. What does RAG stand for?
2. Does RAG search external documents?
3. What is a chunk?`,

  jargon_dump: `# Introduction to RAG (Retrieval-Augmented Generation)

Imagine an open-book exam.

## 1. What is RAG?
RAG stands for Retrieval-Augmented Generation.
We project inputs into Euclidean latent space.
Then we calculate cosine similarity across high-dimensional manifolds without defining what a vector is.
Next, our pipeline accesses the vector database and triggers dense retrieval across topological index trees.

## 2. Why Does RAG Matter?
It mitigates hallucinations and bridges epistemic domain boundaries.

## 3. How Does RAG Work?
1. Documents are parsed.
2. Embeddings are created without explanation.
3. Nearest neighbor search retrieves passages.
4. The transformer executes autoregressive text generation.

## 4. Worked Step-by-Step Example
- Question: "What is the fee?"
- Retrieved: "The annual tuition fee is 50,000 rupees."
- Answer: "The annual tuition fee is 50,000 rupees."

## 5. Limitations of RAG
Search failure degrades generation quality.

## 6. Hinglish Glossary
- RAG: Open-book exam style search.

## 7. Recap and Quick Check
### Recap
RAG leverages cosine similarity and manifolds.
### Questions
1. What does RAG stand for?
2. What space are embeddings projected into?
3. What is the final step in RAG?`,

  bad_flow: `# Introduction to RAG (Retrieval-Augmented Generation)

## 1. Worked Example Before Explanation
Here is an example first before you know anything about AI or computers:
- Question: "What is the scholarship percentage?"
- Retrieved: "Top scorers receive a 50 percent waiver."
- Answer: "Students receive a 50 percent fee waiver."

Now let us look at the database architecture.
We store chunks in a vector database.

## 2. How Does RAG Work?
Chunking splits documents.
Embedding converts chunks into vectors.
Retrieval searches the vectors.
Generation writes the response.

## 3. Why Does RAG Matter?
It avoids hallucinations and accesses private documents.

## 4. What is RAG?
Finally, we explain what RAG actually means.
RAG stands for Retrieval-Augmented Generation.
It is an AI technique that retrieves external documents for an LLM.

## 5. Limitations of RAG
RAG can suffer from retrieval failure and latency costs.

## 6. Hinglish Glossary
- RAG: Kitab khol kar answer likhna.

## 7. Recap and Quick Check
### Recap
We saw the worked example first and finished with the definition.
### Questions
1. What was the sample question about?
2. What does RAG stand for?
3. Which step converts chunks into vectors?`
};

// Rubric Check Metadata Definitions (16 Checkpoints)
const RUBRIC_DEFS = [
  { id: "A1", dim: "A", name: "Correct RAG Definition", type: "llm", criteria: "Accurately defines RAG as retrieval from external knowledge to ground LLM responses." },
  { id: "A2", dim: "A", name: "Grounding Integrity (No Fact Contradictions)", type: "llm", criteria: "Contains zero claims contradicting the fact sheet (e.g. confirms RAG never retrains weights)." },
  { id: "A3", dim: "A", name: "Limitations Mentioned", type: "llm", criteria: "Explicitly discusses real-world limits (latency, costs, garbage in garbage out)." },
  { id: "B1", dim: "B", name: "Average Sentence Length <= 15 Words", type: "code", criteria: "Average word count across all body sentences is 15 words or fewer." },
  { id: "B2", dim: "B", name: "Max Sentence Length <= 25 Words", type: "code", criteria: "No single body sentence exceeds 25 words." },
  { id: "B3a", dim: "B", name: "Jargon Defined at First Use", type: "code", criteria: "Every technical term is introduced with a definition pattern at first use." },
  { id: "B3b", dim: "B", name: "Simple Jargon Explanations", type: "llm", criteria: "All technical terms are explained in genuine everyday words without circular jargon." },
  { id: "B4", dim: "B", name: "No Idioms, Slang, or Complex Words", type: "llm", criteria: "Avoids confusing Western idioms and unnecessarily academic terminology." },
  { id: "C1", dim: "C", name: "Consistent Everyday Analogy", type: "llm", criteria: "Uses one clear, consistent everyday analogy (open-book exam) throughout." },
  { id: "C2", dim: "C", name: "Worked Step-by-Step Example", type: "llm", criteria: "Concrete example showing Question -> Retrieved Text -> Final Answer." },
  { id: "D1", dim: "D", name: "Required Headings (What, Why, How)", type: "code", criteria: "Markdown contains clear section headings for What, Why, and How." },
  { id: "D2", dim: "D", name: "Four Core Pipeline Steps Explained", type: "llm", criteria: "Explains chunking, embedding, retrieval, and generation." },
  { id: "D3", dim: "D", name: "Why-It-Matters Core Benefits", type: "llm", criteria: "Covers hallucinations, outdated cutoff info, and connecting private data." },
  { id: "E1", dim: "E", name: "Logical Teaching Flow", type: "llm", criteria: "Concepts flow naturally without using advanced ideas before explaining them." },
  { id: "E2a", dim: "E", name: "Recap and Exactly 3 Quiz Questions", type: "code", criteria: "Recap section present and exactly 3 numbered quiz questions." },
  { id: "E2b", dim: "E", name: "Quiz Questions Answerable from Lesson", type: "llm", criteria: "All quiz questions test key concepts and can be answered from the text." }
];

// -----------------------------------------------------------------------------
// Initialize App
// -----------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", async () => {
  setupTheme();
  setupCSRF();
  renderRubricGrid();
  setupEventHandlers();
  loadFinalLesson();
  loadMemoryDashboard();
  loadRejectionLogs();
});

// -----------------------------------------------------------------------------
// Theme Management
// -----------------------------------------------------------------------------
function setupTheme() {
  const savedTheme = localStorage.getItem("rag_theme") || "dark";
  document.documentElement.setAttribute("data-theme", savedTheme);
  updateThemeIcon(savedTheme);

  document.getElementById("themeToggleBtn").addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme");
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("rag_theme", next);
    updateThemeIcon(next);
  });
}

function updateThemeIcon(theme) {
  const icon = document.getElementById("themeIcon");
  icon.textContent = theme === "dark" ? "☀️" : "🌙";
}

// -----------------------------------------------------------------------------
// CSRF Management
// -----------------------------------------------------------------------------
function getCsrfToken() {
  const match = document.cookie.match(/(?:^|; )\s*csrf_token=([^;]+)/);
  if (match) {
    return decodeURIComponent(match[1]);
  }
  return csrfToken;
}

async function setupCSRF() {
  try {
    const res = await fetch("/api/csrf", { credentials: "same-origin" });
    if (res.ok) {
      const data = await res.json();
      csrfToken = data.csrf_token;
    }

    // Check system LLM mode (Live vs Mock)
    const confRes = await fetch("/api/config", { credentials: "same-origin" });
    if (confRes.ok) {
      const conf = await confRes.json();
      const badge = document.getElementById("llmModeText");
      const banner = document.getElementById("mockModeBanner");
      if (conf.is_mock) {
        badge.textContent = "OFFLINE MOCK MODE";
        badge.style.color = "var(--accent-amber)";
        badge.style.borderColor = "var(--accent-amber)";
        if (banner) banner.style.display = "flex";
      } else {
        badge.textContent = `LIVE GEMINI (${conf.generator_model})`;
        badge.style.color = "var(--accent-primary)";
        badge.style.borderColor = "var(--accent-primary)";
        if (banner) banner.style.display = "none";
      }
    }
  } catch (err) {
    console.warn("Failed to obtain CSRF token or config:", err);
  }
}

// -----------------------------------------------------------------------------
// Render Rubric Board
// -----------------------------------------------------------------------------
function renderRubricGrid(filter = "all") {
  const grid = document.getElementById("rubricGrid");
  grid.innerHTML = "";

  RUBRIC_DEFS.forEach(check => {
    if (filter === "code" && check.type !== "code") return;
    if (filter === "llm" && check.type !== "llm") return;

    const card = document.createElement("div");
    card.className = "rubric-card";
    card.id = `card-${check.id}`;
    card.setAttribute("role", "button");
    card.setAttribute("tabindex", "0");

    card.innerHTML = `
      <div class="rubric-card-top">
        <span class="rubric-id">${check.id}</span>
        <span class="type-pill">${check.type.toUpperCase()}</span>
      </div>
      <div class="rubric-card-title">${escapeHTML(check.name)}</div>
      <div class="rubric-card-status">
        <span class="dim-tag">Dimension ${check.dim}</span>
        <span class="status-badge pending" id="status-${check.id}">WAITING</span>
      </div>
    `;

    card.addEventListener("click", () => openDrawer(check.id));
    grid.appendChild(card);
  });
}

// -----------------------------------------------------------------------------
// Event Handlers
// -----------------------------------------------------------------------------
function setupEventHandlers() {
  // Topic chips
  document.querySelectorAll(".chip").forEach(btn => {
    btn.addEventListener("click", () => {
      document.getElementById("topicInput").value = btn.dataset.topic;
    });
  });

  // Filter tags
  document.querySelectorAll(".filter-tag").forEach(tag => {
    tag.addEventListener("click", () => {
      document.querySelectorAll(".filter-tag").forEach(t => t.classList.remove("active"));
      tag.classList.add("active");
      renderRubricGrid(tag.dataset.filter);
      // Re-apply current check results to newly rendered cards
      applyCheckResultsToBoard();
    });
  });

  // Main Run Form
  document.getElementById("runForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const topic = document.getElementById("topicInput").value.trim();
    if (!topic) return;
    startGenerationRun(topic);
  });

  // Deliberate Error Lab Buttons
  document.getElementById("loadFactualErrorBtn").addEventListener("click", () => {
    document.getElementById("labTextarea").value = SAMPLE_LESSONS.factual_error;
    showToast("Loaded Factual Error sample lesson (claims RAG retrains weights).");
  });

  document.getElementById("loadJargonDumpBtn").addEventListener("click", () => {
    document.getElementById("labTextarea").value = SAMPLE_LESSONS.jargon_dump;
    showToast("Loaded Jargon Dump sample lesson (unexplained cosine similarity).");
  });

  document.getElementById("loadBadFlowBtn").addEventListener("click", () => {
    document.getElementById("labTextarea").value = SAMPLE_LESSONS.bad_flow;
    showToast("Loaded Bad Flow sample lesson (example before definition).");
  });

  document.getElementById("runLabEvaluateBtn").addEventListener("click", async () => {
    const text = document.getElementById("labTextarea").value.trim();
    if (!text) {
      showToast("Please paste or load a lesson text first.");
      return;
    }
    evaluateLessonLive(text);
  });

  document.getElementById("injectPipelineBtn").addEventListener("click", () => {
    const text = document.getElementById("labTextarea").value.trim();
    if (!text) {
      showToast("Please load a sample lesson first.");
      return;
    }
    // Determine which sample is active
    let key = "factual_error";
    if (text.includes("cosine similarity")) key = "jargon_dump";
    if (text.includes("Worked Example Before")) key = "bad_flow";
    startGenerationRun("Introduction to RAG", key);
  });

  // Sub-tabs
  document.querySelectorAll(".sub-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".sub-tab").forEach(t => t.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
      tab.classList.add("active");
      document.getElementById(tab.dataset.tab).classList.add("active");
    });
  });

  // Drawer Close
  document.getElementById("drawerCloseBtn").addEventListener("click", closeDrawer);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeDrawer();
  });

  // Copy & Download Markdown
  document.getElementById("copyMarkdownBtn").addEventListener("click", () => {
    const content = document.getElementById("lessonMarkdownBody").dataset.rawMarkdown || "";
    if (!content) return;
    navigator.clipboard.writeText(content).then(() => showToast("Markdown copied to clipboard!"));
  });

  document.getElementById("downloadMarkdownBtn").addEventListener("click", () => {
    const content = document.getElementById("lessonMarkdownBody").dataset.rawMarkdown || "";
    if (!content) return;
    const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "final_lesson.md";
    a.click();
    URL.revokeObjectURL(url);
    showToast("Downloaded final_lesson.md");
  });

  // Scroll Progress Bar for Lesson Reader
  window.addEventListener("scroll", () => {
    const reader = document.getElementById("lessonReaderSection");
    if (!reader) return;
    const rect = reader.getBoundingClientRect();
    const height = reader.offsetHeight - window.innerHeight;
    if (height > 0) {
      const scrolled = -rect.top;
      const pct = Math.max(0, Math.min(100, (scrolled / height) * 100));
      document.getElementById("readingProgressBar").style.width = `${pct}%`;
    }
  });
}

// -----------------------------------------------------------------------------
// Generation Run & SSE Streaming
// -----------------------------------------------------------------------------
async function startGenerationRun(topic, sampleKey = null) {
  setSystemStatus("Running", true);
  resetPipelineVisuals();
  resetRubricBoardStatus();
  attemptsHistoryData = [];
  renderAttemptsTabs();

  try {
    let token = getCsrfToken() || csrfToken;
    let res = await fetch("/api/run", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": token
      },
      body: JSON.stringify({ topic, sample_key: sampleKey })
    });

    if (res.status === 403) {
      // Re-synchronize CSRF token once and retry
      await setupCSRF();
      token = getCsrfToken() || csrfToken;
      res = await fetch("/api/run", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": token
        },
        body: JSON.stringify({ topic, sample_key: sampleKey })
      });
    }

    if (!res.ok) {
      const err = await res.json();
      showToast(err.error || err.detail || "Failed to start generation run.");
      setSystemStatus("Ready", false);
      return;
    }

    const data = await res.json();
    currentRunId = data.run_id;
    showToast(`Run initiated: ${currentRunId.slice(0, 8)}...`);
    subscribeToSSE(currentRunId);

  } catch (err) {
    showToast("Network error starting run.");
    setSystemStatus("Ready", false);
  }
}

function subscribeToSSE(runId) {
  if (eventSource) eventSource.close();
  eventSource = new EventSource(`/api/run/${runId}/stream`);

  eventSource.onmessage = (e) => {
    try {
      const event = JSON.parse(e.data);
      handleSSEEvent(event);
    } catch (err) {
      console.error("SSE parse error:", err);
    }
  };

  eventSource.onerror = (err) => {
    console.warn("SSE connection error or completed:", err);
    eventSource.close();
    setSystemStatus("Ready", false);
  };
}

function handleSSEEvent(event) {
  const type = event.event;

  if (type === "PLAN_START") {
    activateNode("nodePlanner", "Analyzing facts...");
  } else if (type === "PLAN_COMPLETE") {
    completeNode("nodePlanner");
    flowConnector("conn1");
  } else if (type === "ATTEMPT_START") {
    document.getElementById("pipelineAttemptBadge").textContent = `Attempt ${event.attempt} / ${event.max_attempts}`;
  } else if (type === "GENERATE_START" || type === "GENERATE_INJECTED") {
    activateNode("nodeGenerator", `Drafting attempt ${event.attempt}...`);
    document.getElementById("retryLoopCallout").style.display = "none";
  } else if (type === "GENERATE_COMPLETE") {
    completeNode("nodeGenerator");
    flowConnector("conn2");
    if (event.lesson) {
      storeAttemptLesson(event.attempt, event.lesson, event.what_changed);
    }
  } else if (type === "EVALUATE_START") {
    activateNode("nodeEvaluator", `Evaluating attempt ${event.attempt}...`);
    shimmerCheckCards();
  } else if (type === "EVALUATE_COMPLETE") {
    completeNode("nodeEvaluator");
    flowConnector("conn3");
    updateRubricCardsWithResults(event.checks);
    updateAttemptResults(event.attempt, event);
  } else if (type === "DECISION") {
    activateNode("nodeDecision", event.decision);
    if (event.decision === "SHIP") {
      completeNode("nodeDecision");
      showToast("Lesson passed all 16 checks and shipped!");
      loadFinalLesson();
    } else if (event.decision === "RETRY") {
      document.getElementById("retryLoopCallout").style.display = "flex";
      document.getElementById("retryLoopText").textContent = `Attempt ${event.attempt} failed ${event.failed_checks.length} check(s). Targeted regeneration triggered...`;
    } else if (event.decision === "NEEDS_HUMAN_REVIEW") {
      document.getElementById("nodeDecision").classList.add("failed");
      showToast("Maximum attempts reached. Saved for human review.");
    }
  } else if (type === "COMPLETE") {
    setSystemStatus("Ready", false);
    if (eventSource) eventSource.close();
    loadMemoryDashboard();
    loadRejectionLogs();
  }
}

// -----------------------------------------------------------------------------
// Live Live Evaluator (Deliberate-Error Lab)
// -----------------------------------------------------------------------------
async function evaluateLessonLive(lessonText) {
  shimmerCheckCards();
  setSystemStatus("Evaluating", true);

  try {
    let token = getCsrfToken() || csrfToken;
    let res = await fetch("/api/evaluate", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": token
      },
      body: JSON.stringify({ lesson_text: lessonText })
    });

    if (res.status === 403) {
      await setupCSRF();
      token = getCsrfToken() || csrfToken;
      res = await fetch("/api/evaluate", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": token
        },
        body: JSON.stringify({ lesson_text: lessonText })
      });
    }

    if (!res.ok) {
      const err = await res.json();
      showToast(err.error || err.detail || "Evaluation failed.");
      setSystemStatus("Ready", false);
      return;
    }

    const data = await res.json();
    updateRubricCardsWithResults(data.checks);
    setSystemStatus("Ready", false);

    if (data.passed) {
      showToast("All checks passed! Flawless lesson.");
    } else {
      showToast(`Evaluator caught ${data.failed_count} deliberate error(s)! Check highlighted cards.`);
    }

  } catch (err) {
    showToast("Evaluation error.");
    setSystemStatus("Ready", false);
  }
}

// -----------------------------------------------------------------------------
// Board & Pipeline Visual Updaters
// -----------------------------------------------------------------------------
function setSystemStatus(label, isBusy) {
  document.getElementById("systemStatusLabel").textContent = `System ${label}`;
  const dot = document.getElementById("systemStatusDot");
  if (isBusy) {
    dot.classList.add("busy");
  } else {
    dot.classList.remove("busy");
  }
}

function resetPipelineVisuals() {
  ["nodePlanner", "nodeGenerator", "nodeEvaluator", "nodeDecision"].forEach(id => {
    const node = document.getElementById(id);
    node.className = "pipeline-node";
    node.querySelector(".node-status").textContent = "Waiting";
  });
  ["conn1", "conn2", "conn3"].forEach(id => {
    document.getElementById(id).classList.remove("flowing");
  });
  document.getElementById("retryLoopCallout").style.display = "none";
}

function activateNode(id, statusText) {
  const node = document.getElementById(id);
  node.classList.add("active");
  node.querySelector(".node-status").textContent = statusText;
}

function completeNode(id) {
  const node = document.getElementById(id);
  node.classList.remove("active");
  node.classList.add("completed");
  node.querySelector(".node-status").textContent = "Completed ✓";
}

function flowConnector(id) {
  document.getElementById(id).classList.add("flowing");
}

function resetRubricBoardStatus() {
  RUBRIC_DEFS.forEach(c => {
    const badge = document.getElementById(`status-${c.id}`);
    if (badge) {
      badge.className = "status-badge pending";
      badge.textContent = "WAITING";
    }
  });
}

function shimmerCheckCards() {
  document.querySelectorAll(".rubric-card").forEach(c => {
    c.style.opacity = "0.75";
  });
}

function updateRubricCardsWithResults(checks) {
  checkResultsMap = {};
  checks.forEach(c => {
    checkResultsMap[c.id] = c;
    const badge = document.getElementById(`status-${c.id}`);
    const card = document.getElementById(`card-${c.id}`);
    if (badge && card) {
      card.style.opacity = "1";
      if (c.passed) {
        badge.className = "status-badge pass";
        badge.textContent = "PASS";
        card.style.borderColor = "var(--status-pass)";
      } else {
        badge.className = "status-badge fail";
        badge.textContent = "FAIL";
        card.style.borderColor = "var(--status-fail)";
      }
    }
  });
}

function applyCheckResultsToBoard() {
  Object.values(checkResultsMap).forEach(c => {
    const badge = document.getElementById(`status-${c.id}`);
    const card = document.getElementById(`card-${c.id}`);
    if (badge && card) {
      if (c.passed) {
        badge.className = "status-badge pass";
        badge.textContent = "PASS";
        card.style.borderColor = "var(--status-pass)";
      } else {
        badge.className = "status-badge fail";
        badge.textContent = "FAIL";
        card.style.borderColor = "var(--status-fail)";
      }
    }
  });
}

// -----------------------------------------------------------------------------
// Side Drawer (Check Detail Inspection)
// -----------------------------------------------------------------------------
function openDrawer(checkId) {
  const meta = RUBRIC_DEFS.find(c => c.id === checkId);
  const result = checkResultsMap[checkId];
  if (!meta) return;

  const drawer = document.getElementById("checkDrawer");
  document.getElementById("drawerCheckBadge").textContent = meta.id;
  document.getElementById("drawerCheckName").textContent = meta.name;
  document.getElementById("drawerCheckMeta").textContent = `${meta.type.toUpperCase()} • Dimension ${meta.dim}`;
  document.getElementById("drawerCheckCriteria").textContent = meta.criteria;

  const statusPill = document.getElementById("drawerCheckStatus");
  const reasonElem = document.getElementById("drawerCheckReason");
  const evidenceGroup = document.getElementById("drawerEvidenceGroup");
  const evidenceElem = document.getElementById("drawerCheckEvidence");
  const fixGroup = document.getElementById("drawerFixGroup");
  const fixElem = document.getElementById("drawerCheckFix");

  if (result) {
    if (result.passed) {
      statusPill.className = "status-pill pass";
      statusPill.textContent = "PASS";
      reasonElem.textContent = result.reason || "Check passed successfully.";
      evidenceGroup.style.display = result.evidence ? "block" : "none";
      evidenceElem.textContent = result.evidence || "";
      fixGroup.style.display = "none";
    } else {
      statusPill.className = "status-pill fail";
      statusPill.textContent = "FAIL";
      let reasonText = result.reason || "Checkpoint failed.";
      if (result.judge_evidence_unverified) {
        reasonText = "[Quote Unverified in Text] " + reasonText;
      }
      reasonElem.textContent = reasonText;
      evidenceGroup.style.display = result.evidence ? "block" : "none";
      evidenceElem.textContent = result.evidence ? `"${result.evidence}"` : "";
      fixGroup.style.display = result.fix_suggestion ? "block" : "none";
      fixElem.textContent = result.fix_suggestion || "";
    }
  } else {
    statusPill.className = "status-pill";
    statusPill.textContent = "NOT EVALUATED YET";
    reasonElem.textContent = "Run generation or the evaluator lab to inspect live results.";
    evidenceGroup.style.display = "none";
    fixGroup.style.display = "none";
  }

  drawer.classList.add("open");
  drawer.setAttribute("aria-hidden", "false");
}

function closeDrawer() {
  const drawer = document.getElementById("checkDrawer");
  drawer.classList.remove("open");
  drawer.setAttribute("aria-hidden", "true");
}

// -----------------------------------------------------------------------------
// Attempts Timeline & Tab Management
// -----------------------------------------------------------------------------
function storeAttemptLesson(attempt, lesson, whatChanged) {
  let existing = attemptsHistoryData.find(a => a.attempt === attempt);
  if (!existing) {
    existing = { attempt, lesson, whatChanged, checks: [] };
    attemptsHistoryData.push(existing);
  } else {
    existing.lesson = lesson;
    existing.whatChanged = whatChanged;
  }
  renderAttemptsTabs();
}

function updateAttemptResults(attempt, eventData) {
  let existing = attemptsHistoryData.find(a => a.attempt === attempt);
  if (!existing) {
    existing = { attempt, lesson: "", whatChanged: "", checks: eventData.checks };
    attemptsHistoryData.push(existing);
  } else {
    existing.checks = eventData.checks;
  }
  renderAttemptsTabs();
  displayAttemptDetail(attempt);
}

function renderAttemptsTabs() {
  const container = document.getElementById("attemptsTabs");
  const badge = document.getElementById("attemptsCountBadge");
  container.innerHTML = "";
  badge.textContent = `${attemptsHistoryData.length} Attempts`;

  attemptsHistoryData.forEach((att, idx) => {
    const btn = document.createElement("button");
    btn.className = `attempt-tab-btn ${idx === attemptsHistoryData.length - 1 ? 'active' : ''}`;
    btn.textContent = `Attempt ${att.attempt}`;
    btn.addEventListener("click", () => {
      document.querySelectorAll(".attempt-tab-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      displayAttemptDetail(att.attempt);
    });
    container.appendChild(btn);
  });
}

function displayAttemptDetail(attemptNumber) {
  const att = attemptsHistoryData.find(a => a.attempt === attemptNumber);
  const body = document.getElementById("attemptDetailBody");
  if (!att) return;

  const failed = (att.checks || []).filter(c => !c.passed);
  let html = `<div style="margin-bottom: 0.8rem;">`;
  html += `<strong>Status:</strong> ${failed.length === 0 ? '<span style="color:var(--status-pass)">Cleared All Checks</span>' : `<span style="color:var(--status-fail)">Failed ${failed.length} Check(s)</span>`}`;
  html += `</div>`;

  if (att.whatChanged) {
    html += `<div style="background:var(--bg-surface-elevated); padding:0.75rem; border-radius:var(--radius-sm); margin-bottom:0.8rem;">`;
    html += `<span style="font-size:0.75rem; text-transform:uppercase; color:var(--text-dim); font-weight:600;">What Changed on Retry:</span>`;
    html += `<p style="margin-top:0.3rem;">${escapeHTML(att.whatChanged)}</p>`;
    html += `</div>`;
  }

  if (failed.length > 0) {
    html += `<div style="margin-bottom:0.5rem; font-weight:600;">Failed Checkpoints:</div>`;
    failed.forEach(fc => {
      html += `<div style="border-left:2px solid var(--status-fail); padding-left:0.6rem; margin-bottom:0.6rem;">`;
      html += `<div><strong>[${fc.id}] ${escapeHTML(fc.name)}</strong></div>`;
      html += `<div style="color:var(--text-muted); font-size:0.82rem;">${escapeHTML(fc.reason)}</div>`;
      if (fc.evidence) {
        html += `<div style="font-family:var(--font-mono); font-size:0.75rem; color:var(--status-fail);">Quote: "${escapeHTML(fc.evidence)}"</div>`;
      }
      html += `</div>`;
    });
  }

  body.innerHTML = html;
}

// -----------------------------------------------------------------------------
// Markdown Lesson Reader & Sanitization
// -----------------------------------------------------------------------------
async function loadFinalLesson() {
  try {
    const res = await fetch("/api/lesson/final");
    if (res.ok) {
      const data = await res.json();
      if (data.found && data.content) {
        renderLessonMarkdown(data.content);
      }
    }
  } catch (err) {
    console.warn("Could not load final lesson:", err);
  }
}

function renderLessonMarkdown(rawMarkdown) {
  const container = document.getElementById("lessonMarkdownBody");
  container.dataset.rawMarkdown = rawMarkdown;

  // Use marked to parse markdown, then STRICTLY sanitize with DOMPurify
  const parsedHTML = marked.parse(rawMarkdown);
  const cleanHTML = DOMPurify.sanitize(parsedHTML, {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ["script", "iframe", "object", "embed"],
    FORBID_ATTR: ["onerror", "onload", "onclick", "onmouseover"]
  });

  container.innerHTML = cleanHTML;
  enhanceInteractiveQuizCards(container);
}

function enhanceInteractiveQuizCards(container) {
  // Find quiz questions and wrap with interactive reveal cards
  const questions = container.querySelectorAll("ol li, ul li");
  questions.forEach(li => {
    if (li.textContent.includes("?")) {
      const parent = li.closest("ol, ul");
      if (parent && parent.previousElementSibling && parent.previousElementSibling.textContent.toLowerCase().includes("quick check")) {
        li.style.cursor = "pointer";
        li.title = "Click to reveal discussion guide";
        li.addEventListener("click", () => {
          let answerBox = li.querySelector(".quiz-answer-inline");
          if (!answerBox) {
            answerBox = document.createElement("div");
            answerBox.className = "quiz-answer-inline";
            answerBox.style.marginTop = "0.4rem";
            answerBox.style.fontSize = "0.85rem";
            answerBox.style.color = "var(--accent-primary)";
            answerBox.textContent = "✓ Check your notes above to verify your answer!";
            li.appendChild(answerBox);
          } else {
            answerBox.remove();
          }
        });
      }
    }
  });
}

// -----------------------------------------------------------------------------
// Memory Dashboard & Rejection Logs
// -----------------------------------------------------------------------------
async function loadMemoryDashboard() {
  try {
    const statsRes = await fetch("/api/stats");
    if (statsRes.ok) {
      const stats = await statsRes.json();
      renderFailureBarChart(stats.check_failures || {});
    }

    const rulesRes = await fetch("/api/rules");
    if (rulesRes.ok) {
      const data = await rulesRes.json();
      renderActiveRules(data.rules || []);
      renderQuarantineList(data.proposed_rubric_changes || []);
    }
  } catch (err) {
    console.warn("Failed to load memory stats:", err);
  }
}

function renderFailureBarChart(checkFailures) {
  const container = document.getElementById("failureChartContainer");
  const entries = Object.entries(checkFailures);
  if (entries.length === 0) {
    container.innerHTML = `<p class="placeholder-text">No failures recorded yet. As lessons are rejected, failure counts will accumulate here.</p>`;
    return;
  }

  const maxVal = Math.max(...entries.map(e => e[1]), 1);
  let svg = `<svg viewBox="0 0 500 160" width="100%" height="160" style="overflow:visible;">`;

  entries.forEach(([cid, count], i) => {
    const x = i * 45 + 20;
    const barHeight = (count / maxVal) * 100;
    const y = 120 - barHeight;

    svg += `
      <rect x="${x}" y="${y}" width="28" height="${barHeight}" rx="4" fill="var(--status-fail)" opacity="0.85">
        <title>${cid}: ${count} failure(s)</title>
      </rect>
      <text x="${x + 14}" y="${y - 6}" text-anchor="middle" fill="var(--text-main)" font-size="11" font-weight="600">${count}</text>
      <text x="${x + 14}" y="140" text-anchor="middle" fill="var(--text-muted)" font-size="11">${cid}</text>
    `;
  });

  svg += `<line x1="10" y1="120" x2="480" y2="120" stroke="var(--border-subtle)" stroke-width="1" />`;
  svg += `</svg>`;
  container.innerHTML = svg;
}

function renderActiveRules(rules) {
  const container = document.getElementById("activeRulesList");
  if (rules.length === 0) {
    container.innerHTML = `<p class="placeholder-text">No learned rules synthesized yet. Rules are generated autonomously when any check reaches 3 failures.</p>`;
    return;
  }

  let html = "";
  rules.forEach(r => {
    html += `
      <div style="background:var(--bg-surface-elevated); border:1px solid var(--border-subtle); border-radius:var(--radius-sm); padding:0.8rem; margin-bottom:0.6rem;">
        <div style="display:flex; justify-content:space-between; margin-bottom:0.3rem;">
          <span class="badge">[${escapeHTML(r.id)}] From Check ${escapeHTML(r.created_from_check || 'System')}</span>
          <span style="font-size:0.75rem; color:var(--accent-primary);">Active & Injected</span>
        </div>
        <p style="font-size:0.88rem; font-weight:500;">${escapeHTML(r.rule_text)}</p>
      </div>
    `;
  });
  container.innerHTML = html;
}

function renderQuarantineList(proposals) {
  const container = document.getElementById("quarantineList");
  if (proposals.length === 0) {
    container.innerHTML = `<p class="placeholder-text">No proposed rubric changes. Evaluator criteria remain 100% stable and protected.</p>`;
    return;
  }

  let html = "";
  proposals.forEach(p => {
    html += `
      <div style="background:var(--bg-surface-elevated); border:1px dashed var(--accent-amber); border-radius:var(--radius-sm); padding:0.8rem; margin-bottom:0.6rem;">
        <div style="display:flex; justify-content:space-between; margin-bottom:0.3rem;">
          <span class="badge">[${escapeHTML(p.id)}] Rubric Check: ${escapeHTML(p.check_id)}</span>
          <span style="font-size:0.75rem; color:var(--accent-amber);">QUARANTINED • REQUIRES HUMAN APPROVAL</span>
        </div>
        <p style="font-size:0.85rem;"><strong>Proposed Modification:</strong> ${escapeHTML(p.proposal)}</p>
        <p style="font-size:0.78rem; color:var(--text-muted); margin-top:0.2rem;">Reason: ${escapeHTML(p.reason)}</p>
      </div>
    `;
  });
  container.innerHTML = html;
}

async function loadRejectionLogs() {
  try {
    const res = await fetch("/api/log");
    if (res.ok) {
      const data = await res.json();
      const tbody = document.querySelector("#rejectionLogTable tbody");
      tbody.innerHTML = "";

      if (!data.logs || data.logs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--text-dim); padding:1.5rem;">No rejection entries recorded yet.</td></tr>`;
        return;
      }

      data.logs.slice(-20).reverse().forEach(log => {
        const tr = document.createElement("tr");
        const failedCids = (log.failed_check_ids || []).join(", ");
        tr.innerHTML = `
          <td>${new Date(log.timestamp).toLocaleTimeString()}</td>
          <td style="font-family:var(--font-mono); font-size:0.75rem;">${(log.run_id || '').slice(0, 8)}...</td>
          <td>${log.attempt}</td>
          <td style="color:var(--status-fail); font-weight:600;">${escapeHTML(failedCids)}</td>
          <td>${escapeHTML((log.what_changed_on_retry || '').slice(0, 70))}...</td>
          <td><span class="status-pill ${log.final_status === 'SHIPPED' ? 'pass' : 'fail'}">${log.final_status}</span></td>
        `;
        tbody.appendChild(tr);
      });
    }
  } catch (err) {
    console.warn("Failed to load rejection logs:", err);
  }
}

// -----------------------------------------------------------------------------
// Utilities
// -----------------------------------------------------------------------------
function showToast(msg) {
  const container = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

function escapeHTML(str) {
  if (!str) return "";
  return str.replace(/[&<>'"]/g, tag => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    "'": '&#39;',
    '"': '&quot;'
  }[tag] || tag));
}

