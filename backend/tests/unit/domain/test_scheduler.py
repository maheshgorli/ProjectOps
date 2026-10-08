"""Unit tests for the deterministic resource-constrained scheduler."""

from datetime import date

import pytest
from backend.app.domain.models import Member, Task
from backend.app.domain.scheduler import SchedulingError, schedule_project


def test_scheduler_empty_tasks():
    sched = schedule_project(
        tasks={},
        dependencies=[],
        members={},
        project_start_date=date(2026, 11, 2),
    )
    assert len(sched.entries) == 0
    assert sched.project_start_date == date(2026, 11, 2)
    assert sched.meets_deadline is True


def test_scheduler_serializes_tasks_for_same_member():
    """Member Bob assigned two independent tasks T1 (2d) and T2 (2d).

    Because Bob can only work on 1 task at a time (max_parallel_tasks=1),
    they must be serialized in time rather than run in parallel!
    """
    members = {
        "m-bob": Member(id="m-bob", name="Bob", max_parallel_tasks=1),
    }
    tasks = {
        "T1": Task(id="T1", title="Task 1", duration_working_days=2, assigned_to_id="m-bob"),
        "T2": Task(id="T2", title="Task 2", duration_working_days=2, assigned_to_id="m-bob"),
    }
    # No dependency between T1 and T2
    sched = schedule_project(
        tasks=tasks,
        dependencies=[],
        members=members,
        project_start_date=date(2026, 11, 2),  # Monday
    )
    assert len(sched.entries) == 2
    e1 = sched.entries["T1"]
    e2 = sched.entries["T2"]

    # Verify no time overlap
    assert (e1.end_date < e2.start_date) or (e2.end_date < e1.start_date)


def test_scheduler_deadline_breach():
    members = {"m-1": Member(id="m-1", name="Dev")}
    tasks = {
        "T1": Task(id="T1", title="T1", duration_working_days=10, assigned_to_id="m-1"),
    }
    start_date = date(2026, 11, 2)
    tight_deadline = date(2026, 11, 6)  # 5 days (impossible for 10-day task)

    sched = schedule_project(tasks, [], members, start_date, deadline=tight_deadline)
    assert sched.meets_deadline is False


def test_scheduler_unknown_member_raises_error():
    tasks = {
        "T1": Task(id="T1", title="T1", duration_working_days=1, assigned_to_id="unknown_member"),
    }
    with pytest.raises(SchedulingError):
        schedule_project(tasks, [], {}, date(2026, 11, 2))
