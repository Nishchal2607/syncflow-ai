# SyncFlow AI — API Contract

Base URL: `http://localhost:8000`

## REST endpoints

### `GET /api/health`
Returns `{ "status": "ok", "mode": "llm" | "deterministic_fallback" }`.

### `POST /api/sessions`
Body: `{ "goal": string }`
Creates a session in `IDLE` state. Returns `SessionOut` (tasks empty).

### `POST /api/sessions/{id}/start`
Transitions `IDLE → PLANNING → RUNNING`, invokes the Planner Agent, persists
the task graph, and starts the coordinator's execution loop. Returns the
full `SessionOut` including tasks.
- `404` if session not found.
- `409` if the session isn't in a startable state (duplicate `/start` calls
  while already running are a silent no-op, not an error).

### `GET /api/sessions/{id}`
Returns the session with its current tasks.

### `POST /api/sessions/{id}/pause`
Valid only from `RUNNING`. `409` otherwise.

### `POST /api/sessions/{id}/resume`
Valid only from `PAUSED`. `409` otherwise.

### `POST /api/sessions/{id}/redirect`
Body: `{ "task_id"?: string, "instruction": string }`
Valid only while `PAUSED` (`409` with an explanatory message otherwise,
since redirect requires the loop to be blocked at a safe checkpoint).
Mutates the task graph: marks the target task `skipped`, inserts a new task
at the same position, and rewires dependent tasks' `depends_on` lists.

### `POST /api/sessions/{id}/cancel`
Valid from any non-terminal state. Sets `CANCELLED` and stops the loop.

### `POST /api/approvals/{approval_id}/approve`
Marks the approval `approved`, the gated task `completed`, and resumes the
session (`AWAITING_APPROVAL → RUNNING`) so the loop can finish.

### `POST /api/approvals/{approval_id}/reject`
Marks the approval `rejected`, the gated task `failed`, and the session
`FAILED`.

### `GET /api/sessions/{id}/events`
Returns the full, ordered event history for the session.

## WebSocket

### `/ws/sessions/{id}`
Server pushes JSON messages of these shapes as they happen (no inbound
messages expected from the client):

```jsonc
{"type": "session_status", "status": "RUNNING", "session_id": "..."}
{"type": "task_update", "task": { ...full Task row... }}
{"type": "event", "event": { ...full Event row... }}
{"type": "approval_request", "approval": { ...full Approval row... }}
{"type": "approval_resolved", "approval_id": "...", "status": "approved" | "rejected"}
```

## Schemas
See `backend/app/schemas/schemas.py` for the full Pydantic models
(`SessionOut`, `TaskOut`, `EventOut`, `ApprovalOut`, `RedirectRequest`).
