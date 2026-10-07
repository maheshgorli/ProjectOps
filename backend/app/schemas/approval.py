"""Pydantic schemas for Human Approval Gateway."""

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.plan import PlanCreateRequest, PlanResponseSchema


class ReplanApprovalRequest(BaseModel):
    """Request payload to officially approve a candidate replan."""

    model_config = ConfigDict(frozen=True)

    candidate_plan: PlanCreateRequest = Field(
        ...,
        description="The candidate replan snapshot to activate.",
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
    previous_version: int
    new_version: int
    decision_id: str
    status: str = "APPROVED"
    summary: str
    plan: PlanResponseSchema


class ReplanRejectionRequest(BaseModel):
    """Request payload to reject a candidate replan proposition."""

    model_config = ConfigDict(frozen=True)

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
    current_version: int
    decision_id: str
    status: str = "REJECTED"
    rationale: str
