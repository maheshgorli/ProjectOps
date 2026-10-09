"""Pydantic v2 schemas for task and dependency structural editing (Core Principle 5)."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.plan import PlanResponseSchema


class TaskCreateRequest(BaseModel):
    """Payload to add a new task to the active plan snapshot."""

    model_config = ConfigDict(extra="forbid")

    id: str | None = Field(
        default=None,
        description="Optional custom task ID. If omitted, generated sequentially.",
    )
    title: str = Field(..., min_length=1, description="Task title.")
    description: str = Field(default="", description="Task description.")
    estimated_hours: float = Field(default=8.0, gt=0, description="Estimated work hours.")
    assigned_to_id: str | None = Field(
        default=None, description="Project member ID assigned to task."
    )
    due_date: date | None = Field(default=None, description="Planned due date.")
    start_date: date | None = Field(default=None, description="Planned start date.")
    dependencies: list[str] = Field(default_factory=list, description="Predecessor task IDs.")


class TaskEditRequest(BaseModel):
    """Payload to update an existing task's planned baseline attributes."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1)
    description: str | None = None
    estimated_hours: float | None = Field(default=None, gt=0)
    assigned_to_id: str | None = None
    due_date: date | None = None
    start_date: date | None = None
    dependencies: list[str] | None = Field(
        default=None, description="If provided, replaces all predecessor dependencies."
    )


class DependencyCreateRequest(BaseModel):
    """Payload to add a dependency edge between two existing tasks."""

    model_config = ConfigDict(extra="forbid")

    predecessor_id: str = Field(..., min_length=1)
    successor_id: str = Field(..., min_length=1)
    dep_type: str = Field(
        default="FINISH_TO_START",
        description="FINISH_TO_START, START_TO_START, FINISH_TO_FINISH, START_TO_FINISH",
    )
    lag_days: int = Field(default=0, ge=0)


class MemberUpdateRequest(BaseModel):
    """Payload to update an existing team member's details."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1)
    role: str | None = Field(default=None, min_length=1)
    daily_capacity_hours: float | None = Field(default=None, gt=0)


class PlanMutationResponse(BaseModel):
    """Response returned upon successful structural plan modification."""

    model_config = ConfigDict(frozen=True)

    project_id: str
    previous_version: int
    new_version: int
    action: str
    affected_id: str
    decision_id: str
    plan: PlanResponseSchema
