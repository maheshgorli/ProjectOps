"""Pydantic v2 schemas for risk analysis and replan proposals."""

from datetime import date

from pydantic import BaseModel

from backend.app.domain.risk.models import RiskSeverity, RiskType
from backend.app.schemas.plan import PlanResponseSchema


class DetectedRiskSchema(BaseModel):
    """Schema representing an identified risk event."""

    risk_type: RiskType
    severity: RiskSeverity
    description: str
    affected_task_ids: list[str] = []
    metrics: dict[str, str | int | float] = {}


class RiskAnalysisResponse(BaseModel):
    """Complete risk evaluation output for a project plan snapshot."""

    project_id: str
    plan_version: int
    health_score: int
    is_at_risk: bool
    summary: str
    risks: list[DetectedRiskSchema] = []


class ReplanCandidateResponse(BaseModel):
    """Proposed candidate replan with deterministic impact evaluation."""

    proposal_id: str | None = None
    project_id: str
    baseline_version: int
    proposed_version: int
    baseline_finish_date: date
    proposed_finish_date: date
    finish_date_delta_days: int
    resolved_risks_count: int
    mitigation_notes: list[str]
    proposed_plan: PlanResponseSchema
