"""Deterministic Critical Path Method (CPM) calculation.

Forward pass, backward pass, earliest/latest dates, slack, and critical path identification.
Pure Python, zero I/O.
"""

from collections.abc import Iterable
from datetime import date

from backend.app.domain.calendar import (
    DEFAULT_DAILY_CAPACITY_HOURS,
    add_working_days,
    calculate_task_finish_date,
    calculate_task_start_date,
    next_working_day,
    working_days_between,
)
from backend.app.domain.graph import TaskGraph
from backend.app.domain.models import CriticalPathData, Dependency, Task


def calculate_critical_path(
    tasks: dict[str, Task] | Iterable[Task],
    dependencies: list[Dependency],
    project_start_date: date,
    daily_capacity_hours: float = DEFAULT_DAILY_CAPACITY_HOURS,
) -> tuple[dict[str, CriticalPathData], list[str]]:
    """Compute the Critical Path Method (CPM) schedule for the given tasks.

    Returns:
        tuple containing:
        - dict mapping task_id to CriticalPathData
        - ordered list of critical path task IDs
    """
    task_dict: dict[str, Task] = {t.id: t for t in tasks} if not isinstance(tasks, dict) else tasks
    if not task_dict:
        return {}, []

    graph = TaskGraph(task_dict.values(), dependencies)
    topo_order = graph.topological_sort()

    start_date = next_working_day(project_start_date)

    # 1. Forward Pass (Early Start & Early Finish)
    early_starts: dict[str, date] = {}
    early_finishes: dict[str, date] = {}

    for task_id in topo_order:
        task = task_dict[task_id]
        dur = task.duration_days(daily_capacity_hours)
        preds = graph.predecessors[task_id]

        if not preds:
            es = start_date
        else:
            cand_starts: list[date] = []
            for pred_id in preds:
                pred_finish = early_finishes[pred_id]
                # Look up lag if defined
                lag = 0
                for dep in dependencies:
                    if dep.predecessor_id == pred_id and dep.successor_id == task_id:
                        lag = dep.lag_days
                        break
                cand_starts.append(add_working_days(pred_finish, 1 + lag))
            es = max(cand_starts)

        ef = calculate_task_finish_date(es, dur)
        early_starts[task_id] = es
        early_finishes[task_id] = ef

    project_finish = max(early_finishes.values()) if early_finishes else start_date

    # 2. Backward Pass (Late Finish & Late Start)
    late_starts: dict[str, date] = {}
    late_finishes: dict[str, date] = {}

    for task_id in reversed(topo_order):
        task = task_dict[task_id]
        dur = task.duration_days(daily_capacity_hours)
        succs = graph.successors[task_id]

        if not succs:
            lf = project_finish
        else:
            cand_finishes: list[date] = []
            for succ_id in succs:
                succ_start = late_starts[succ_id]
                lag = 0
                for dep in dependencies:
                    if dep.predecessor_id == task_id and dep.successor_id == succ_id:
                        lag = dep.lag_days
                        break
                cand_finishes.append(add_working_days(succ_start, -(1 + lag)))
            lf = min(cand_finishes)

        ls = calculate_task_start_date(lf, dur)
        late_starts[task_id] = ls
        late_finishes[task_id] = lf

    # 3. Slack & Critical Path Detection
    cpm_results: dict[str, CriticalPathData] = {}
    critical_path: list[str] = []

    for task_id in topo_order:
        es = early_starts[task_id]
        ls = late_starts[task_id]
        ef = early_finishes[task_id]
        lf = late_finishes[task_id]

        total_slack = 0 if ls <= es else max(0, working_days_between(es, ls) - 1)
        is_critical = total_slack == 0
        if is_critical:
            critical_path.append(task_id)

        cpm_results[task_id] = CriticalPathData(
            task_id=task_id,
            early_start=es,
            early_finish=ef,
            late_start=ls,
            late_finish=lf,
            total_slack=total_slack,
            is_critical=is_critical,
        )

    return cpm_results, critical_path
