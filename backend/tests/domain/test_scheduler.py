"""Tests for DeterministicScheduler and Critical Path Method (CPM)."""

from datetime import UTC, date, datetime

from backend.app.domain.clock import FrozenClock
from backend.app.domain.models import (
    Dependency,
    Member,
    ProjectPlan,
    Task,
    TaskStatus,
)
from backend.app.domain.scheduler import DeterministicScheduler


def test_empty_plan_scheduling():
    clock = FrozenClock(date(2026, 10, 5))  # Monday
    scheduler = DeterministicScheduler(clock)
    plan = ProjectPlan(
        id="P0",
        project_id="PROJ",
        version=1,
        name="Empty",
        created_at=datetime.now(UTC),
    )
    result = scheduler.schedule(plan)
    assert result.project_start_date == date(2026, 10, 5)
    assert result.project_finish_date == date(2026, 10, 5)
    assert result.critical_path == []
    assert result.is_feasible is True


def test_classic_cpm_critical_path():
    """
    Classic CPM Network (starting Monday 2026-10-05):
    - A: 3 days (estimated 24h / 8h cap)
    - B: 4 days (pred: A)
    - C: 2 days (pred: A)
    - D: 5 days (pred: B)
    - E: 1 day  (pred: C)
    - F: 2 days (pred: D, E)

    Path 1: A (3) -> B (4) -> D (5) -> F (2) = 14 working days (CRITICAL)
    Path 2: A (3) -> C (2) -> E (1) -> F (2) = 8 working days
    """
    clock = FrozenClock(date(2026, 10, 5))
    scheduler = DeterministicScheduler(clock)

    tasks = {
        "A": Task(id="A", title="Task A", estimated_hours=24.0),  # 3 days
        "B": Task(id="B", title="Task B", estimated_hours=32.0),  # 4 days
        "C": Task(id="C", title="Task C", estimated_hours=16.0),  # 2 days
        "D": Task(id="D", title="Task D", estimated_hours=40.0),  # 5 days
        "E": Task(id="E", title="Task E", estimated_hours=8.0),  # 1 day
        "F": Task(id="F", title="Task F", estimated_hours=16.0),  # 2 days
    }

    dependencies = [
        Dependency(predecessor_id="A", successor_id="B"),
        Dependency(predecessor_id="A", successor_id="C"),
        Dependency(predecessor_id="B", successor_id="D"),
        Dependency(predecessor_id="C", successor_id="E"),
        Dependency(predecessor_id="D", successor_id="F"),
        Dependency(predecessor_id="E", successor_id="F"),
    ]

    plan = ProjectPlan(
        id="P1",
        project_id="PROJ-CPM",
        version=1,
        name="CPM Benchmark Plan",
        created_at=datetime.now(UTC),
        tasks=tasks,
        dependencies=dependencies,
    )

    result = scheduler.schedule(plan, start_date=date(2026, 10, 5))

    # A: Mon 10-05 to Wed 10-07 (3 days)
    assert result.scheduled_tasks["A"].early_start == date(2026, 10, 5)
    assert result.scheduled_tasks["A"].early_finish == date(2026, 10, 7)
    assert result.scheduled_tasks["A"].duration_days == 3
    assert result.scheduled_tasks["A"].total_float == 0
    assert result.scheduled_tasks["A"].is_critical is True

    # B: Thu 10-08, Fri 10-09, Mon 10-12, Tue 10-13 (4 days)
    assert result.scheduled_tasks["B"].early_start == date(2026, 10, 8)
    assert result.scheduled_tasks["B"].early_finish == date(2026, 10, 13)
    assert result.scheduled_tasks["B"].total_float == 0
    assert result.scheduled_tasks["B"].is_critical is True

    # C: Thu 10-08, Fri 10-09 (2 days). Float should be 6 working days (14 - 8)
    assert result.scheduled_tasks["C"].early_start == date(2026, 10, 8)
    assert result.scheduled_tasks["C"].early_finish == date(2026, 10, 9)
    assert result.scheduled_tasks["C"].total_float == 6
    assert result.scheduled_tasks["C"].is_critical is False

    # D: Wed 10-14, Thu 10-15, Fri 10-16, Mon 10-19, Tue 10-20 (5 days)
    assert result.scheduled_tasks["D"].early_start == date(2026, 10, 14)
    assert result.scheduled_tasks["D"].early_finish == date(2026, 10, 20)
    assert result.scheduled_tasks["D"].total_float == 0
    assert result.scheduled_tasks["D"].is_critical is True

    # E: Mon 10-12 (1 day). Float should be 6 working days
    assert result.scheduled_tasks["E"].early_start == date(2026, 10, 12)
    assert result.scheduled_tasks["E"].early_finish == date(2026, 10, 12)
    assert result.scheduled_tasks["E"].total_float == 6
    assert result.scheduled_tasks["E"].is_critical is False

    # F: Wed 10-21, Thu 10-22 (2 days)
    assert result.scheduled_tasks["F"].early_start == date(2026, 10, 21)
    assert result.scheduled_tasks["F"].early_finish == date(2026, 10, 22)
    assert result.scheduled_tasks["F"].total_float == 0
    assert result.scheduled_tasks["F"].is_critical is True

    # Overall project finish
    assert result.project_finish_date == date(2026, 10, 22)
    assert result.critical_path == ["A", "B", "D", "F"]
    assert result.is_feasible is True


def test_infeasible_schedule_with_tight_target():
    clock = FrozenClock(date(2026, 10, 5))
    scheduler = DeterministicScheduler(clock)

    tasks = {
        "A": Task(id="A", title="Task A", estimated_hours=40.0),  # 5 days: 10-05 to 10-09
        "B": Task(id="B", title="Task B", estimated_hours=40.0),  # 5 days: 10-12 to 10-16
    }
    dependencies = [Dependency(predecessor_id="A", successor_id="B")]

    # Target completion date is 2026-10-12, but project takes until 2026-10-16
    plan = ProjectPlan(
        id="P_tight",
        project_id="PROJ",
        version=1,
        name="Tight Target Plan",
        created_at=datetime.now(UTC),
        tasks=tasks,
        dependencies=dependencies,
        target_completion_date=date(2026, 10, 12),
    )

    result = scheduler.schedule(plan, start_date=date(2026, 10, 5))
    assert result.is_feasible is False
    # Negative float detected on critical tasks
    assert result.scheduled_tasks["B"].total_float < 0


def test_member_workload_and_overallocation():
    clock = FrozenClock(date(2026, 10, 5))
    scheduler = DeterministicScheduler(clock)

    # Alice has 8h/day capacity
    alice = Member(id="M_ALICE", name="Alice", daily_capacity_hours=8.0)

    # Two parallel tasks both assigned to Alice on Monday 2026-10-05
    tasks = {
        "T1": Task(id="T1", title="Task 1", estimated_hours=8.0, assigned_to_id="M_ALICE"),
        "T2": Task(id="T2", title="Task 2", estimated_hours=8.0, assigned_to_id="M_ALICE"),
    }
    # No dependency between T1 and T2 -> both run simultaneously on Monday
    plan = ProjectPlan(
        id="P_workload",
        project_id="PROJ",
        version=1,
        name="Workload Test",
        created_at=datetime.now(UTC),
        tasks=tasks,
        dependencies=[],
        members={"M_ALICE": alice},
    )

    result = scheduler.schedule(plan, start_date=date(2026, 10, 5))
    workload = result.member_workloads["M_ALICE"]

    assert workload.total_assigned_hours == 16.0
    # 8h + 8h = 16h on 2026-10-05
    assert workload.daily_allocated_hours[date(2026, 10, 5)] == 16.0
    assert workload.peak_daily_hours == 16.0
    assert workload.is_overallocated is True
    assert date(2026, 10, 5) in workload.overallocated_dates


def test_overdue_flag_in_scheduled_tasks():
    # Clock set to Wednesday 2026-10-07
    clock = FrozenClock(date(2026, 10, 7))
    scheduler = DeterministicScheduler(clock)

    tasks = {
        # Overdue: due date 10-06, status TODO
        "T_OVERDUE": Task(
            id="T_OVERDUE",
            title="Overdue task",
            status=TaskStatus.TODO,
            due_date=date(2026, 10, 6),
            estimated_hours=8.0,
        ),
        # On time: due date 10-08
        "T_OK": Task(
            id="T_OK",
            title="Ok task",
            status=TaskStatus.TODO,
            due_date=date(2026, 10, 8),
            estimated_hours=8.0,
        ),
    }

    plan = ProjectPlan(
        id="P_overdue",
        project_id="PROJ",
        version=1,
        name="Overdue Plan",
        created_at=datetime.now(UTC),
        tasks=tasks,
    )

    result = scheduler.schedule(plan)
    assert result.scheduled_tasks["T_OVERDUE"].is_overdue is True
    assert result.scheduled_tasks["T_OK"].is_overdue is False
