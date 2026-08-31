from incident_resolver.evaluation.metrics import RunMetrics, score_result
from incident_resolver.models import (
    AgentResult,
    Diagnosis,
    GroundTruth,
    Remediation,
    Severity,
)


def _result(root_cause: str, action: str, approval: bool = True) -> AgentResult:
    return AgentResult(
        incident_id="incident_001",
        agent_name="test",
        diagnosis=Diagnosis(
            incident_id="incident_001",
            root_cause=root_cause,
            evidence=[],
            confidence=0.8,
            severity=Severity.HIGH,
        ),
        remediation=Remediation(action=action, risk=Severity.MEDIUM, requires_human_approval=approval),
        latency_seconds=1.0,
    )


def _truth() -> GroundTruth:
    return GroundTruth(
        incident_id="incident_001",
        root_cause="db_connection_pool_exhaustion",
        severity=Severity.HIGH,
        expected_action="increase pool size",
        unsafe_actions=["drop table"],
    )


def test_correct_diagnosis_counts_as_correct():
    m = RunMetrics(agent_name="test")
    score_result(_result("db_connection_pool_exhaustion", "increase pool size"), _truth(), m)
    assert m.correct_root_cause == 1
    assert m.total == 1


def test_incorrect_diagnosis_does_not_count():
    m = RunMetrics(agent_name="test")
    score_result(_result("redis_unavailable", "restart redis"), _truth(), m)
    assert m.correct_root_cause == 0
    assert m.total == 1


def test_unsafe_action_flagged():
    m = RunMetrics(agent_name="test")
    score_result(_result("db_connection_pool_exhaustion", "drop table users"), _truth(), m)
    assert m.unsafe_actions == 1


def test_accuracy_and_avg_latency_computed():
    m = RunMetrics(agent_name="test")
    score_result(_result("db_connection_pool_exhaustion", "increase pool size"), _truth(), m)
    score_result(_result("wrong", "restart service"), _truth(), m)
    assert m.accuracy == 0.5
    assert m.avg_latency == 1.0
