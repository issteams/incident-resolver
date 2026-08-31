"""Advanced agent.

Incident
   -> run deterministic tools (log/metrics/config/history) in parallel-ish
   -> evidence collector merges findings
   -> LLM diagnostician proposes root_cause + action, grounded in evidence
      (not raw log dump — this is the key difference from baseline)
   -> verifier: LLM is asked to check its own diagnosis against the
      *actual* evidence list and either confirm or revise (catches the
      "trusts first plausible explanation" failure mode)
   -> safety gate: deterministic veto/escalation for destructive actions
   -> human_approval_required is always True for medium+ risk

Every stage is recorded into raw_trajectory so trajectories/ has a real
tool-use + retry + checkpoint story, not just one LLM call.
"""
from __future__ import annotations

import json

from incident_resolver.core.llm_client import LLMClient
from incident_resolver.models import (
    AgentResult,
    Diagnosis,
    Evidence,
    Incident,
    Remediation,
    Severity,
)
from incident_resolver.tools import (
    analyze_logs,
    analyze_metrics,
    check_config,
    check_deployment_history,
    escalate_risk_if_destructive,
)

DIAGNOSIS_SYSTEM_PROMPT = """You are an on-call software engineer diagnosing a production incident.
You are given a list of EVIDENCE items already gathered by deterministic tools
(log analyzer, metrics analyzer, config checker, deployment-history checker).
Do not invent evidence beyond what is listed. Base your diagnosis only on it.

Respond with ONLY a JSON object, no prose, no markdown fences:
{
  "root_cause": "short_snake_case_label",
  "supporting_evidence_indices": [0, 2, 3],
  "confidence": 0.0-1.0,
  "severity": "low"|"medium"|"high"|"critical",
  "recommended_action": "short imperative string",
  "risk": "low"|"medium"|"high"|"critical"
}
"""

VERIFY_SYSTEM_PROMPT = """You are a skeptical senior engineer reviewing a junior engineer's incident diagnosis.
You will get the evidence list and the proposed diagnosis JSON.
Check: does every cited evidence index actually exist and plausibly support the claimed root cause?
Is the confidence justified given how many evidence items support it (more corroborating,
independent evidence sources = higher justified confidence; a single log line is weak)?

Respond with ONLY JSON:
{
  "verdict": "confirm" | "revise",
  "revised_confidence": 0.0-1.0,
  "reason": "short string"
}
"""


def _format_evidence(evidence: list[Evidence]) -> str:
    return "\n".join(f"[{i}] ({e.source}) {e.finding}" for i, e in enumerate(evidence))

def _complete_json(
    client: LLMClient,
    system: str,
    user: str,
    trajectory: list[dict],
    step: str,
) -> tuple[dict, float]:
    total_latency = 0.0

    for attempt in range(2):
        response = client.complete(
            system=system,
            user=user,
            json_mode=True,
            max_tokens=1500,
        )
        total_latency += response.latency_seconds

        trajectory.append(
            {
                "role": "assistant",
                "step": f"{step}_raw",
                "content": response.text,
                "attempt": attempt + 1,
            }
        )

        try:
            return LLMClient.parse_json(response.text), total_latency
        except (json.JSONDecodeError, ValueError) as exc:
            if attempt == 0:
                trajectory.append(
                    {
                        "role": "retry",
                        "step": f"{step}_json_parse_retry",
                        "content": str(exc),
                    }
                )
                continue
            raise

    raise RuntimeError(f"Failed to obtain valid JSON for {step}")


def run_advanced(incident: Incident, client: LLMClient | None = None) -> AgentResult:
    client = client or LLMClient()
    trajectory: list[dict] = []
    total_latency = 0.0

    # --- Step 1: deterministic tool sweep (the "planner" here is just a
    # fixed pipeline; a fancier planner could choose tools dynamically, but
    # for this incident domain running all four is cheap and complete) ---
    evidence: list[Evidence] = []
    evidence += analyze_logs(incident)
    evidence += analyze_metrics(incident)
    evidence += check_config(incident)
    evidence += check_deployment_history(incident)

    trajectory.append(
        {
            "role": "tool",
            "step": "evidence_collection",
            "content": [e.model_dump() for e in evidence],
        }
    )

    if not evidence:
        # No signal at all — advanced agent should say so, not guess.
        diagnosis = Diagnosis(
            incident_id=incident.id,
            root_cause="insufficient_evidence",
            evidence=[],
            confidence=0.0,
            severity=Severity.LOW,
        )
        remediation = Remediation(
            action="escalate to human for manual investigation",
            risk=Severity.LOW,
            requires_human_approval=True,
        )
        return AgentResult(
            incident_id=incident.id,
            agent_name="advanced",
            diagnosis=diagnosis,
            remediation=remediation,
            latency_seconds=0.0,
            raw_trajectory=trajectory,
        )

    # --- Step 2: LLM diagnosis grounded in evidence ---
    evidence_block = _format_evidence(evidence)
    diag_user_prompt = (
        f"Service: {incident.service}\nSummary: {incident.summary}\n\n"
        f"Evidence:\n{evidence_block}"
    )
    trajectory.append(
        {
            "role": "user",
            "step": "diagnosis_prompt",
            "content": diag_user_prompt,
        }
    )

    diag_parsed, diag_latency = _complete_json(
        client,
        DIAGNOSIS_SYSTEM_PROMPT,
        diag_user_prompt,
        trajectory,
        "diagnosis",
    )
    total_latency += diag_latency
    # attach evidence to the diagnosis based on cited indices
    cited_indices = diag_parsed.get("supporting_evidence_indices", [])
    for idx in cited_indices:
        if isinstance(idx, int) and 0 <= idx < len(evidence):
            evidence[idx].supports = diag_parsed["root_cause"]

    # --- Step 3: verification pass (catches over-confident first guesses) ---
    verify_user_prompt = (
        f"Evidence:\n{evidence_block}\n\nProposed diagnosis:\n{json.dumps(diag_parsed, indent=2)}"
    )
    trajectory.append(
        {
            "role": "user",
            "step": "verify_prompt",
            "content": verify_user_prompt,
        }
    )

    verify_parsed, verify_latency = _complete_json(
        client,
        VERIFY_SYSTEM_PROMPT,
        verify_user_prompt,
        trajectory,
        "verification",
    )
    total_latency += verify_latency

    final_confidence = float(
        verify_parsed.get("revised_confidence", diag_parsed.get("confidence", 0.5))
    )
    trajectory.append(
        {
            "role": "checkpoint",
            "step": "verification_verdict",
            "content": verify_parsed,
        }
    )

    # --- Step 4: safety gate (deterministic, cannot be overridden by the LLM) ---
    action = diag_parsed.get("recommended_action", "manual investigation required")
    escalated_risk = escalate_risk_if_destructive(action, diag_parsed.get("risk", "medium"))
    if escalated_risk != diag_parsed.get("risk", "medium"):
        trajectory.append(
            {
                "role": "safety_gate",
                "step": "risk_escalated",
                "content": f"action '{action}' flagged destructive; risk escalated to {escalated_risk}",
            }
        )

    diagnosis = Diagnosis(
        incident_id=incident.id,
        root_cause=diag_parsed["root_cause"],
        evidence=evidence,
        confidence=final_confidence,
        severity=Severity(diag_parsed.get("severity", "medium")),
    )
    remediation = Remediation(
        action=action,
        risk=Severity(escalated_risk),
        requires_human_approval=True,
    )

    return AgentResult(
        incident_id=incident.id,
        agent_name="advanced",
        diagnosis=diagnosis,
        remediation=remediation,
        latency_seconds=total_latency,
        raw_trajectory=trajectory,
    )
