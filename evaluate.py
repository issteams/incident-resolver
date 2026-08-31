#!/usr/bin/env python
"""CLI: python evaluate.py — runs baseline+advanced over the full dataset."""
from incident_resolver.evaluation.runner import run_evaluation, print_report

if __name__ == "__main__":
    results = run_evaluation()
    print_report(results)
