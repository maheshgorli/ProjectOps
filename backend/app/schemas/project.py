"""Pydantic v2 schemas for Projects and Members."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class MemberCreateRequest(BaseModel):
    """Payload to add a member to a project."""

    name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(default="engineer", max_length=100)
    daily_capacity_hours: float = Field(default=8.0, gt=0, le=24)


class MemberResponse(BaseModel):
    """Response schema for a project member."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    name: str
    role: str
    daily_capacity_hours: float
    created_at: datetime


class ProjectCreateRequest(BaseModel):
    """Payload to create a new project."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)


class ProjectResponse(BaseModel):
    """Response schema for a project."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    members: list[MemberResponse] = []
    task_count: int = 0
    active_plan_version: int | None = None
    target_completion_date: date | None = None
