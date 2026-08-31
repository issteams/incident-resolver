"""Deterministic tools are kept LLM-free on purpose: they're cheap, fast,
and 100% reproducible, so the advanced agent's edge over baseline comes
from *structured evidence gathering*, not from asking the LLM twice."""
from __future__ import annotations

from incident_resolver.models import Evidence, Incident

ERROR_LEVELS = {"ERROR", "CRITICAL", "FATAL"}


def analyze_logs(incident: Incident) -> list[Evidence]:
    findings: list[Evidence] = []
    error_lines = [l for l in incident.logs if l.level.upper() in ERROR_LEVELS]

    if not error_lines:
        return findings

    # group by rough signature (first 4 words) to avoid duplicate noise
    seen: set[str] = set()
    for line in error_lines:
        sig = " ".join(line.message.split()[:4])
        if sig in seen:
            continue
        seen.add(sig)
        findings.append(
            Evidence(
                source="log_analyzer",
                finding=f"[{line.timestamp}] {line.level}: {line.message}",
                supports="",  # filled in later once a root-cause hypothesis exists
            )
        )
    return findings
