"""
System A — conventional prompt-and-wait baseline, for comparison against
SyncFlow AI (System B).

This is intentionally minimal: one goal in, one blocking call out, no plan
visibility, no pause/redirect/approval. It reuses the same deterministic
fallback / live-LLM logic as SyncFlow AI's Reporter agent so the two systems
are compared on *interaction model*, not on prompt quality or model choice.

Usage:
    python baseline_app.py "Research three electric vehicle companies..."
"""
import sys
import asyncio
import time

sys.path.insert(0, "../backend")
from app.agents import planner, workers  # noqa: E402


async def run_baseline(goal: str):
    start = time.time()
    print("Submitted. Waiting for the system to finish (no visibility into progress)...")

    tasks_spec, _used_llm = await planner.generate_plan(goal)
    research_tasks = [t for t in tasks_spec if t["agent"] == "research"]

    research_outputs = []
    for t in research_tasks:
        out = await workers.run_research(t["name"], goal)
        research_outputs.append(out)

    verification = await workers.run_verification([o["result"] for o in research_outputs], goal)
    report = await workers.run_reporter(research_outputs + [verification], goal)

    elapsed = time.time() - start
    print(f"\n--- Final report (only output the human ever sees) ---\n{report['result']}")
    print(f"\n[System A] total time: {elapsed:.1f}s, no intermediate visibility, "
          f"no redirect possible without cancelling and restarting from scratch.")


if __name__ == "__main__":
    goal = sys.argv[1] if len(sys.argv) > 1 else (
        "Research three electric vehicle companies, compare their products, "
        "verify important claims, and prepare a report."
    )
    asyncio.run(run_baseline(goal))
