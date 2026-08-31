#!/usr/bin/env python
"""CLI: python evaluate.py — runs baseline+advanced over the full dataset."""
import json
from pathlib import Path

from incident_resolver.evaluation import run_evaluation, print_report


if __name__ == "__main__":
    results = run_evaluation()
    print_report(results)

    out_path = Path(__file__).resolve().parent / "evaluation_report.json"
    out_path.write_text(
        json.dumps(
            {
                "baseline": results["baseline"].as_dict(),
                "advanced": results["advanced"].as_dict(),
                "baseline_per_incident": results["baseline"].per_incident,
                "advanced_per_incident": results["advanced"].per_incident,
            },
            indent=2,
        )
    )

    print(f"\nDetailed report written to {out_path}")