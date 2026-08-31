"""Safety/risk gate. This is the piece the README/video should highlight:
baseline can happily recommend "drop and recreate the table" with high
confidence; the advanced agent vetoes destructive actions and forces
human approval + a HIGH risk label instead of silently executing them.
"""
from __future__ import annotations

DESTRUCTIVE_PATTERNS = [
    "drop table",
    "drop database",
    "delete from",
    "rm -rf",
    "truncate",
    "force push",
    "delete all",
    "reset --hard",
    "terminate instance",
    "revoke all",
]


def is_destructive(action: str) -> bool:
    lowered = action.lower()
    return any(p in lowered for p in DESTRUCTIVE_PATTERNS)


def escalate_risk_if_destructive(action: str, current_risk: str) -> str:
    """Returns the (possibly escalated) risk level. Never downgrades."""
    order = ["low", "medium", "high", "critical"]
    if is_destructive(action):
        return "critical"
    return current_risk if current_risk in order else "medium"
