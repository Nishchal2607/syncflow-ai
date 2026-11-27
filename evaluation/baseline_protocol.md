# Baseline Test Protocol

## Purpose
Compare **System A** (conventional prompt-and-wait) against **System B**
(SyncFlow AI) on the same task family, using the same underlying model
(or the deterministic fallback agents, for repeatability without API cost).

## System A — Prompt-and-wait baseline
A single-turn interface: the participant submits the full goal, waits for one
LLM completion, and receives one final report. No visibility into
intermediate steps, no ability to pause, redirect, or gate approval.
Implemented as `evaluation/baseline_app.py` (a minimal CLI/HTTP stub) using
the same Reporter-style prompt as SyncFlow AI's Reporter agent, run as a
single shot with no task decomposition, so the two systems differ in
*interaction model*, not in underlying model capability.

## System B — SyncFlow AI
The full multi-agent, interruptible, inspectable workspace described in the
main README.

## Procedure
1. Each participant completes **two** comparable tasks (see
   `experiment_tasks.md`), one on System A and one on System B, with task
   order counterbalanced across participants to control for learning effects.
2. Every task includes at least one planted error or outdated/contestable
   claim in the underlying source material, to measure error recovery.
3. Immediately after each task, the participant completes the data
   collection template (`participant_data.csv` columns) including a NASA-TLX
   workload questionnaire.
4. The facilitator records: total completion time, whether each intervention
   attempt (on System B) succeeded, and whether the participant correctly
   flagged the planted error.

## Sample size and methodology (fill in per actual run)
- Number of participants: _________ (document actual N; do not fabricate)
- Within-subjects, counterbalanced design.
- Session environment: local deployment of both systems, same hardware,
  same network conditions.
- Facilitator: _________
- Date(s): _________

## Known threats to validity
- Small sample sizes typical of hackathon timeframes limit statistical power;
  report results as directional/descriptive, not as proof of a significant
  effect, unless a proper statistical test is run and reported.
- Novelty effects: participants' first exposure to an interruptible UI may
  inflate perceived workload independent of the interface's actual quality.
