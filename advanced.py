#!/usr/bin/env python
"""CLI: python advanced.py dataset/incidents/incident_001.json"""
import json
import sys

from incident_resolver.agents.advanced import run_advanced
from incident_resolver.models import Incident


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python advanced.py <incident.json>")
        sys.exit(1)

    incident = Incident.model_validate_json(open(sys.argv[1]).read())
    result = run_advanced(incident)
    print(json.dumps(result.model_dump(exclude={"raw_trajectory"}), indent=2))

    if result.remediation.requires_human_approval:
        print("\n[HUMAN APPROVAL REQUIRED]")
        print(f"  Proposed action: {result.remediation.action}")
        print(f"  Risk: {result.remediation.risk.value}")
        print("  (simulated — no real action taken)")


if __name__ == "__main__":
    main()
