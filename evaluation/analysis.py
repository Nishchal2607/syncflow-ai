"""
Metric calculation script for the SyncFlow AI vs. prompt-and-wait evaluation.

Usage:
    python analysis.py participant_data.csv

Reads the CSV defined by participant_data.csv's header and prints descriptive
statistics per system (System A / System B) for each of the six metrics
defined in the hackathon problem statement. This script performs NO
imputation and fabricates NOTHING: if a column is empty for a row, that row
is excluded from the relevant metric's average and the exclusion count is
reported.

This script is intentionally simple (no external stats dependency) so it can
run anywhere Python 3 runs. If scipy is available, a Mann-Whitney U or
Wilcoxon test can be layered on top for the within-subjects comparisons;
that is left as a documented extension rather than implemented here, since
fabricating a statistical test on a currently-empty/placeholder dataset would
misrepresent results.
"""
import csv
import sys
import statistics as st
from collections import defaultdict


NUMERIC_FIELDS = [
    "task_effectiveness", "completion_time_seconds",
    "intervention_attempts", "intervention_successes",
    "tlx_mental_demand", "tlx_physical_demand", "tlx_temporal_demand",
    "tlx_performance", "tlx_effort", "tlx_frustration",
]
BOOL_FIELDS = ["planted_error_caught"]


def load(path: str):
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def summarize(rows: list[dict]):
    by_system = defaultdict(list)
    for r in rows:
        by_system[r.get("system", "unknown")].append(r)

    if not rows:
        print("No participant data found yet. This is expected until real "
              "sessions are run — see baseline_protocol.md for the procedure.")
        return

    for system, system_rows in by_system.items():
        print(f"\n=== {system} (n={len(system_rows)}) ===")

        for field in NUMERIC_FIELDS:
            values = [to_float(r.get(field)) for r in system_rows]
            values = [v for v in values if v is not None]
            excluded = len(system_rows) - len(values)
            if values:
                print(f"{field:28s} mean={st.mean(values):.2f}  "
                      f"stdev={(st.stdev(values) if len(values) > 1 else 0):.2f}  "
                      f"n={len(values)}  excluded(missing)={excluded}")
            else:
                print(f"{field:28s} no data")

        # intervention success rate
        attempts = [to_float(r.get("intervention_attempts")) for r in system_rows]
        successes = [to_float(r.get("intervention_successes")) for r in system_rows]
        pairs = [(a, s) for a, s in zip(attempts, successes) if a is not None and s is not None and a > 0]
        if pairs:
            rate = sum(s for _, s in pairs) / sum(a for a, _ in pairs)
            print(f"{'intervention_success_rate':28s} {rate:.2%} (n={len(pairs)})")
        else:
            print(f"{'intervention_success_rate':28s} no data")

        # trust calibration / error recovery
        caught = [r.get("planted_error_caught") for r in system_rows]
        caught = [c.strip().lower() for c in caught if c and c.strip()]
        if caught:
            rate = sum(1 for c in caught if c in ("1", "true", "yes", "y")) / len(caught)
            print(f"{'error_recovery_rate':28s} {rate:.2%} (n={len(caught)})")
        else:
            print(f"{'error_recovery_rate':28s} no data")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "participant_data.csv"
    summarize(load(path))
