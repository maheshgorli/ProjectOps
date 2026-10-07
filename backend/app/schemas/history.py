"""Pydantic v2 schemas for append-only audit trail: progress, decisions, and risks."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProgressEventCreateRequest(BaseModel):
    """Payload to record a task progress event."""

    task_id: str = Field(..., min_length=1, max_length=100)
    new_status: str = Field(..., min_length=1, max_length=50)
    previous_status: str | None = None
    evidence_notes: str = Field(default="", max_length=2000)
    recorded_by: str = Field(default="system", max_length=255)


class ProgressEventResponse(BaseModel):
    """Response schema for a progress event record."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    task_id: str
    previous_status: str | None
    new_status: str
    evidence_notes: str
    recorded_by: str
    recorded_at: datetime


class DecisionCreateRequest(BaseModel):
    """Payload to record a governance or replan decision."""

    decision_type: str = Field(..., min_length=1, max_length=100)
    summary: str = Field(..., min_length=1, max_length=255)
    rationale: str = Field(default="", max_length=4000)
    decided_by: str = Field(..., min_length=1, max_length=255)
    plan_id: str | None = None


class DecisionResponse(BaseModel):
    """Response schema for a decision record."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    plan_id: str | None
    decision_type: str
    summary: str
    rationale: str
    decided_by: str
    recorded_at: datetime


class RiskEventCreateRequest(BaseModel):
    """Payload to record a detected risk anomaly."""

    risk_type: str = Field(..., min_length=1, max_length=100)
    severity: str = Field(..., min_length=1, max_length=50)
    description: str = Field(..., min_length=1, max_length=2000)
    payload_json: str | None = None


class RiskEventResponse(BaseModel):
    """Response schema for a detected risk anomaly record."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    risk_type: str
    severity: str
    description: str
    payload_json: str | None
    detected_at: datetime
