"""Tests for pure domain models and derived overdue status."""

from datetime import UTC, date, datetime

import pytest

from backend.app.domain.clock import FrozenClock
from backend.app.domain.models import (
    Member,
    ProjectPlan,
    Task,
    TaskStatus,
)


def test_task_status_enum_values():
    assert TaskStatus.TODO == "TODO"
    assert TaskStatus.IN_PROGRESS == "IN_PROGRESS"
    assert TaskStatus.BLOCKED == "BLOCKED"
    assert TaskStatus.COMPLETED == "COMPLETED"
    # Verify OVERDUE is NOT in enum (Rule: OVERDUE is derived, never stored)
    with pytest.raises(ValueError):
        TaskStatus("OVERDUE")


def test_task_derived_is_overdue():
    clock = FrozenClock(date(2026, 10, 7))

    # Task without due date is never overdue
    task_no_due = Task(id="T1", title="No due date", status=TaskStatus.TODO, due_date=None)
    assert task_no_due.is_overdue(clock) is False

    # Task due today is not overdue
    task_due_today = Task(
        id="T2", title="Due today", status=TaskStatus.TODO, due_date=date(2026, 10, 7)
    )
    assert task_due_today.is_overdue(clock) is False

    # Task due tomorrow is not overdue
    task_due_tomorrow = Task(
        id="T3", title="Due tomorrow", status=TaskStatus.TODO, due_date=date(2026, 10, 8)
    )
    assert task_due_tomorrow.is_overdue(clock) is False

    # Task due yesterday (2026-10-06) is overdue when status is TODO
    task_due_yesterday = Task(
        id="T4", title="Due yesterday", status=TaskStatus.TODO, due_date=date(2026, 10, 6)
    )
    assert task_due_yesterday.is_overdue(clock) is True

    # Same task in progress is overdue
    task_in_progress = Task(
        id="T5",
        title="In progress overdue",
        status=TaskStatus.IN_PROGRESS,
        due_date=date(2026, 10, 6),
    )
    assert task_in_progress.is_overdue(clock) is True

    # Same task blocked is overdue
    task_blocked = Task(
        id="T6", title="Blocked overdue", status=TaskStatus.BLOCKED, due_date=date(2026, 10, 6)
    )
    assert task_blocked.is_overdue(clock) is True

    # Task due yesterday but COMPLETED is NOT overdue
    task_completed = Task(
        id="T7", title="Completed", status=TaskStatus.COMPLETED, due_date=date(2026, 10, 6)
    )
    assert task_completed.is_overdue(clock) is False


def test_member_validation():
    valid_member = Member(id="M1", name="Alice", daily_capacity_hours=7.5)
    assert valid_member.daily_capacity_hours == 7.5

    with pytest.raises(ValueError, match="positive"):
        Member(id="M2", name="Bob", daily_capacity_hours=0)

    with pytest.raises(ValueError, match="positive"):
        Member(id="M3", name="Charlie", daily_capacity_hours=-4.0)


def test_project_plan_member_capacity():
    plan = ProjectPlan(
        id="P1",
        project_id="PROJ-1",
        version=1,
        name="Test Plan",
        created_at=datetime.now(UTC),
        members={"M1": Member(id="M1", name="Alice", daily_capacity_hours=6.0)},
    )
    assert plan.get_member_capacity("M1") == 6.0
    assert plan.get_member_capacity("UNKNOWN") == 8.0
    assert plan.get_member_capacity(None) == 8.0
