"""Deterministic delay impact analysis.

Simulates delaying a task by N working days, computes directly and indirectly affected tasks,
identifies affected team members, and computes the projected project end-date shift
by re-running the deterministic scheduler.
Pure Python, zero I/O.
"""

from copy import copy
from datetime import date

from backend.app.domain.calendar import working_days_delta
from backend.app.domain.graph import TaskGraph
from backend.app.domain.models import Dependency, ImpactReport, Member, Task
from backend.app.domain.scheduler import schedule_project


def calculate_delay_impact(
    task_id: str,
    delay_working_days: int,
    tasks: dict[str, Task],
    dependencies: list[Dependency],
    members: dict[str, Member],
    project_start_date: date,
    deadline: date | None = None,
) -> ImpactReport:
    """Analyze the downstream impact of delaying a specific task.

    Args:
        task_id: The ID of the task being delayed.
        delay_working_days: Number of working days to delay the task.
        tasks: Dictionary of tasks.
        dependencies: Precedence dependencies.
        members: Project members.
        project_start_date: Project kick-off date.
        deadline: Optional project completion deadline.

    Returns:
        ImpactReport with affected tasks, members, and end-date shift.
    """
    if task_id not in tasks:
        raise ValueError(f"Task '{task_id}' not found in project tasks.")

    graph = TaskGraph(tasks.values(), dependencies)

    # 1. Baseline schedule
    baseline_schedule = schedule_project(
        tasks=tasks,
        dependencies=dependencies,
        members=members,
        project_start_date=project_start_date,
        deadline=deadline,
    )

    # 2. Directly and indirectly affected tasks
    direct_affected = sorted(graph.get_downstream(task_id, transitive=False))
    all_downstream = graph.get_downstream(task_id, transitive=True)
    indirect_affected = sorted(all_downstream - set(direct_affected))

    # 3. Affected members
    affected_tasks_set = {task_id} | all_downstream
    affected_members: set[str] = set()
    for tid in affected_tasks_set:
        assigned_id = tasks[tid].assigned_to_id
        if assigned_id:
            affected_members.add(assigned_id)

    # 4. Construct delayed task scenario
    delayed_tasks: dict[str, Task] = {}
    for tid, t in tasks.items():
        if tid == task_id:
            curr_dur = t.duration_days()
            new_task = copy(t)
            new_task.duration_working_days = curr_dur + delay_working_days
            delayed_tasks[tid] = new_task
        else:
            delayed_tasks[tid] = t

    # 5. Re-run scheduler with delay
    simulated_schedule = schedule_project(
        tasks=delayed_tasks,
        dependencies=dependencies,
        members=members,
        project_start_date=project_start_date,
        deadline=deadline,
    )

    shift_days = working_days_delta(
        baseline_schedule.project_end_date,
        simulated_schedule.project_end_date,
    )

    return ImpactReport(
        delayed_task_id=task_id,
        delay_days=delay_working_days,
        directly_affected_task_ids=direct_affected,
        indirectly_affected_task_ids=indirect_affected,
        affected_member_ids=sorted(affected_members),
        original_project_end_date=baseline_schedule.project_end_date,
        projected_project_end_date=simulated_schedule.project_end_date,
        end_date_shift_working_days=max(0, shift_days),
    )
