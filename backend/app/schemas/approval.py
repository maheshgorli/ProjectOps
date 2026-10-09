"""Pydantic schemas for Human Approval Gateway (Core Principle 4 & P0-1 fix)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.plan import PlanResponseSchema


class ReplanApprovalRequest(BaseModel):
    """Request payload to officially approve a candidate replan."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    proposal_id: str = Field(
        ...,
        min_length=1,
        description="ID of server-stored replan proposal to approve.",
    )
    decision_rationale: str = Field(
        ...,
        min_length=3,
        description="Justification / context for approving this replan.",
    )
    decided_by: str = Field(
        ...,
        min_length=1,
        description="Name or identifier of the human operator granting approval.",
    )


class ReplanApprovalResponse(BaseModel):
    """Response returned upon successful approval and activation of a new plan version."""

    model_config = ConfigDict(frozen=True)

    project_id: str
    proposal_id: str
    previous_version: int
    new_version: int
    decision_id: str
    status: str = "APPROVED"
    summary: str
    plan: PlanResponseSchema


class ReplanRejectionRequest(BaseModel):
    """Request payload to reject a candidate replan proposition."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    proposal_id: str = Field(
        ...,
        min_length=1,
        description="ID of server-stored replan proposal to reject.",
    )
    rationale: str = Field(
        ...,
        min_length=3,
        description="Reason for rejecting the candidate replan.",
    )
    decided_by: str = Field(
        ...,
        min_length=1,
        description="Name or identifier of the human operator rejecting the plan.",
    )


class ReplanRejectionResponse(BaseModel):
    """Response returned upon formal rejection of a candidate replan proposition."""

    model_config = ConfigDict(frozen=True)

    project_id: str
    proposal_id: str
    current_version: int
    decision_id: str
    status: str = "REJECTED"
    rationale: str


class ReplanProposalResponse(BaseModel):
    """Detailed view of a server-stored replan proposal snapshot."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    baseline_version: int
    candidate_plan: PlanResponseSchema
    risks_addressed: list[str] = Field(default_factory=list)
    explanation: str = ""
    status: str  # PENDING, APPROVED, REJECTED, SUPERSEDED
    created_by: str
    created_at: datetime
    decided_by: str | None = None
    decided_at: datetime | None = None
    rationale: str | None = None
