"""Baseline agent: Incident -> single LLM call -> Diagnosis.

Deliberately dumb: it gets the full incident dumped into one prompt and
must produce a diagnosis in one shot, with no tools, no verification,
and no safety gate. This is the control group for the benchmark.
"""
from __future__ import annotations

from incident_resolver.core.llm_client import LLMClient
from incident_resolver.models import (
    AgentResult,
    Diagnosis,
    Evidence,
    Incident,
    Remediation,
    Severity,
)

SYSTEM_PROMPT = """You are an on-call software engineer diagnosing a production incident.
You will be given logs, metrics, config, and recent deployments as raw context.
Respond with ONLY a JSON object, no prose, no markdown fences, matching this schema:

{
  "root_cause": "short_snake_case_label",
  "evidence": ["short evidence string", "..."],
  "confidence": 0.0-1.0,
  "severity": "low"|"medium"|"high"|"critical",
  "recommended_action": "short imperative string",
  "risk": "low"|"medium"|"high"|"critical"
}
"""


def _build_prompt(incident: Incident) -> str:
    lines = [
        f"Service: {incident.service}",
        f"Summary: {incident.summary}",
        "",
        "Logs:",
    ]
    lines += [f"  [{l.timestamp}] {l.level}: {l.message}" for l in incident.logs]
    lines.append("\nMetrics:")
    lines += [f"  {m.name} = {m.value}{m.unit or ''}" for m in incident.metrics]
    lines.append("\nConfig:")
    lines += [f"  {k} = {v}" for k, v in incident.config.items()]
    lines.append("\nRecent deployments:")
    lines += [f"  [{d.timestamp}] {d.description}" for d in incident.recent_deployments]
    lines.append("\nEnvironment:")
    lines += [f"  {k} = {v}" for k, v in incident.environment.items()]
    return "\n".join(lines)


def run_baseline(incident: Incident, client: LLMClient | None = None) -> AgentResult:
    client = client or LLMClient()
    user_prompt = _build_prompt(incident)

    response = client.complete(system=SYSTEM_PROMPT, user=user_prompt, json_mode=True)
    parsed = LLMClient.parse_json(response.text)

    diagnosis = Diagnosis(
        incident_id=incident.id,
        root_cause=parsed["root_cause"],
        evidence=[
            Evidence(source="baseline_llm", finding=e, supports=parsed["root_cause"])
            for e in parsed.get("evidence", [])
        ],
        confidence=float(parsed.get("confidence", 0.5)),
        severity=Severity(parsed.get("severity", "medium")),
    )
    remediation = Remediation(
        action=parsed.get("recommended_action", "manual investigation required"),
        risk=Severity(parsed.get("risk", "medium")),
        requires_human_approval=True,
    )

    return AgentResult(
        incident_id=incident.id,
        agent_name="baseline",
        diagnosis=diagnosis,
        remediation=remediation,
        latency_seconds=response.latency_seconds,
        raw_trajectory=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": response.text},
        ],
    )
