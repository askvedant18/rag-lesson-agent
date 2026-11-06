"""
FastAPI Backend Application for rag-lesson-agent.
Provides real-time Server-Sent Events (SSE) streaming of agent pipeline execution,
secure CSRF endpoints, deliberate error evaluation lab, memory analytics, and rejection logs.
"""

import os
import json
import asyncio
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, Response, HTTPException, status, Depends
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from web.security import (
    SecurityHeadersMiddleware,
    TopicRunRequest,
    EvaluateLessonRequest,
    validate_csrf,
    generate_csrf_token,
    global_limiter,
    sanitize_untrusted_text,
    ALLOWED_SAMPLE_LESSONS,
    UUID4_REGEX
)
from main import run_agent_pipeline
from agents.evaluator import EvaluatorAgent
from agents.reflector import atomic_read_json

app = FastAPI(title="rag-lesson-agent", docs_url=None, redoc_url=None)

# Add security headers and rate limiter middleware
app.add_middleware(SecurityHeadersMiddleware)

# Directory configurations
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
MEMORY_DIR = os.path.join(BASE_DIR, "memory")

# In-memory storage of event queues for SSE streaming
run_queues: Dict[str, asyncio.Queue] = {}
run_results: Dict[str, Any] = {}


@app.get("/")
async def serve_index():
    """Serves the main single-page application."""
    index_file = os.path.join(STATIC_DIR, "index.html")
    return FileResponse(index_file, media_type="text/html")


@app.get("/api/csrf")
async def get_csrf_token(response: Response):
    """
    Issues a cryptographically secure CSRF token.
    Sets double-submit cookie with SameSite=Strict.
    """
    token = generate_csrf_token()
    response.set_cookie(
        key="csrf_token",
        value=token,
        httponly=False,  # Needs to be read by client to set X-CSRF-Token header
        samesite="strict",
        secure=False     # Set to True on production HTTPS
    )
    return {"csrf_token": token}


async def _execute_pipeline_task(run_id: str, topic: str, sample_key: Optional[str]):
    """Background worker executing the agent pipeline and publishing events to SSE queue."""
    queue = run_queues.get(run_id)
    if not queue:
        return

    injected_text = None
    if sample_key and sample_key in ALLOWED_SAMPLE_LESSONS:
        sample_path = os.path.join(BASE_DIR, ALLOWED_SAMPLE_LESSONS[sample_key])
        if os.path.exists(sample_path):
            with open(sample_path, "r", encoding="utf-8") as f:
                injected_text = f.read()

    try:
        # Run generator in separate thread to avoid blocking the asyncio event loop
        loop = asyncio.get_event_loop()
        def _run_sync():
            events = []
            for ev in run_agent_pipeline(topic=topic, injected_lesson=injected_text):
                events.append(ev)
            return events

        # Yield events as they occur
        for event in run_agent_pipeline(topic=topic, injected_lesson=injected_text):
            # Sanitize text payloads
            if "lesson" in event:
                event["lesson"] = sanitize_untrusted_text(event["lesson"])
            await queue.put(event)
            # Give client time to animate
            await asyncio.sleep(0.3)

    except Exception as exc:
        await queue.put({
            "event": "ERROR",
            "run_id": run_id,
            "error": "A pipeline error occurred during execution."
        })
    finally:
        global_limiter.release_run_slot()
        await queue.put({"event": "STREAM_END", "run_id": run_id})


@app.post("/api/run", dependencies=[Depends(validate_csrf)])
async def start_run(request: Request, body: TopicRunRequest):
    """
    Starts an end-to-end self-evaluating generation run.
    Returns run_id to subscribe via SSE.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    global_limiter.acquire_run_slot(client_ip)

    import uuid
    run_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    run_queues[run_id] = queue

    # Start pipeline in background task
    asyncio.create_task(_execute_pipeline_task(run_id, body.topic, body.sample_key))

    return {
        "status": "started",
        "run_id": run_id,
        "topic": body.topic
    }


@app.get("/api/run/{run_id}/stream")
async def stream_run(run_id: str):
    """
    Server-Sent Events (SSE) live event stream for a running agent session.
    """
    if not UUID4_REGEX.match(run_id):
        raise HTTPException(status_code=400, detail="Invalid run ID format.")

    if run_id not in run_queues:
        raise HTTPException(status_code=404, detail="Run not found or already completed.")

    queue = run_queues[run_id]

    async def event_generator():
        try:
            while True:
                # Wait for next event with a timeout
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=120.0)
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'event': 'PING'})}\n\n"
                    continue

                event_type = event.get("event")
                yield f"data: {json.dumps(event)}\n\n"

                if event_type == "STREAM_END":
                    break
        finally:
            if run_id in run_queues:
                del run_queues[run_id]

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/api/evaluate", dependencies=[Depends(validate_csrf)])
async def evaluate_lesson_endpoint(body: EvaluateLessonRequest):
    """
    Evaluates candidate lesson text live against the rubric (Deliberate Error Lab).
    """
    evaluator = EvaluatorAgent()
    cleaned_text = sanitize_untrusted_text(body.lesson_text)
    result = evaluator.evaluate(cleaned_text)
    return result


@app.get("/api/log")
async def get_rejection_logs():
    """Returns the persistent rejection log history."""
    log_file = os.path.join(LOGS_DIR, "rejection_log.jsonl")
    entries = []
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        pass
    return {"logs": entries[-50:]}


@app.get("/api/stats")
async def get_memory_stats():
    """Returns cumulative failure statistics and learning trends."""
    stats_file = os.path.join(MEMORY_DIR, "failure_stats.json")
    stats = atomic_read_json(stats_file, {})
    return stats


@app.get("/api/rules")
async def get_learned_rules():
    """Returns the list of active learned generator rules and proposed rubric changes."""
    rules_file = os.path.join(MEMORY_DIR, "learned_rules.json")
    proposals_file = os.path.join(MEMORY_DIR, "proposed_rubric_changes.json")

    rules = atomic_read_json(rules_file, [])
    proposals = atomic_read_json(proposals_file, [])

    return {
        "rules": rules,
        "proposed_rubric_changes": proposals
    }


@app.get("/api/lesson/final")
async def get_final_lesson():
    """Returns the currently shipped final lesson markdown."""
    lesson_path = os.path.join(OUTPUT_DIR, "final_lesson.md")
    if not os.path.exists(lesson_path):
        return {"content": "", "found": False}
    with open(lesson_path, "r", encoding="utf-8") as f:
        content = f.read()
    return {"content": content, "found": True}


# Mount static assets directory
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
