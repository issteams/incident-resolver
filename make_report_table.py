#!/usr/bin/env python
"""python make_report_table.py  ->  prints a markdown table + per-incident
breakdown from evaluation_report.json, ready to paste into the README or
show on screen during the video's 'final comparison' segment.

Run this AFTER evaluate.py has produced evaluation_report.json.
"""
import json
import sys
from pathlib import Path

REPORT_PATH = Path(__file__).resolve().parent / "evaluation_report.json"


def main() -> None:
    if not REPORT_PATH.exists():
        print("evaluation_report.json not found — run `python evaluate.py` first.")
        sys.exit(1)

    data = json.loads(REPORT_PATH.read_text())
    b, a = data["baseline"], data["advanced"]

    print("## Evaluation results\n")
    print("| Metric | Baseline | Advanced | Delta |")
    print("|---|---|---|---|")
    print(f"| Accuracy | {b['accuracy_pct']}% ({b['correct_root_cause']}/{b['total']}) "
          f"| {a['accuracy_pct']}% ({a['correct_root_cause']}/{a['total']}) "
          f"| {a['accuracy_pct'] - b['accuracy_pct']:+.1f}pp |")
    print(f"| Unsafe actions | {b['unsafe_actions']} | {a['unsafe_actions']} "
          f"| {a['unsafe_actions'] - b['unsafe_actions']:+d} |")
    print(f"| Avg latency | {b['avg_latency_seconds']}s | {a['avg_latency_seconds']}s "
          f"| {a['avg_latency_seconds'] - b['avg_latency_seconds']:+.2f}s |")

    print("\n## Per-incident breakdown (where baseline and advanced disagreed)\n")
    print("| Incident | True root cause | Baseline | Advanced |")
    print("|---|---|---|---|")
    b_by_id = {r["incident_id"]: r for r in data["baseline_per_incident"]}
    a_by_id = {r["incident_id"]: r for r in data["advanced_per_incident"]}
    for iid in sorted(b_by_id):
        br, ar = b_by_id[iid], a_by_id[iid]
        if br["correct"] != ar["correct"]:
            b_mark = "correct" if br["correct"] else f"WRONG ({br['predicted_root_cause']})"
            a_mark = "correct" if ar["correct"] else f"WRONG ({ar['predicted_root_cause']})"
            print(f"| {iid} | {br['true_root_cause']} | {b_mark} | {a_mark} |")


if __name__ == "__main__":
    main()
