"""Pydantic v2 schemas for Plans, Tasks, and Dependencies."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.domain.models import DependencyType, TaskStatus


class TaskCreateSchema(BaseModel):
    """Schema for defining a task when creating or updating a plan snapshot."""

    id: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    status: TaskStatus = Field(default=TaskStatus.TODO)
    estimated_hours: float = Field(default=8.0, ge=0)
    assigned_to_id: str | None = None
    due_date: date | None = None
    start_date: date | None = None


class TaskResponseSchema(BaseModel):
    """Schema for task representation in a plan snapshot response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str
    status: TaskStatus
    estimated_hours: float
    assigned_to_id: str | None
    due_date: date | None
    start_date: date | None
    completed_at: datetime | None
    is_overdue: bool = False


class DependencySchema(BaseModel):
    """Precedence dependency relationship between tasks."""

    model_config = ConfigDict(from_attributes=True)

    predecessor_id: str
    successor_id: str
    dep_type: DependencyType = DependencyType.FINISH_TO_START
    lag_days: int = 0


class PlanCreateRequest(BaseModel):
    """Payload to create an immutable plan snapshot."""

    version: int = Field(..., ge=1, description="Monotonically increasing version number")
    name: str = Field(..., min_length=1, max_length=255)
    target_completion_date: date | None = None
    created_by: str = Field(default="system", max_length=255)
    tasks: list[TaskCreateSchema] = Field(default_factory=list)
    dependencies: list[DependencySchema] = Field(default_factory=list)


class PlanResponseSchema(BaseModel):
    """Response schema for a complete versioned plan snapshot."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    version: int
    name: str
    target_completion_date: date | None
    created_at: datetime
    created_by: str
    tasks: list[TaskResponseSchema] = []
    dependencies: list[DependencySchema] = []


class PlanVersionListResponse(BaseModel):
    """Response schema listing available plan versions for a project."""

    project_id: str
    versions: list[int]
    active_version: int | None
