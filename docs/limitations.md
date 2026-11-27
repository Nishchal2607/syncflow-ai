# Known Limitations

This is a 12-hour hackathon prototype. Documented honestly, per the project
rules ("do not fabricate results or evidence", "do not claim a feature is
implemented until tested").

## Execution engine
- Per-session execution control (`SessionControl`) is in-process memory.
  Pending approvals survive restart and are replayed through WebSocket
  snapshots, while running/planning sessions are intentionally failed closed
  during recovery. Automatic replay of running work is not enabled.
- Redirect currently supports one operation: skip-and-replace a single task.
  It does not support richer graph edits (e.g. inserting a task in the
  middle of an already-completed chain, or multi-task redirects in one call).
- The planner's deterministic fallback uses a naive regex-based subject
  extractor; it does not understand the goal as well as a real LLM would.
  With `ANTHROPIC_API_KEY` set, the Planner/Research/Verification/Reporter
  agents use the live Anthropic API for materially better plans and results.

## Agents
- In deterministic fallback mode, "research," "verification" and "report"
  content is simulated placeholder text, clearly labeled as such. It is not
  real retrieval and must never be treated as factual output.
- Even in live-LLM mode, the agents currently have no real external tools
  (no actual web search/browsing), so "research" is the model's own
  knowledge, not live retrieval — the `limitations` field on each task
  output says so.

## Evaluation module
- No human-subject trials have been run. `participant_data.csv` is an empty
  template; `results.md` contains no numbers, only the table structure
  `analysis.py` will populate once real data exists.
- `analysis.py` does not run a formal significance test (e.g. paired
  Wilcoxon) by default, to avoid implying statistical significance on data
  that doesn't exist yet. This is a documented, intentional gap.

## Frontend
- No persistent session list / history browsing across page reloads yet
  (the sidebar shows only the current session's id). A session can still be
  reloaded directly via its REST id if the id is known.
- No automated frontend integration tests (Playwright/Cypress) yet — frontend
  verification so far is a successful production build (`npm run build`) plus
  manual API-driven smoke testing of the running dev/prod server.
- Mobile/narrow-viewport layout is not optimized; the desktop two/three-pane
  layout is the supported target.

## Security
- No authentication/authorization layer — any client can hit any session's
  endpoints. Fine for a local hackathon demo, not for multi-tenant use.
- CORS is open to a single configured origin (`FRONTEND_ORIGIN`), not
  hardened further.
