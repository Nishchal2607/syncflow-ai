"""Planner Agent: converts a user's goal into a structured task graph."""
import re
from app.agents.llm_client import complete_json, is_live

SYSTEM_PROMPT = """You are the Planner Agent inside SyncFlow AI, a human-steerable
multi-agent workspace. Convert the user's goal into a structured task graph.

Return JSON of this exact shape:
{
  "tasks": [
    {"name": "...", "agent": "research|verification|reporter", "depends_on_index": [list of 0-based indices into this same array]}
  ]
}
Keep it to 4-8 tasks. Research tasks should come first (one per distinct subject
mentioned in the goal), then a verification task depending on all research
tasks, then a final reporter task depending on verification.
"""


def _extract_subjects(goal: str) -> list[str]:
    """Deterministic fallback: naive extraction of subjects to research."""
    # look for patterns like "three X companies" or comma separated lists
    # Try to find explicit named entities first (capitalized multi-word runs)
    candidates = re.findall(r"\b([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?)\b", goal)
    stop = {"Research", "Compare", "Verify", "Generate", "Prepare", "The", "A", "An"}
    named = [c for c in candidates if c not in stop]
    if len(named) >= 2:
        # de-dup, keep order
        seen = []
        for n in named:
            if n not in seen:
                seen.append(n)
        return seen[:4]

    # otherwise default to a generic 3-subject demo (matches hackathon demo scenario)
    m = re.search(r"\b(two|three|four|five|\d+)\b", goal.lower())
    count = {"two": 2, "three": 3, "four": 4, "five": 5}.get(m.group(1), 3) if m else 3
    try:
        count = int(count)
    except (TypeError, ValueError):
        count = 3
    count = max(2, min(count, 4))
    return [f"Subject {chr(65 + i)}" for i in range(count)]


def deterministic_plan(goal: str) -> list[dict]:
    subjects = _extract_subjects(goal)
    tasks: list[dict] = []
    research_indices = []
    for subj in subjects:
        tasks.append({
            "name": f"Research {subj}",
            "agent": "research",
            "depends_on_index": [],
        })
        research_indices.append(len(tasks) - 1)

    tasks.append({
        "name": "Compare results",
        "agent": "research",
        "depends_on_index": research_indices,
    })
    compare_idx = len(tasks) - 1

    tasks.append({
        "name": "Verify information",
        "agent": "verification",
        "depends_on_index": [compare_idx],
    })
    verify_idx = len(tasks) - 1

    tasks.append({
        "name": "Generate final report",
        "agent": "reporter",
        "depends_on_index": [verify_idx],
    })
    return tasks


async def generate_plan(goal: str) -> tuple[list[dict], bool]:
    """
    Returns (tasks, used_llm).
    tasks: list of {"name", "agent", "depends_on_index"}
    """
    if is_live():
        result = await complete_json(SYSTEM_PROMPT, f"Goal: {goal}")
        if result and isinstance(result.get("tasks"), list) and len(result["tasks"]) > 0:
<<<<<<< HEAD
            tasks = result["tasks"]
            if valid_plan(tasks):
                return tasks, True
    return deterministic_plan(goal), False


def valid_plan(tasks):
    if not isinstance(tasks, list) or not tasks or len(tasks) > 32:
        return False
    for i, task in enumerate(tasks):
        if not isinstance(task, dict) or not isinstance(task.get("name"), str) or not task["name"].strip():
            return False
        if task.get("agent") not in ("research", "verification", "reporter"):
            return False
        deps = task.get("depends_on_index", [])
        if not isinstance(deps, list) or any(type(d) is not int or not 0 <= d < i for d in deps) or len(set(deps)) != len(deps):
            return False
    return tasks[-1]["agent"] == "reporter" and sum(t["agent"] == "reporter" for t in tasks) == 1
=======
            valid = []
            for t in result["tasks"]:
                if "name" in t and t.get("agent") in ("research", "verification", "reporter"):
                    valid.append({
                        "name": str(t["name"])[:200],
                        "agent": t["agent"],
                        "depends_on_index": t.get("depends_on_index", []) or [],
                    })
            if valid:
                return valid, True
    return deterministic_plan(goal), False
>>>>>>> ff3b8e6d1f4bd3c8d0eb54f5fb1847df4306cdb3
