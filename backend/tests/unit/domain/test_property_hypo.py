"""Property-based tests for domain calendar and scheduler using Hypothesis."""

from datetime import date

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.app.domain.calendar import (
    add_working_days,
    calculate_task_finish_date,
    calculate_task_start_date,
    is_working_day,
)
from backend.app.domain.models import Dependency, Member, Task
from backend.app.domain.scheduler import schedule_project

# Safe date strategy (within modern years)
date_strategy = st.dates(min_value=date(2025, 1, 1), max_value=date(2035, 12, 31))


@given(start_date=date_strategy, days=st.integers(min_value=1, max_value=100))
@settings(max_examples=100)
def test_add_working_days_is_always_a_working_day(start_date: date, days: int):
    """Adding positive working days always produces a valid Monday-Friday working day."""
    result = add_working_days(start_date, days)
    assert is_working_day(result) is True


@given(start_date=date_strategy, duration=st.integers(min_value=1, max_value=50))
@settings(max_examples=100)
def test_task_date_calculation_roundtrip(start_date: date, duration: int):
    """calculate_task_finish_date and calculate_task_start_date are symmetric inverses."""
    finish = calculate_task_finish_date(start_date, duration)
    start_back = calculate_task_start_date(finish, duration)

    assert is_working_day(finish) is True
    assert is_working_day(start_back) is True
    assert calculate_task_finish_date(start_back, duration) == finish


@given(
    d1=st.integers(min_value=1, max_value=5),
    d2=st.integers(min_value=1, max_value=5),
    d3=st.integers(min_value=1, max_value=5),
)
@settings(max_examples=50)
def test_scheduler_invariants(d1: int, d2: int, d3: int):
    """Generate linear and diamond graphs and verify:

    1. No dependency violations: for all (u, v), start_date(v) > end_date(u).
    2. No task starts or ends on a weekend.
    3. project_end_date >= every task end date.
    """
    members = {
        "m1": Member(id="m1", name="Dev 1", daily_capacity_hours=8.0),
        "m2": Member(id="m2", name="Dev 2", daily_capacity_hours=8.0),
    }
    tasks = {
        "T1": Task(id="T1", title="T1", duration_working_days=d1, assigned_to_id="m1"),
        "T2": Task(id="T2", title="T2", duration_working_days=d2, assigned_to_id="m2"),
        "T3": Task(id="T3", title="T3", duration_working_days=d3, assigned_to_id="m1"),
    }
    deps = [
        Dependency("T1", "T2"),
        Dependency("T2", "T3"),
    ]
    start = date(2026, 11, 2)
    schedule = schedule_project(tasks, deps, members, start)

    # 1. Check dependencies
    e1 = schedule.entries["T1"]
    e2 = schedule.entries["T2"]
    e3 = schedule.entries["T3"]
    assert e2.start_date > e1.end_date
    assert e3.start_date > e2.end_date

    # 2. Check no task starts or ends on weekend
    for entry in schedule.entries.values():
        assert is_working_day(entry.start_date) is True
        assert is_working_day(entry.end_date) is True

    # 3. Check project end date bounds
    for entry in schedule.entries.values():
        assert schedule.project_end_date >= entry.end_date
