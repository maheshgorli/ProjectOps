"""Member workload and capacity utilization analysis.

Computes utilization per member per period = assigned hours / available hours.
Flags overload above a configurable threshold.
Pure Python, zero I/O.
"""

from datetime import date

from backend.app.domain.calendar import (
    working_days_between,
)
from backend.app.domain.models import Member, MemberWorkload, ScheduleEntry, Task


def calculate_member_workloads(
    members: dict[str, Member],
    tasks: dict[str, Task],
    schedule_entries: dict[str, ScheduleEntry],
    period_start: date,
    period_end: date,
    overload_threshold: float = 1.0,
) -> dict[str, MemberWorkload]:
    """Compute member workloads and utilization rates across a specified date interval.

    Args:
        members: Dictionary of project members keyed by member ID.
        tasks: Dictionary of tasks keyed by task ID.
        schedule_entries: Dictionary of schedule entries keyed by task ID.
        period_start: Start date of measurement period.
        period_end: End date of measurement period.
        overload_threshold: Utilization threshold above which is_overloaded is True
            (default 1.0 = 100%).

    Returns:
        Dictionary mapping member_id to MemberWorkload.
    """
    total_working_days = working_days_between(period_start, period_end)
    workloads: dict[str, MemberWorkload] = {}

    for member_id, member in members.items():
        avail_hours = total_working_days * member.daily_capacity_hours
        assigned_hours = 0.0

        for task_id, entry in schedule_entries.items():
            if entry.assignee_id != member_id:
                continue

            task = tasks.get(task_id)
            if not task:
                continue

            # Calculate overlap between [entry.start, entry.end] and [period_start, period_end]
            overlap_start = max(entry.start_date, period_start)
            overlap_end = min(entry.end_date, period_end)

            if overlap_start <= overlap_end:
                overlap_days = working_days_between(overlap_start, overlap_end)
                total_task_days = max(1, task.duration_days(member.daily_capacity_hours))
                hours_in_period = task.estimated_hours * (overlap_days / total_task_days)
                assigned_hours += hours_in_period

        util_rate = (
            (assigned_hours / avail_hours)
            if avail_hours > 0
            else (1.0 if assigned_hours > 0 else 0.0)
        )
        is_overloaded = util_rate > overload_threshold

        workloads[member_id] = MemberWorkload(
            member_id=member_id,
            period_start=period_start,
            period_end=period_end,
            assigned_hours=round(assigned_hours, 2),
            available_hours=round(avail_hours, 2),
            utilization_rate=round(util_rate, 4),
            is_overloaded=is_overloaded,
        )

    return workloads
