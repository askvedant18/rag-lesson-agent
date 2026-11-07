"""
Main Entrypoint and Orchestrator for rag-lesson-agent.
Implements the explicit Generate -> Evaluate -> Regenerate state machine loop.
Provides full CLI controls, deliberate-error injection, statistics reporting,
and acts as the shared core pipeline for the web application SSE stream.
"""

import os
import sys
import json
import uuid
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Generator

# Import agent components
from agents.planner import PlannerAgent
from agents.generator import GeneratorAgent
from agents.evaluator import EvaluatorAgent
from agents.reflector import ReflectorAgent, atomic_write_json, atomic_read_json
from llm import get_llm_client

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
FINAL_LESSON_PATH = os.path.join(OUTPUT_DIR, "final_lesson.md")
HUMAN_REVIEW_PATH = os.path.join(OUTPUT_DIR, "NEEDS_HUMAN_REVIEW.md")
RUN_SUMMARY_PATH = os.path.join(OUTPUT_DIR, "run_summary.json")
LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")
REJECTION_LOG_PATH = os.path.join(LOGS_DIR, "rejection_log.jsonl")

# ANSI Color codes for terminal logging
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def append_rejection_log(entry: Dict[str, Any]):
    """Appends an event safely to logs/rejection_log.jsonl."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    with open(REJECTION_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def finalize_rejection_logs(
    run_id: str,
    final_status: str,
    total_attempts: int,
    retry_changes: Dict[int, str]
):
    """
    Updates all rejection log entries for run_id with the final run outcome
    and the actual what_changed_on_retry explanations produced on retry.
    """
    if not os.path.exists(REJECTION_LOG_PATH):
        return

    updated_lines = []
    with open(REJECTION_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if record.get("run_id") == run_id:
                    record["final_status"] = final_status
                    record["total_attempts"] = total_attempts
                    att = record.get("attempt", 1)
                    if att in retry_changes:
                        record["what_changed_on_retry"] = retry_changes[att]
                updated_lines.append(json.dumps(record))
            except Exception:
                updated_lines.append(line.strip())

    with open(REJECTION_LOG_PATH, "w", encoding="utf-8") as f:
        for l in updated_lines:
            f.write(l + "\n")


def run_agent_pipeline(
    topic: str = "Introduction to RAG (Retrieval-Augmented Generation)",
    injected_lesson: Optional[str] = None,
    max_attempts: int = 3
) -> Generator[Dict[str, Any], None, Dict[str, Any]]:
    """
    Core state machine loop yielding real-time events.
    Shared by both CLI and Web SSE endpoints.
    """
    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()
    llm_client = get_llm_client()
    initial_api_calls = llm_client.api_call_count

    yield {
        "event": "START",
        "run_id": run_id,
        "topic": topic,
        "timestamp": started_at,
        "max_attempts": max_attempts
    }

    # 1. PLAN
    planner = PlannerAgent(llm_client=llm_client)
    yield {
        "event": "PLAN_START",
        "run_id": run_id,
        "is_mock": llm_client.is_mock,
        "message": f"Planning curriculum specification for: '{topic}'"
    }

    lesson_spec = planner.plan_lesson(topic=topic)
    yield {
        "event": "PLAN_COMPLETE",
        "run_id": run_id,
        "spec": lesson_spec
    }

    # Initialize Generator, Evaluator, Reflector
    generator = GeneratorAgent(llm_client=llm_client)
    evaluator = EvaluatorAgent(llm_client=llm_client)
    reflector = ReflectorAgent(llm_client=llm_client)

    prompt_version = generator.prompt_version
    current_lesson = ""
    previous_lesson = ""
    failed_checks: List[Dict[str, Any]] = []
    failed_history: Dict[int, List[str]] = {}
    what_changed_desc = ""
    retry_changes: Dict[int, str] = {}
    final_status = "IN_PROGRESS"
    all_accumulated_failures: List[str] = []

    # 2. GENERATE -> EVALUATE -> REGENERATE LOOP
    for attempt in range(1, max_attempts + 1):
        yield {
            "event": "ATTEMPT_START",
            "run_id": run_id,
            "attempt": attempt,
            "max_attempts": max_attempts
        }

        # Step A: Generation
        if attempt == 1 and injected_lesson:
            current_lesson = injected_lesson
            yield {
                "event": "GENERATE_INJECTED",
                "run_id": run_id,
                "attempt": attempt,
                "message": "Using deliberately injected bad lesson as Attempt 1",
                "lesson": current_lesson
            }
        else:
            yield {
                "event": "GENERATE_START",
                "run_id": run_id,
                "attempt": attempt,
                "is_retry": attempt > 1,
                "target_failed_checks": [c.get("id") for c in failed_checks]
            }

            current_lesson = generator.generate(
                lesson_spec=lesson_spec,
                attempt_number=attempt,
                previous_lesson=previous_lesson if attempt > 1 else None,
                failed_checks=failed_checks if attempt > 1 else None
            )

            if attempt > 1 and previous_lesson and failed_checks:
                what_changed_desc = generator.explain_changes(
                    previous_lesson=previous_lesson,
                    new_lesson=current_lesson,
                    failed_checks=failed_checks
                )
                retry_changes[attempt - 1] = what_changed_desc

            yield {
                "event": "GENERATE_COMPLETE",
                "run_id": run_id,
                "attempt": attempt,
                "lesson": current_lesson,
                "what_changed": what_changed_desc
            }

        # Step B: Evaluation
        yield {
            "event": "EVALUATE_START",
            "run_id": run_id,
            "attempt": attempt
        }

        eval_result = evaluator.evaluate(
            lesson_text=current_lesson,
            jargon_list=lesson_spec.get("jargon_list")
        )

        passed = eval_result["passed"]
        failed_checks = eval_result["failed_checks"]
        failed_ids = [c["id"] for c in failed_checks]
        failed_history[attempt] = failed_ids
        all_accumulated_failures.extend(failed_ids)

        yield {
            "event": "EVALUATE_COMPLETE",
            "run_id": run_id,
            "attempt": attempt,
            "passed": passed,
            "total_checks": eval_result["total_checks"],
            "passed_count": eval_result["passed_count"],
            "failed_count": eval_result["failed_count"],
            "checks": eval_result["checks"]
        }

        # Step C: Router Decision
        if passed:
            final_status = "SHIPPED"
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            with open(FINAL_LESSON_PATH, "w", encoding="utf-8") as f:
                f.write(current_lesson)

            yield {
                "event": "DECISION",
                "run_id": run_id,
                "attempt": attempt,
                "decision": "SHIP",
                "message": f"All rubric checks cleared on attempt {attempt}! Lesson shipped to output/final_lesson.md"
            }
            break
        else:
            # Rejection logging
            rejection_record = {
                "run_id": run_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "is_mock": llm_client.is_mock,
                "attempt": attempt,
                "prompt_version": prompt_version,
                "failed_check_ids": failed_ids,
                "check_details": [
                    {
                        "id": c["id"],
                        "name": c["name"],
                        "reason": c["reason"],
                        "evidence": c.get("evidence", ""),
                        "fix_suggestion": c.get("fix_suggestion", "")
                    }
                    for c in failed_checks
                ],
                "what_changed_on_retry": what_changed_desc if attempt > 1 else "Initial rejection",
                "final_status": "RETRYING" if attempt < max_attempts else "NEEDS_HUMAN_REVIEW",
                "total_attempts": attempt
            }
            append_rejection_log(rejection_record)

            if attempt < max_attempts:
                yield {
                    "event": "DECISION",
                    "run_id": run_id,
                    "attempt": attempt,
                    "decision": "RETRY",
                    "failed_checks": failed_ids,
                    "retries_left": max_attempts - attempt,
                    "message": f"Attempt {attempt} failed {len(failed_ids)} check(s). Regenerating with targeted feedback..."
                }
                previous_lesson = current_lesson
            else:
                final_status = "NEEDS_HUMAN_REVIEW"
                os.makedirs(OUTPUT_DIR, exist_ok=True)
                review_content = f"# NEEDS HUMAN REVIEW\n\n"
                review_content += f"**Run ID**: {run_id}\n"
                review_content += f"**Timestamp**: {datetime.now(timezone.utc).isoformat()}\n"
                review_content += f"**Attempts Exhausted**: {attempt}/{max_attempts}\n"
                review_content += f"**Unresolved Check Failures**: {', '.join(failed_ids)}\n\n"
                review_content += "## Diagnostic Report\n"
                for fc in failed_checks:
                    review_content += f"### Check [{fc['id']}]: {fc['name']}\n"
                    review_content += f"- **Reason**: {fc['reason']}\n"
                    if fc.get("evidence"):
                        review_content += f"- **Evidence**: `{fc['evidence']}`\n"
                    if fc.get("fix_suggestion"):
                        review_content += f"- **Fix Suggestion**: {fc['fix_suggestion']}\n\n"
                review_content += "---\n\n## Candidate Lesson Text\n\n" + current_lesson

                with open(HUMAN_REVIEW_PATH, "w", encoding="utf-8") as f:
                    f.write(review_content)

                yield {
                    "event": "DECISION",
                    "run_id": run_id,
                    "attempt": attempt,
                    "decision": "NEEDS_HUMAN_REVIEW",
                    "message": f"Maximum attempts ({max_attempts}) reached without clearing all checks. Saved to output/NEEDS_HUMAN_REVIEW.md"
                }

    # Finalize rejection log statuses and explanations
    finalize_rejection_logs(
        run_id=run_id,
        final_status=final_status,
        total_attempts=attempt,
        retry_changes=retry_changes
    )

    # 3. REFLECTOR & METRICS
    run_source = "injected_test" if injected_lesson else "generator"
    reflector_stats = reflector.record_run(
        attempts=attempt,
        passed=(final_status == "SHIPPED"),
        all_failed_check_ids=all_accumulated_failures,
        source=run_source
    )

    total_api_calls = llm_client.api_call_count - initial_api_calls
    summary_data = {
        "run_id": run_id,
        "topic": topic,
        "is_mock": llm_client.is_mock,
        "timestamp": started_at,
        "total_attempts": attempt,
        "final_status": final_status,
        "failed_checks_by_attempt": failed_history,
        "total_api_calls": total_api_calls,
        "prompt_version": prompt_version,
        "learned_rules_count": len(atomic_read_json(os.path.join(os.path.dirname(__file__), "memory", "learned_rules.json"), []))
    }
    atomic_write_json(RUN_SUMMARY_PATH, summary_data)

    yield {
        "event": "COMPLETE",
        "run_id": run_id,
        "status": final_status,
        "attempts": attempt,
        "summary": summary_data,
        "stats": reflector_stats
    }

    return summary_data


def print_cli_banner():
    llm = get_llm_client()
    print(f"\n{BOLD}{CYAN}===================================================================={RESET}")
    print(f"{BOLD}{CYAN}   rag-lesson-agent | Self-Evaluating Content Generation System      {RESET}")
    print(f"{BOLD}{CYAN}===================================================================={RESET}")
    if llm.is_mock:
        print(f"{BOLD}{YELLOW}⚠️  [OFFLINE MOCK MODE ACTIVE]{RESET}")
        print(f"   No GEMINI_API_KEY detected in .env. Outputs are generated offline.")
        print(f"   Add your key to .env (from https://aistudio.google.com/) for live AI.")
    else:
        from llm import DEFAULT_GENERATOR_MODEL, DEFAULT_JUDGE_MODEL
        print(f"{BOLD}{GREEN}✨ [LIVE GEMINI API CONNECTED]{RESET}")
        print(f"   Generator Model: {DEFAULT_GENERATOR_MODEL} | Judge Model: {DEFAULT_JUDGE_MODEL}")
    print(f"{CYAN}--------------------------------------------------------------------{RESET}\n")


def print_check_table(checks: List[Dict[str, Any]]):
    print(f"\n{BOLD}{'ID':<6} {'TYPE':<6} {'STATUS':<8} {'CHECK NAME':<38} {'EVIDENCE / DETAILS'}{RESET}")
    print("-" * 90)
    for c in checks:
        status_color = GREEN if c["passed"] else RED
        status_text = f"{status_color}{'PASS' if c['passed'] else 'FAIL'}{RESET}"
        type_badge = f"[{c.get('type', 'llm').upper()}]"
        name = c.get("name", "")[:36]
        details = c.get("reason", "")
        if not c["passed"] and c.get("evidence"):
            details = f"Quote: \"{c['evidence'][:35]}...\" | {details}"
        if c.get("judge_evidence_unverified"):
            details = f"[Unverified Quote Flag] {details}"
        print(f"{c.get('id'):<6} {type_badge:<6} {status_text:<17} {name:<38} {details[:45]}")
    print("-" * 90)


def main():
    parser = argparse.ArgumentParser(description="Self-Evaluating Lesson Content Generator CLI")
    parser.add_argument("--topic", type=str, default="Introduction to RAG (Retrieval-Augmented Generation)", help="Lesson topic to generate")
    parser.add_argument("--inject-bad", type=str, help="Path to deliberate bad lesson markdown to inject as Attempt 1")
    parser.add_argument("--evaluate-only", type=str, help="Evaluate a markdown lesson file directly without running generation")
    parser.add_argument("--stats", action="store_true", help="Print cumulative failure memory stats and exit")
    parser.add_argument("--serve", action="store_true", help="Start the FastAPI web interface with SSE stream")

    args = parser.parse_args()

    # Mode 1: Serve Web App
    if args.serve:
        print_cli_banner()
        print(f"{GREEN}Starting FastAPI Web Interface on http://127.0.0.1:8000 ...{RESET}")
        import uvicorn
        uvicorn.run("web.app:app", host="127.0.0.1", port=8000, reload=False)
        return

    # Mode 2: Show Cumulative Memory Stats
    if args.stats:
        print_cli_banner()
        stats_path = os.path.join(os.path.dirname(__file__), "memory", "failure_stats.json")
        rules_path = os.path.join(os.path.dirname(__file__), "memory", "learned_rules.json")
        proposals_path = os.path.join(os.path.dirname(__file__), "memory", "proposed_rubric_changes.json")

        stats = atomic_read_json(stats_path, {})
        rules = atomic_read_json(rules_path, [])
        proposals = atomic_read_json(proposals_path, [])

        print(f"{BOLD}Cumulative System Memory & Learning Analytics:{RESET}\n")
        print(f"Total Runs:          {stats.get('total_runs', 0)}")
        print(f"Successful Ships:    {stats.get('successful_runs', 0)}")
        print(f"Human Review Flags:  {stats.get('human_review_runs', 0)}")
        print(f"Attempts History:    {stats.get('attempts_history', [])[-10:]}")
        print(f"\n{BOLD}Check Failure Distribution:{RESET}")
        for cid, count in stats.get("check_failures", {}).items():
            print(f"  - Check {cid:<5}: {count} failure(s)")

        print(f"\n{BOLD}Active Learned Generator Rules ({len(rules)}):{RESET}")
        for r in rules:
            print(f"  [{r.get('id')}] (from {r.get('created_from_check')}): {r.get('rule_text')}")

        print(f"\n{BOLD}Proposed Rubric Changes Quarantined for Human Review ({len(proposals)}):{RESET}")
        for p in proposals:
            print(f"  [{p.get('id')}] For {p.get('check_id')}: {p.get('proposal')} (Status: {p.get('status')})")
        return

    # Mode 3: Evaluate Only
    if args.evaluate_only:
        print_cli_banner()
        if not os.path.exists(args.evaluate_only):
            print(f"{RED}Error: File not found: {args.evaluate_only}{RESET}")
            sys.exit(1)
        with open(args.evaluate_only, "r", encoding="utf-8") as f:
            content = f.read()
        print(f"Evaluating lesson file: {args.evaluate_only} ({len(content)} characters)...\n")
        evaluator = EvaluatorAgent()
        res = evaluator.evaluate(content)
        print_check_table(res["checks"])
        if res["passed"]:
            print(f"\n{GREEN}{BOLD}Result: 100% PASS - Ready to Ship!{RESET}\n")
        else:
            print(f"\n{RED}{BOLD}Result: REJECTED ({res['failed_count']}/{res['total_checks']} failed checks){RESET}\n")
        return

    # Mode 4: End-to-End Pipeline
    print_cli_banner()
    injected_content = None
    if args.inject_bad:
        if not os.path.exists(args.inject_bad):
            print(f"{RED}Error: Injected file not found: {args.inject_bad}{RESET}")
            sys.exit(1)
        with open(args.inject_bad, "r", encoding="utf-8") as f:
            injected_content = f.read()
        print(f"{YELLOW}{BOLD}[DEMO MODE] Injecting deliberate bad lesson: {args.inject_bad}{RESET}\n")

    print(f"Input Topic: {BOLD}{args.topic}{RESET}\n")

    for event in run_agent_pipeline(topic=args.topic, injected_lesson=injected_content):
        etype = event.get("event")

        if etype == "PLAN_START":
            print(f"{CYAN}[PLAN]{RESET} Analyzing learner profile and grounding facts...")
        elif etype == "PLAN_COMPLETE":
            print(f"{GREEN}[PLAN]{RESET} Curriculum spec generated. Analogy: '{event['spec'].get('analogy')}'.")
        elif etype == "GENERATE_INJECTED":
            print(f"\n{YELLOW}[GENERATE - Attempt {event['attempt']}]{RESET} Injected bad lesson loaded into evaluation loop.")
        elif etype == "GENERATE_START":
            if event.get("is_retry"):
                print(f"\n{YELLOW}[REGENERATE - Attempt {event['attempt']}]{RESET} Revising failed checks: {event['target_failed_checks']}...")
            else:
                print(f"\n{CYAN}[GENERATE - Attempt {event['attempt']}]{RESET} Drafting lesson in simple English with Indian context...")
        elif etype == "GENERATE_COMPLETE":
            if event.get("what_changed"):
                print(f"  {BOLD}What changed on retry:{RESET} {event['what_changed']}")
        elif etype == "EVALUATE_START":
            print(f"{CYAN}[EVALUATE - Attempt {event['attempt']}]{RESET} Executing dual-layer checks (Code checks + Zero-temp LLM Judge)...")
        elif etype == "EVALUATE_COMPLETE":
            print_check_table(event["checks"])
            print(f"  Score: {event['passed_count']}/{event['total_checks']} checks passed.")
        elif etype == "DECISION":
            decision = event.get("decision")
            if decision == "SHIP":
                print(f"\n{GREEN}{BOLD}[DECISION: SHIP]{RESET} {event['message']}")
            elif decision == "RETRY":
                print(f"\n{YELLOW}{BOLD}[DECISION: REJECT & RETRY]{RESET} {event['message']}")
            elif decision == "NEEDS_HUMAN_REVIEW":
                print(f"\n{RED}{BOLD}[DECISION: HUMAN REVIEW]{RESET} {event['message']}")
        elif etype == "COMPLETE":
            print(f"\n{BOLD}Pipeline Complete.{RESET} Run ID: {event['run_id']} | Final Status: {event['status']} | Total Attempts: {event['attempts']}")
            print(f"Summary persisted to {RUN_SUMMARY_PATH}\n")


if __name__ == "__main__":
    main()

