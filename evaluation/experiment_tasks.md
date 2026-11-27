# Experiment Task Definitions

Two comparable task variants, matched for difficulty and structure, used
across System A and System B (counterbalanced per participant).

## Task 1 — EV companies
> "Research three electric vehicle companies, compare their products, verify
> important claims, and prepare a report."

**Planted intervention point:** after the plan is visible (System B) or after
the system begins (System A, invisible), the facilitator asks the
participant to redirect: "Exclude [Company C] and research [Company D]
instead."
- On System B: measured as a REDIRECT intervention attempt.
- On System A: the participant must stop the model, manually edit a new
  prompt, and resubmit from scratch — this is the "redirect" baseline
  participants are timed against.

**Planted error:** one of the three source summaries given to the research
step contains a subtly wrong figure (e.g. an incorrect range or price).
Success = participant/system flags it as uncertain or incorrect during
verification or review.

## Task 2 — Database providers
> "Research two cloud database providers, compare pricing and reliability,
> verify claims, and summarize."

Same structure as Task 1: one planted redirect instruction, one planted
factual error in the source material.

## Metrics captured per task (see `analysis.py` for calculations)
1. Task effectiveness (completed tasks / total tasks in the plan)
2. Task completion time (goal submission -> final report delivered/approved)
3. Human intervention success (successful redirects / attempted redirects)
4. Trust calibration (did the participant correctly flag the planted error?)
5. Cognitive workload (NASA-TLX, administered immediately after each task)
6. Error recovery (planted errors successfully caught / planted errors)
