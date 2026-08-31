#!/usr/bin/env python
"""CLI: python baseline.py dataset/incidents/incident_001.json"""
import json
import sys

from incident_resolver.agents.baseline import run_baseline
from incident_resolver.models import Incident


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python baseline.py <incident.json>")
        sys.exit(1)

    incident = Incident.model_validate_json(open(sys.argv[1]).read())
    result = run_baseline(incident)
    print(json.dumps(result.model_dump(exclude={"raw_trajectory"}), indent=2))


if __name__ == "__main__":
    main()
