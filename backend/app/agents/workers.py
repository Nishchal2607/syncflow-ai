"""
Research, Verification and Reporter agents.

Every agent returns a structured output dict with the Trust & Transparency
fields required by the spec: result, explanation, evidence, uncertainty,
limitations, agent identity. In deterministic (no API key) mode these are
clearly labelled as a deterministic demonstration rather than live retrieval,
per the "do not fabricate evidence" rule.
"""
import asyncio
import json
import os
from datetime import datetime, timezone
from app.agents.llm_client import MODEL, PROVIDER, complete_json, is_live
from app.evidence import retrieve, verify_claim

# Deterministic-mode tasks are near-instant by default, which leaves no real
# window for a human to pause/redirect mid-execution. We simulate realistic
# agent latency so PAUSE/REDIRECT are exercising actual concurrency, not just
# a lucky race. Configurable so tests can set it to 0.
SIMULATED_WORK_SECONDS = float(os.getenv("SYNCFLOW_SIMULATED_WORK_SECONDS", "3"))


async def _simulate_work():
    if not is_live() and SIMULATED_WORK_SECONDS > 0:
        await asyncio.sleep(SIMULATED_WORK_SECONDS)


async def run_research(task_name: str, goal: str) -> dict:
    subject = task_name.replace("Research ", "").strip()
    system = """You are the Research Agent in SyncFlow AI. Research the given
subject in the context of the user's overall goal. Return JSON:
{"result": "2-4 sentence summary", "explanation": "why you concluded this",
 "evidence": ["source or reasoning point 1", "source or reasoning point 2"],
 "uncertainty": "low|medium|high", "limitations": "short note on what you could not verify"}
Do not invent specific statistics or citations you are not confident in;
if you lack real retrieval tools, say so in limitations and keep uncertainty
at medium or high."""
    if is_live():
        result = await complete_json(system, f"Goal: {goal}\nSubject: {subject}")
        if result and "result" in result:
            return {
                "result": result.get("result", ""),
                "explanation": result.get("explanation", ""),
                "evidence": result.get("evidence", []),
                "uncertainty": result.get("uncertainty", "medium"),
                "limitations": result.get("limitations", "Model-generated; not a live web search."),
                "agent": "research",
                "is_live": True,
            }
    await _simulate_work()
    sources = retrieve(subject + " " + goal)
    status = verify_claim(subject, sources)
    return {
        "result": f"[Deterministic demo] Compiled a placeholder research profile for {subject}: "
                   f"product line-up, market positioning, and publicly discussed strengths/weaknesses.",
        "explanation": "No LLM/API key configured, so this task ran in deterministic fallback mode "
                       "and did not perform real retrieval.",
        "evidence": sources or [{
            "status": "insufficient_evidence",
            "title": "Local controlled collection",
            "url": "local://collection",
            "document_id": "local-none",
            "excerpt": "No matching controlled-document evidence was found.",
            "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
        }],
        "uncertainty": "high",
        "limitations": "This is a simulated result for demo purposes, not verified real-world data.",
        "agent": "research",
        "is_live": False,
    }


async def run_verification(context_summaries: list[str], goal: str) -> dict:
    system = """You are the Verification Agent in SyncFlow AI. Review the
research summaries provided and flag which claims look well supported vs.
uncertain. Return JSON:
{"result": "2-4 sentence verification summary", "explanation": "...",
 "evidence": ["point checked 1", "point checked 2"],
 "uncertainty": "low|medium|high", "limitations": "..."}
Be explicit that you are checking internal consistency, not performing
independent live fact-checking, unless real tools are available to you."""
    if is_live():
        joined = "\n".join(f"- {s}" for s in context_summaries)
        result = await complete_json(system, f"Goal: {goal}\nResearch summaries:\n{joined}")
        if result and "result" in result:
            return {
                "result": result.get("result", ""),
                "explanation": result.get("explanation", ""),
                "evidence": result.get("evidence", []),
                "uncertainty": result.get("uncertainty", "medium"),
                "limitations": result.get("limitations", ""),
                "agent": "verification",
                "is_live": True,
            }
    await _simulate_work()
    return {
        "result": "[Deterministic demo] Cross-checked the research summaries for internal consistency; "
                   "no contradictions detected among the simulated findings.",
        "explanation": "Deterministic fallback: this agent did not perform independent, live fact-checking.",
        "evidence": [f"checked {len(context_summaries)} research outputs for consistency"],
        "uncertainty": "high",
        "limitations": "Simulated verification only — treat as a placeholder, not a real audit.",
        "agent": "verification",
        "is_live": False,
    }


async def run_reporter(all_results: list[dict], goal: str) -> dict:
    system = """You are the Reporter Agent in SyncFlow AI. Produce a clear,
detailed answer to the user's goal using only the supplied agent outputs.
Return JSON with:
{"result": "the direct answer, with a concise summary, detailed findings, and useful next steps",
 "explanation": "a detailed account of the inputs used, the role of each agent,
 how findings were compared or checked, and which tools were or were not used",
 "evidence": ["only evidence items present in the supplied agent outputs"],
 "uncertainty": "low|medium|high", "limitations": "specific caveats"}

Do not invent facts, statistics, citations, URLs, source names, or tools.
The workflow has no live web search or browsing tool. Distinguish model
reasoning from independently verified evidence. If source evidence is missing
or weak, say so plainly and set uncertainty to high. Write the answer and
explanation in readable prose with short paragraphs, not markdown code blocks."""
    if is_live():
        report_context = {
            "goal": goal,
            "provider": PROVIDER,
            "model": MODEL,
            "available_tools": [
                f"{PROVIDER} API for language generation using {MODEL}",
                "No live web search or browsing tool is configured",
            ],
            "prior_agent_outputs": [
                {
                    "agent": item.get("agent"),
                    "result": item.get("result", ""),
                    "explanation": item.get("explanation", ""),
                    "evidence": item.get("evidence", []),
                    "uncertainty": item.get("uncertainty", "unknown"),
                    "limitations": item.get("limitations", ""),
                }
                for item in all_results
            ],
        }
        result = await complete_json(
            system,
            json.dumps(report_context, ensure_ascii=False, default=str),
            max_tokens=2800,
        )
        if result and "result" in result:
            return {
                "result": result.get("result", ""),
                "explanation": result.get("explanation", ""),
                "evidence": result.get("evidence", []),
                "uncertainty": result.get("uncertainty", "medium"),
                "limitations": result.get("limitations", ""),
                "agent": "reporter",
                "is_live": True,
            }
    await _simulate_work()
    bullets = "; ".join(r.get("result", "")[:80] for r in all_results)
    return {
        "result": f"[Deterministic demo] Final report synthesized from {len(all_results)} prior "
                  f"task outputs: {bullets}",
        "explanation": "Deterministic fallback: assembled from placeholder agent outputs, not live data.",
        "evidence": ["aggregated from upstream task results"],
        "uncertainty": "high",
        "limitations": "This report is a structural demonstration, not a factual deliverable.",
        "agent": "reporter",
        "is_live": False,
    }
