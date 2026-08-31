from __future__ import annotations

from incident_resolver.models import Evidence, Incident

# Config keys worth flagging when present at all — the LLM diagnostician
# decides whether they're *relevant*, this tool just surfaces them.
WATCHED_KEYS = {
    "max_connections",
    "pool_size",
    "timeout_ms",
    "retry_count",
    "circuit_breaker_enabled",
    "cache_ttl_seconds",
}


def check_config(incident: Incident) -> list[Evidence]:
    findings: list[Evidence] = []
    for key, value in incident.config.items():
        if key in WATCHED_KEYS:
            findings.append(
                Evidence(
                    source="config_check",
                    finding=f"config.{key} = {value}",
                    supports="",
                )
            )
    return findings
