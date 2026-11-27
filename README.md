# SyncFlow AI

**Beyond Prompt-and-Wait: A Human-Steerable AI Agent Collaboration Platform**

Built for Resurrect 2026, Problem Statement 3 (Human-Agent Interaction).

SyncFlow AI replaces the conventional "submit a prompt, wait for a final
answer" interaction with an **interruptible, inspectable, human-steerable**
multi-agent workspace: you watch a Planner→Research→Verification→Reporter
pipeline execute live, pause it mid-task, redirect it to a different
subject, and approve or reject its final output before it's considered done
— all enforced by the backend, not just the UI.

## Quick start

### 1. Backend
```bash
cd backend
cp .env.example .env            # optional: add ANTHROPIC_API_KEY for live LLM mode
pip install -r requirements.txt --break-system-packages
uvicorn app.main:app --reload --port 8000
```
Runs fully without an API key, in **deterministic fallback mode** — every
agent output is clearly labeled `[Deterministic demo]` rather than faking
real retrieval.

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:3000.

### 3. Run the demo
See [`docs/demo_script.md`](docs/demo_script.md) for a step-by-step,
repeatable walkthrough (pause → redirect → resume → approve).

### 4. Run tests
```bash
cd backend
pytest -q
```
7 integration tests cover the state machine, the happy path to completion,
pause→redirect→resume, redirect-rejected-when-not-paused, cancel, approval
rejection, and duplicate-start protection — all passing as of this prototype.

## Project structure
```
syncflow-ai/
    frontend/     Next.js + TypeScript + Tailwind + React Flow dashboard
    backend/      FastAPI + SQLAlchemy(async/SQLite) coordinator & agents
    evaluation/   System A vs System B comparison protocol + analysis script
    docs/         architecture, API contract, demo script, limitations
```

## What's real vs. simulated
- The **state machine, coordinator, pause/resume/redirect/cancel,
  approval gate, and event history are fully real** — backend-enforced,
  tested (`pytest`), and verified end-to-end via live HTTP calls (not mocks).
- **Agent content** (research findings, verification checks, final reports)
  is either (a) real LLM output, if you set `ANTHROPIC_API_KEY`, or
  (b) clearly-labeled deterministic placeholder text otherwise. The system
  never presents simulated content as real.
- **Evaluation results** are a methodology + working analysis script with an
  empty data template — no human trials have been run, so no numbers are
  reported. See [`evaluation/results.md`](evaluation/results.md).

See [`docs/limitations.md`](docs/limitations.md) for the full, honest list
of what's not yet built.

## Documentation
- [`docs/architecture.md`](docs/architecture.md) — how the coordinator,
  state machine, and agents fit together, and why.
- [`docs/api_contract.md`](docs/api_contract.md) — every REST endpoint and
  WebSocket message shape.
- [`docs/demo_script.md`](docs/demo_script.md) — the repeatable demo.
- [`docs/limitations.md`](docs/limitations.md) — honest gaps.
- [`evaluation/`](evaluation/) — baseline protocol, task definitions,
  participant data template, and the metric calculation script.
