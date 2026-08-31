from __future__ import annotations

from pydantic import BaseModel

from .incident import Severity


class GroundTruth(BaseModel):
    incident_id: str
    root_cause: str
    severity: Severity
    expected_action: str
    unsafe_actions: list[str] = []  # actions that would be dangerous to recommend
