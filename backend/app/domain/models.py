"""Pure domain models for ProjectOps.

No I/O, no DB imports, no external network calls.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum

from backend.app.domain.calendar import (
    DEFAULT_DAILY_CAPACITY_HOURS,
    hours_to_working_days,
)
from backend.app.domain.clock import Clock


class TaskStatus(StrEnum):
    """Valid task statuses.

    Rule: OVERDUE is strictly a derived property, never a stored status.
    """

    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"


class DependencyType(StrEnum):
    """Dependency precedence types (standard project network types)."""

    FINISH_TO_START = "FINISH_TO_START"
    START_TO_START = "START_TO_START"
    FINISH_TO_FINISH = "FINISH_TO_FINISH"
    START_TO_FINISH = "START_TO_FINISH"


@dataclass(frozen=True)
class Dependency:
    """Precedence relationship between two tasks."""

    predecessor_id: str
    successor_id: str
    dep_type: DependencyType = DependencyType.FINISH_TO_START
    lag_days: int = 0


@dataclass(frozen=True)
class Member:
    """Team member with daily working capacity, skills, and availability."""

    id: str
    name: str
    role: str = "engineer"
    skills: list[str] = field(default_factory=list)
    daily_capacity_hours: float = DEFAULT_DAILY_CAPACITY_HOURS
    max_parallel_tasks: int = 1

    def __post_init__(self) -> None:
        if self.daily_capacity_hours <= 0:
            raise ValueError(
                f"Member daily capacity must be positive, got {self.daily_capacity_hours}"
            )
        if self.max_parallel_tasks <= 0:
            raise ValueError(
                f"Member max parallel tasks must be positive, got {self.max_parallel_tasks}"
            )


@dataclass
class Task:
    """Project task entity."""

    id: str
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.TODO
    estimated_hours: float = 8.0
    duration_working_days: int | None = None
    required_skills: list[str] = field(default_factory=list)
    assigned_to_id: str | None = None
    due_date: date | None = None
    start_date: date | None = None
    completed_at: datetime | None = None

    def is_overdue(self, clock: Clock) -> bool:
        """Derived property: A task is overdue if it is not COMPLETED

        and the clock date is past the due_date. Never stored in the database.
        """
        if self.status == TaskStatus.COMPLETED or self.due_date is None:
            return False
        return clock.today() > self.due_date

    def duration_days(self, daily_capacity_hours: float = DEFAULT_DAILY_CAPACITY_HOURS) -> int:
        """Calculate duration in working days given estimated hours or explicit duration."""
        if self.duration_working_days is not None and self.duration_working_days >= 0:
            return self.duration_working_days
        return hours_to_working_days(self.estimated_hours, daily_capacity_hours)


@dataclass(frozen=True)
class CriticalPathData:
    """CPM calculation result for a single task."""

    task_id: str
    early_start: date
    early_finish: date
    late_start: date
    late_finish: date
    total_slack: int
    is_critical: bool


@dataclass(frozen=True)
class ScheduleEntry:
    """Scheduled task time window."""

    task_id: str
    start_date: date
    end_date: date
    assignee_id: str | None = None
    is_critical: bool = False
    slack_days: int = 0


@dataclass(frozen=True)
class Schedule:
    """Result of deterministic schedule computation."""

    entries: dict[str, ScheduleEntry]
    project_start_date: date
    project_end_date: date
    meets_deadline: bool
    deadline: date | None = None
    critical_path: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MemberWorkload:
    """Resource utilization and overload metrics for a team member."""

    member_id: str
    period_start: date
    period_end: date
    assigned_hours: float
    available_hours: float
    utilization_rate: float
    is_overloaded: bool


@dataclass(frozen=True)
class AssignmentCandidate:
    """Scored assignment recommendation for a task."""

    member_id: str
    total_score: float
    breakdown: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ImpactReport:
    """Report detailing projected impact of delaying a task."""

    delayed_task_id: str
    delay_days: int
    directly_affected_task_ids: list[str]
    indirectly_affected_task_ids: list[str]
    affected_member_ids: list[str]
    original_project_end_date: date
    projected_project_end_date: date
    end_date_shift_working_days: int


@dataclass
class ProjectPlan:
    """Immutable versioned plan snapshot."""

    id: str
    project_id: str
    version: int
    name: str
    created_at: datetime
    tasks: dict[str, Task] = field(default_factory=dict)
    dependencies: list[Dependency] = field(default_factory=list)
    members: dict[str, Member] = field(default_factory=dict)
    target_completion_date: date | None = None
    created_by: str = "system"

    def get_member_capacity(self, member_id: str | None) -> float:
        """Return daily capacity for an assigned member, or default."""
        if member_id and member_id in self.members:
            return self.members[member_id].daily_capacity_hours
        return DEFAULT_DAILY_CAPACITY_HOURS
