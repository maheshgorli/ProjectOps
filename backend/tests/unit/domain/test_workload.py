"""Unit tests for member workload and capacity utilization analysis."""

from datetime import date

from backend.app.domain.models import Member, ScheduleEntry, Task
from backend.app.domain.workload import calculate_member_workloads


def test_member_workload_normal_and_overload():
    members = {
        "m-bob": Member(id="m-bob", name="Bob", daily_capacity_hours=8.0),
        "m-alice": Member(id="m-alice", name="Alice", daily_capacity_hours=8.0),
    }

    # 5 working days period (Mon 2026-11-02 to Fri 2026-11-06) = 40 available hours
    start_date = date(2026, 11, 2)
    end_date = date(2026, 11, 6)

    tasks = {
        "T1": Task(id="T1", title="Task 1", estimated_hours=20.0, duration_working_days=5),
        "T2": Task(id="T2", title="Task 2", estimated_hours=48.0, duration_working_days=5),
    }

    schedule_entries = {
        "T1": ScheduleEntry(
            task_id="T1",
            start_date=start_date,
            end_date=end_date,
            assignee_id="m-bob",
        ),
        "T2": ScheduleEntry(
            task_id="T2",
            start_date=start_date,
            end_date=end_date,
            assignee_id="m-alice",
        ),
    }

    workloads = calculate_member_workloads(
        members=members,
        tasks=tasks,
        schedule_entries=schedule_entries,
        period_start=start_date,
        period_end=end_date,
        overload_threshold=1.0,
    )

    # Bob: 20h / 40h = 50% utilization -> not overloaded
    bob_wl = workloads["m-bob"]
    assert bob_wl.available_hours == 40.0
    assert bob_wl.assigned_hours == 20.0
    assert bob_wl.utilization_rate == 0.5
    assert bob_wl.is_overloaded is False

    # Alice: 48h / 40h = 120% utilization -> overloaded!
    alice_wl = workloads["m-alice"]
    assert alice_wl.available_hours == 40.0
    assert alice_wl.assigned_hours == 48.0
    assert alice_wl.utilization_rate == 1.2
    assert alice_wl.is_overloaded is True
