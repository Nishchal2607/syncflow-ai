# Evaluation Results

**Status: no human-subject trials have been run yet.** The tables below are
templates with the exact columns `analysis.py` will populate once
`participant_data.csv` contains real rows. Per the project rules, no
fabricated numbers are included here.

## Template — Task Effectiveness & Completion Time

| System | N | Task effectiveness (mean) | Completion time, s (mean) |
|---|---|---|---|
| System A (prompt-and-wait) | — | — | — |
| System B (SyncFlow AI) | — | — | — |

## Template — Intervention Success & Error Recovery

| System | N | Intervention success rate | Error recovery rate |
|---|---|---|---|
| System A | — | n/a (no in-flight intervention mechanism) | — |
| System B | — | — | — |

## Template — NASA-TLX (0–100 per subscale)

| System | Mental | Physical | Temporal | Performance | Effort | Frustration |
|---|---|---|---|---|---|---|
| System A | — | — | — | — | — | — |
| System B | — | — | — | — | — | — |

## How to regenerate this once data exists
```
cd evaluation
python analysis.py participant_data.csv
```
Paste the script's output into the tables above, and report the real N next
to each row. Do not report a number here that the script did not produce
from `participant_data.csv`.
