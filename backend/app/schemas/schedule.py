"""Pydantic v2 schemas for deterministic scheduling and what-if simulation."""

from datetime import date

from pydantic import BaseModel, Field

from backend.app.schemas.plan import DependencySchema, TaskCreateSchema


class ScheduledTaskResponse(BaseModel):
    """Timing and float metrics for a scheduled task."""

    task_id: str
    early_start: date
    early_finish: date
    late_start: date
    late_finish: date
    duration_days: int
    total_float: int
    is_critical: bool
    is_overdue: bool


class MemberWorkloadResponse(BaseModel):
    """Workload utilization and capacity analysis for a member."""

    member_id: str
    capacity_hours_per_day: float
    total_assigned_hours: float
    daily_allocated_hours: dict[str, float]
    peak_daily_hours: float
    is_overallocated: bool
    overallocated_dates: list[date]


class ScheduleResponse(BaseModel):
    """Complete computed project schedule output."""

    project_start_date: date
    project_finish_date: date
    target_completion_date: date | None
    scheduled_tasks: list[ScheduledTaskResponse]
    critical_path: list[str]
    member_workloads: list[MemberWorkloadResponse]
    is_feasible: bool


class ScheduleSimulationRequest(BaseModel):
    """What-if simulation payload (computes impact without writing to DB)."""

    candidate_tasks: list[TaskCreateSchema] = Field(default_factory=list)
    candidate_dependencies: list[DependencySchema] = Field(default_factory=list)
    start_date: date | None = None
    target_completion_date: date | None = None


class ScheduleSimulationResponse(BaseModel):
    """Comparison diff between active baseline and simulated scenario."""

    baseline_finish_date: date
    simulated_finish_date: date
    finish_date_delta_working_days: int
    critical_path_changed: bool
    simulation: ScheduleResponse
