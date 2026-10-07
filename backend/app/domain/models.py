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
    """
    Valid task statuses.
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
    """Team member with daily working capacity in hours."""

    id: str
    name: str
    role: str = "engineer"
    daily_capacity_hours: float = DEFAULT_DAILY_CAPACITY_HOURS

    def __post_init__(self) -> None:
        if self.daily_capacity_hours <= 0:
            raise ValueError(
                f"Member daily capacity must be positive, got {self.daily_capacity_hours}"
            )


@dataclass
class Task:
    """Project task entity."""

    id: str
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.TODO
    estimated_hours: float = 8.0
    assigned_to_id: str | None = None
    due_date: date | None = None
    start_date: date | None = None
    completed_at: datetime | None = None

    def is_overdue(self, clock: Clock) -> bool:
        """
        Derived property: A task is overdue if it is not COMPLETED
        and the clock date is past the due_date.
        Never stored in the database.
        """
        if self.status == TaskStatus.COMPLETED or self.due_date is None:
            return False
        return clock.today() > self.due_date

    def duration_days(self, daily_capacity_hours: float = DEFAULT_DAILY_CAPACITY_HOURS) -> int:
        """Calculate duration in working days given estimated hours and member capacity."""
        return hours_to_working_days(self.estimated_hours, daily_capacity_hours)


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
