from __future__ import annotations

from datetime import datetime, timedelta

from incident_resolver.models import Evidence, Incident

# Deployments within this window of the *last* log entry are treated as
# plausibly correlated with the incident.
CORRELATION_WINDOW = timedelta(minutes=30)


def _parse(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def check_deployment_history(incident: Incident) -> list[Evidence]:
    findings: list[Evidence] = []
    if not incident.logs or not incident.recent_deployments:
        return findings

    last_log_ts = max((_parse(l.timestamp) for l in incident.logs if _parse(l.timestamp)), default=None)
    if last_log_ts is None:
        return findings

    for dep in incident.recent_deployments:
        dep_ts = _parse(dep.timestamp)
        if dep_ts is None:
            continue
        if abs(last_log_ts - dep_ts) <= CORRELATION_WINDOW:
            findings.append(
                Evidence(
                    source="history_search",
                    finding=f"[{dep.timestamp}] {dep.description} (within {CORRELATION_WINDOW} of incident)",
                    supports="",
                )
            )
    return findings
