"""Pydantic v2 schemas for mutable task execution state and merged task views."""

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from backend.app.domain.models import TaskStatus

ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    TaskStatus.TODO.value: {TaskStatus.IN_PROGRESS.value, TaskStatus.BLOCKED.value},
    TaskStatus.IN_PROGRESS.value: {
        TaskStatus.COMPLETED.value,
        TaskStatus.BLOCKED.value,
        TaskStatus.TODO.value,
    },
    TaskStatus.BLOCKED.value: {TaskStatus.IN_PROGRESS.value, TaskStatus.TODO.value},
    TaskStatus.COMPLETED.value: {TaskStatus.IN_PROGRESS.value},  # Allow reopening if needed
}


class TaskStatusUpdateRequest(BaseModel):
    """Payload to update the runtime execution state of an existing task."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(..., description="Target status: TODO, IN_PROGRESS, BLOCKED, or COMPLETED.")
    actual_start: date | None = Field(default=None, description="Actual start date of execution.")
    actual_finish: date | None = Field(default=None, description="Actual completion date.")
    actual_hours: float | None = Field(
        default=None, ge=0, description="Logged actual execution hours."
    )
    percent_complete: Annotated[int | None, Field(ge=0, le=100)] = Field(
        default=None, description="Estimated completion percentage (0-100)."
    )
    blocked_reason: str | None = Field(default=None, description="Reason if task is BLOCKED.")
    evidence_notes: str = Field(
        default="", description="Audit evidence or commentary for progress history."
    )
    updated_by: str = Field(
        default="user", min_length=1, description="Operator or agent ID making this update."
    )


class TaskMergedResponse(BaseModel):
    """Merged representation combining planned truth with runtime execution state."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Task identifier, e.g., TASK-01.")
    project_id: str
    title: str
    description: str
    status: str
    estimated_hours: float
    assigned_to_id: str | None = None
    planned_start_date: date | None = None
    planned_due_date: date | None = None
    actual_start: date | None = None
    actual_finish: date | None = None
    actual_hours: float = 0.0
    percent_complete: int = 0
    blocked_reason: str | None = None
    is_overdue: bool = False
    dependencies: list[str] = Field(default_factory=list, description="Predecessor task IDs.")
    updated_by: str = "system"
    updated_at: datetime
