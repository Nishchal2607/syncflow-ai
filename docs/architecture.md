# SyncFlow AI — Architecture

## Overview
SyncFlow AI is a human-steerable multi-agent workspace. A single backend
**Coordinator** drives one asyncio execution loop per session through a
shared, persisted task graph. The frontend observes and steers that loop
via REST (commands) and WebSocket (live state).

```
┌─────────────┐      REST (commands)       ┌───────────────────────────┐
│  Next.js UI │ ─────────────────────────▶ │   FastAPI backend          │
│ (React Flow,│                             │                            │
│  dashboard) │ ◀───────────────────────── │  Coordinator (state        │
└─────────────┘      WebSocket (events)     │  machine + asyncio loop)   │
                                             │         │                  │
                                             │         ▼                  │
                                             │  Planner / Research /      │
                                             │  Verification / Reporter  │
                                             │  agents (LLM or            │
                                             │  deterministic fallback)   │
                                             │         │                  │
                                             │         ▼                  │
                                             │  SQLite (sessions, tasks,  │
                                             │  events, approvals)        │
                                             └───────────────────────────┘
```

## Why a single coordinator loop per session
The spec requires that pause/resume/redirect/cancel are *enforced by the
backend*, not just a UI state. A single `asyncio.Task` per session, guarded
by a per-session lock (so duplicate `/start` calls can't spawn a second
loop) and an `asyncio.Event` used as a pause gate, gives us:
- A single safe checkpoint (between tasks) where PAUSE takes effect.
- REDIRECT is only accepted while PAUSED, which guarantees the loop is
  blocked and cannot race the task-graph mutation.
- CANCEL sets a flag and cancels the asyncio task outright; it is allowed
  from any non-terminal state.

## State machine
`app/orchestration/state_machine.py` is the single source of truth for
legal transitions (see the table in the module). The coordinator always
calls `transition()` before writing a new status; every API route surfaces
an `InvalidTransition` as an HTTP 409, so illegal commands from the UI (e.g.
redirecting a RUNNING session) are rejected, not silently ignored.

## Agents
Each of the four agent roles (`app/agents/`) returns a single structured
output: `result`, `explanation`, `evidence`, `uncertainty`, `limitations`,
and `agent` (identity). This is the Trust & Transparency contract the UI
renders in the Task Inspector. In **deterministic fallback mode** (no
`ANTHROPIC_API_KEY` configured) every agent still returns this exact shape,
but clearly labels its result as `[Deterministic demo]` and sets
`uncertainty: "high"` — the system never pretends simulated output is real
retrieval.

## Human-in-the-loop mechanics
- **PAUSE**: backend transitions RUNNING→PAUSED and clears the loop's resume
  event; the in-flight task is allowed to finish (so nothing is half-executed)
  and the loop blocks before starting the next one.
- **RESUME**: PAUSED→RUNNING, sets the resume event; if the loop task had
  exited, a new one is spawned that resumes from the persisted task graph
  (no serialized "state blob" needed — Postgres/SQLite *is* the state).
- **REDIRECT**: only while PAUSED. Marks the target task `skipped`, inserts a
  new task in its place, and rewires every downstream task's `depends_on`
  list from the old task id to the new one. This is a real graph mutation,
  not a renamed label.
- **APPROVAL**: the Reporter's output is held as `running` (not `completed`)
  until a human calls `/approve`; rejection marks the task `failed` and the
  session `FAILED` rather than silently completing.

## Data model
See `app/database/models.py`. Four tables: `sessions`, `tasks`, `events`,
`approvals`. Events are append-only and are the backbone of the Event
History UI panel — every important state change is both persisted and
broadcast over the session's WebSocket in the same transaction.

## Known simplification
The coordinator's per-session runtime control (`SessionControl`, the
`asyncio.Lock`/`Event`) lives in-process memory, not in SQLite. This means
a backend process restart loses in-flight *execution* (though all
persisted state — tasks, events, approvals — survives). For a hackathon
timeframe this is an accepted, documented trade-off; a production version
would move the pause/resume signal into the DB or a message queue so any
worker process could pick the session back up.
