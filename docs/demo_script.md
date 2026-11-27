# SyncFlow AI — Demo Script (repeatable, deterministic fallback mode)

No API key required — this runs entirely on the deterministic fallback
agents, which is honest about being a structural demonstration (every
result is labeled `[Deterministic demo]`), not live retrieval.

## Setup
```
# Terminal 1
cd backend
cp .env.example .env
pip install -r requirements.txt --break-system-packages
export SYNCFLOW_SIMULATED_WORK_SECONDS=3   # gives you time to click Pause
uvicorn app.main:app --reload --port 8000

# Terminal 2
cd frontend
npm install
npm run dev
```
Open http://localhost:3000.

## Script
1. On the goal screen, click the first example goal: *"Research three
   electric vehicle companies, compare their products, verify important
   claims, and prepare a report."*
2. The Planner Agent runs, the workflow graph renders 6 nodes (3 research →
   compare → verify → report). Watch the first node turn cyan ("running").
3. While "Research Subject A" is running, click **Pause** in the control
   bar. The status pill turns amber (PAUSED). The in-flight task is allowed
   to finish — this is the backend-enforced "safe checkpoint," not an
   instant freeze.
4. Click **Redirect**. Type: *"Exclude Subject C and research Subject D
   instead."* Click **Apply redirect**. In the graph, the "Research Subject
   C" node dims and shows `skipped`; a new `[Redirected] ...` node appears
   in its place, and the "Compare results" node's incoming edge now points
   at the new node instead.
5. Click **Resume**. Execution continues through compare → verify.
6. When the Reporter agent finishes, a modal appears: **Human approval
   required**, showing the proposed action, expected impact, and evidence.
   This is a real gate — the report is not marked complete until you act.
7. Click **Approve**. The session status turns green (COMPLETED). Click the
   final report node to see its full `result`, `explanation`, `evidence`,
   `uncertainty`, and `limitations` in the Task Inspector.
8. Scroll the Event History panel at the bottom — every step from
   `session_created` through `approval_granted` to `session_completed` is
   there, each with a timestamp and actor.

## Alternate ending: Reject
Repeat steps 1–6, then click **Reject** instead. The session status turns
red (FAILED), and the event history shows `approval_rejected` — SyncFlow AI
never silently finishes a session whose consequential action was rejected.

## Alternate ending: Cancel mid-flight
At any point, click **Cancel**. The status turns grey (CANCELLED) and no
further tasks execute, even ones already `pending`.
