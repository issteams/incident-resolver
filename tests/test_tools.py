import json
from pathlib import Path

from incident_resolver.models import Incident
from incident_resolver.tools import (
    analyze_logs,
    analyze_metrics,
    check_config,
    check_deployment_history,
    is_destructive,
    escalate_risk_if_destructive,
)

DATASET = Path(__file__).resolve().parents[1] / "dataset" / "incidents"


def _load(name: str) -> Incident:
    return Incident.model_validate_json((DATASET / name).read_text())


def test_analyze_logs_finds_pool_exhaustion_errors():
    incident = _load("incident_001.json")
    findings = analyze_logs(incident)
    assert any("connection pool exhausted" in f.finding for f in findings)


def test_analyze_metrics_flags_pool_utilization():
    incident = _load("incident_001.json")
    findings = analyze_metrics(incident)
    assert any("connection_pool_utilization" in f.finding for f in findings)


def test_check_config_flags_watched_keys():
    incident = _load("incident_001.json")
    findings = check_config(incident)
    keys_found = {f.finding.split(" = ")[0] for f in findings}
    assert "config.max_connections" in keys_found
    assert "config.pool_size" in keys_found


def test_check_deployment_history_correlates_recent_deploy():
    incident = _load("incident_001.json")
    findings = check_deployment_history(incident)
    assert len(findings) == 1
    assert "pool_size" in findings[0].finding


def test_no_evidence_for_clean_incident():
    incident = Incident(id="clean", service="x", summary="nothing wrong")
    assert analyze_logs(incident) == []
    assert analyze_metrics(incident) == []
    assert check_config(incident) == []
    assert check_deployment_history(incident) == []


def test_safety_gate_flags_destructive_actions():
    assert is_destructive("DROP TABLE users;")
    assert is_destructive("rm -rf /data")
    assert not is_destructive("increase connection pool size")


def test_safety_gate_escalates_risk_and_never_downgrades():
    assert escalate_risk_if_destructive("drop database", "low") == "critical"
    assert escalate_risk_if_destructive("restart service", "high") == "high"
    assert escalate_risk_if_destructive("restart service", "medium") == "medium"
