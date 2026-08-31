from __future__ import annotations

from incident_resolver.models import Evidence, Incident

# Simple heuristic thresholds. In a real system these would be baselined
# per-service; here they're deliberately simple so the behavior is
# reproducible and easy to explain in the README.
THRESHOLDS = {
    "error_rate": 0.05,
    "latency_ms": 500,
    "connection_pool_utilization": 0.85,
    "cpu_percent": 85,
    "memory_percent": 85,
}


def analyze_metrics(incident: Incident) -> list[Evidence]:
    findings: list[Evidence] = []
    for m in incident.metrics:
        threshold = THRESHOLDS.get(m.name)
        if threshold is not None and m.value >= threshold:
            findings.append(
                Evidence(
                    source="metrics_analyzer",
                    finding=f"{m.name} = {m.value}{m.unit or ''} (>= threshold {threshold})",
                    supports="",
                )
            )
    return findings
