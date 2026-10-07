"""Pydantic schemas for the Autonomous Multi-Agent Execution Loop."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from backend.app.schemas.risk import ReplanCandidateResponse


class AgentRunSchema(BaseModel):
    """Schema representing an execution record in the agent loop audit trail."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: str
    project_id: str
    loop_stage: str
    status: str
    summary: str
    details_json: str | None
    triggered_by: str
    recorded_at: datetime


class LoopStepResponse(BaseModel):
    """Response returned upon completing a step/cycle of the multi-agent loop."""

    model_config = ConfigDict(frozen=True)

    project_id: str
    current_stage: str
    status: str
    health_score: float
    is_at_risk: bool
    summary: str
    detected_risks_count: int
    actionable_tasks: list[str]
    replan_candidate: ReplanCandidateResponse | None = None
    requires_human_approval: bool = False


class AgentLoopStatusResponse(BaseModel):
    """Overall status and execution history of the multi-agent loop."""

    model_config = ConfigDict(frozen=True)

    project_id: str
    active_plan_version: int | None
    current_status: str
    requires_human_approval: bool
    recent_runs: list[AgentRunSchema]
