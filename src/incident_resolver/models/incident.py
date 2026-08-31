"""Core domain models for the Incident Resolver system.

These are intentionally simple, serializable (Pydantic) models so that:
  - synthetic incidents can be authored as plain JSON
  - baseline and advanced agents consume/produce the exact same shapes
  - the evaluator can diff a Diagnosis against ground truth deterministically
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class LogEntry(BaseModel):
    timestamp: str
    level: str
    message: str


class MetricPoint(BaseModel):
    name: str
    value: float
    unit: Optional[str] = None


class DeploymentEvent(BaseModel):
    timestamp: str
    description: str


class Incident(BaseModel):
    """A single synthetic incident case. Mirrors dataset/incidents/*.json."""

    id: str
    service: str
    summary: str
    logs: list[LogEntry] = Field(default_factory=list)
    metrics: list[MetricPoint] = Field(default_factory=list)
    config: dict[str, str] = Field(default_factory=dict)
    recent_deployments: list[DeploymentEvent] = Field(default_factory=list)
    environment: dict[str, str] = Field(default_factory=dict)


class Evidence(BaseModel):
    source: str  # which tool produced this, e.g. "log_analyzer"
    finding: str
    supports: str  # short root-cause label this evidence supports


class Diagnosis(BaseModel):
    incident_id: str
    root_cause: str
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    severity: Severity


class Remediation(BaseModel):
    action: str
    risk: Severity
    requires_human_approval: bool = True


class AgentResult(BaseModel):
    """What baseline.py / advanced.py ultimately emit for one incident."""

    incident_id: str
    agent_name: str  # "baseline" | "advanced"
    diagnosis: Diagnosis
    remediation: Remediation
    latency_seconds: float
    raw_trajectory: list[dict] = Field(default_factory=list)  # for trajectories/
