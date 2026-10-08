"""Deterministic Critical Path Method (CPM) and Resource-Constrained Scheduler.

Rules:
- Deterministic code owns truth: dates, graphs, critical path, scheduling, workload.
- Pure Python: No I/O, no DB, no LLM. Takes injectable Clock.
- Correctness over optimality: uses a priority-rule heuristic (Critical-Path-First).
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date

from backend.app.domain.calendar import (
    DEFAULT_DAILY_CAPACITY_HOURS,
    add_working_days,
    calculate_task_finish_date,
    calculate_task_start_date,
    next_working_day,
    working_days_delta,
)
from backend.app.domain.clock import Clock
from backend.app.domain.critical_path import calculate_critical_path
from backend.app.domain.graph import TaskGraph
from backend.app.domain.models import (
    Dependency,
    Member,
    ProjectPlan,
    Schedule,
    ScheduleEntry,
    Task,
)


class SchedulingError(Exception):
    """Raised when an impossible schedule is detected."""

    pass


@dataclass(frozen=True)
class ScheduledTask:
    """Schedule timing and float calculations for an individual task."""

    task_id: str
    early_start: date
    early_finish: date
    late_start: date
    late_finish: date
    duration_days: int
    total_float: int
    is_critical: bool
    is_overdue: bool


@dataclass
class MemberWorkload:
    """Workload and capacity utilization for a team member."""

    member_id: str
    capacity_hours_per_day: float
    total_assigned_hours: float = 0.0
    daily_allocated_hours: dict[date, float] = field(default_factory=dict)
    peak_daily_hours: float = 0.0
    is_overallocated: bool = False
    overallocated_dates: list[date] = field(default_factory=list)


@dataclass
class ScheduleResult:
    """Complete deterministic project schedule result."""

    project_start_date: date
    project_finish_date: date
    target_completion_date: date | None
    scheduled_tasks: dict[str, ScheduledTask]
    critical_path: list[str]
    member_workloads: dict[str, MemberWorkload]
    is_feasible: bool


def schedule_project(
    tasks: dict[str, Task] | Iterable[Task],
    dependencies: list[Dependency],
    members: dict[str, Member],
    project_start_date: date,
    deadline: date | None = None,
) -> Schedule:
    """Resource-constrained deterministic scheduler.

    Priority-Rule Heuristic (Critical-Path-First):
    1. Validates the DAG for cycles and self-dependencies.
    2. Runs initial CPM forward/backward passes to determine task slacks.
    3. Simulates timeline day-by-day forward from project_start_date.
    4. When member capacity is constrained, ready tasks are prioritized by:
       - Smallest total slack (critical path first)
       - Longest duration
       - Task ID (alphabetical tie-breaker for strict determinism)
    5. Returns Schedule with entries, end date, and deadline feasibility.
    """
    task_dict: dict[str, Task] = {t.id: t for t in tasks} if not isinstance(tasks, dict) else tasks
    start_date = next_working_day(project_start_date)

    if not task_dict:
        return Schedule(
            entries={},
            project_start_date=start_date,
            project_end_date=start_date,
            meets_deadline=True if deadline is None else (start_date <= deadline),
            deadline=deadline,
            critical_path=[],
        )

    # Validate graph structure
    graph = TaskGraph(task_dict.values(), dependencies)
    graph.validate_dag()

    # Verify assignees exist in members
    for t in task_dict.values():
        if t.assigned_to_id and t.assigned_to_id not in members:
            raise SchedulingError(f"Task '{t.id}' assigned to unknown member '{t.assigned_to_id}'.")

    # Initial CPM pass to establish heuristic priorities (slack)
    cpm_results, critical_path = calculate_critical_path(task_dict, dependencies, start_date)

    scheduled_entries: dict[str, ScheduleEntry] = {}
    completed_dates: dict[str, date] = {}
    member_busy_until: dict[str, date] = {}

    current_date = start_date
    unscheduled = set(task_dict.keys())

    # Build dependency lookup
    dep_lag: dict[tuple[str, str], int] = {
        (d.predecessor_id, d.successor_id): d.lag_days for d in dependencies
    }

    max_simulation_days = 2000  # Guard against infinite loops
    simulation_step = 0

    while unscheduled and simulation_step < max_simulation_days:
        simulation_step += 1
        # 1. Identify ready tasks
        ready_tasks: list[str] = []
        for tid in unscheduled:
            preds = graph.predecessors[tid]
            if all(p in completed_dates for p in preds):
                # Check lag requirements
                can_start = True
                for p in preds:
                    p_finish = completed_dates[p]
                    lag = dep_lag.get((p, tid), 0)
                    min_start = add_working_days(p_finish, 1 + lag)
                    if current_date < min_start:
                        can_start = False
                        break
                if can_start:
                    ready_tasks.append(tid)

        # 2. Sort ready tasks using Critical-Path-First priority rule
        def priority_key(tid: str) -> tuple[int, int, str]:
            cpm_data = cpm_results.get(tid)
            slack = cpm_data.total_slack if cpm_data else 9999
            dur = task_dict[tid].duration_days()
            return (slack, -dur, tid)

        ready_tasks.sort(key=priority_key)

        # 3. Assign tasks to available members
        for tid in list(ready_tasks):
            task = task_dict[tid]
            assignee_id = task.assigned_to_id

            # Check if assigned member is free
            if assignee_id:
                member = members[assignee_id]
                busy_until = member_busy_until.get(assignee_id)
                if busy_until and current_date <= busy_until:
                    # Member is currently busy
                    continue
                daily_cap = member.daily_capacity_hours
            else:
                daily_cap = DEFAULT_DAILY_CAPACITY_HOURS

            # Schedule this task
            dur = task.duration_days(daily_cap)
            t_finish = calculate_task_finish_date(current_date, dur)

            cpm_data = cpm_results.get(tid)
            is_crit = cpm_data.is_critical if cpm_data else False
            slack = cpm_data.total_slack if cpm_data else 0

            scheduled_entries[tid] = ScheduleEntry(
                task_id=tid,
                start_date=current_date,
                end_date=t_finish,
                assignee_id=assignee_id,
                is_critical=is_crit,
                slack_days=slack,
            )
            completed_dates[tid] = t_finish
            if assignee_id:
                member_busy_until[assignee_id] = t_finish

            unscheduled.remove(tid)

        # Advance current date to next working day
        current_date = add_working_days(current_date, 1)

    if unscheduled:
        raise SchedulingError(
            "Failed to schedule tasks due to unresolved resource or dependency "
            f"contention: {unscheduled}"
        )

    project_finish = max(e.end_date for e in scheduled_entries.values())
    meets_deadline = (project_finish <= deadline) if deadline else True

    return Schedule(
        entries=scheduled_entries,
        project_start_date=start_date,
        project_end_date=project_finish,
        meets_deadline=meets_deadline,
        deadline=deadline,
        critical_path=critical_path,
    )


class DeterministicScheduler:
    """Calculates deterministic CPM schedule, critical path, and member workloads."""

    def __init__(self, clock: Clock) -> None:
        self.clock = clock

    def schedule(
        self,
        plan: ProjectPlan,
        start_date: date | None = None,
    ) -> ScheduleResult:
        """Compute deterministic CPM schedule and capacity allocations."""
        base_start = start_date if start_date is not None else self.clock.today()
        proj_start = next_working_day(base_start)

        if not plan.tasks:
            return ScheduleResult(
                project_start_date=proj_start,
                project_finish_date=proj_start,
                target_completion_date=plan.target_completion_date,
                scheduled_tasks={},
                critical_path=[],
                member_workloads={},
                is_feasible=True,
            )

        graph = TaskGraph(tasks=plan.tasks.values(), dependencies=plan.dependencies)
        topo_order = graph.topological_sort()

        task_durations: dict[str, int] = {}
        for t_id, task in plan.tasks.items():
            member_cap = plan.get_member_capacity(task.assigned_to_id)
            task_durations[t_id] = task.duration_days(member_cap)

        early_start: dict[str, date] = {}
        early_finish: dict[str, date] = {}

        dep_map: dict[tuple[str, str], int] = {
            (d.predecessor_id, d.successor_id): d.lag_days for d in plan.dependencies
        }

        for u in topo_order:
            preds = graph.predecessors[u]
            if not preds:
                es = proj_start
            else:
                earliest_possible = []
                for p in preds:
                    lag = dep_map.get((p, u), 0)
                    p_next = add_working_days(early_finish[p], 1 + lag)
                    earliest_possible.append(p_next)
                es = max(earliest_possible)

            early_start[u] = es
            dur = task_durations[u]
            early_finish[u] = calculate_task_finish_date(es, dur)

        project_finish = max(early_finish.values())
        effective_target = plan.target_completion_date or project_finish
        if plan.target_completion_date is not None and plan.target_completion_date < project_finish:
            backward_finish_bound = plan.target_completion_date
        else:
            backward_finish_bound = max(project_finish, effective_target)

        late_finish: dict[str, date] = {}
        late_start: dict[str, date] = {}

        for u in reversed(topo_order):
            succs = graph.successors[u]
            if not succs:
                lf = backward_finish_bound
            else:
                latest_possible = []
                for s in succs:
                    lag = dep_map.get((u, s), 0)
                    s_prev = add_working_days(late_start[s], -(1 + lag))
                    latest_possible.append(s_prev)
                lf = min(latest_possible)

            dur = task_durations[u]
            late_finish[u] = lf
            late_start[u] = calculate_task_start_date(lf, dur)

        scheduled_tasks: dict[str, ScheduledTask] = {}
        critical_path_tasks: list[str] = []

        for u in topo_order:
            es = early_start[u]
            ef = early_finish[u]
            ls = late_start[u]
            lf = late_finish[u]
            dur = task_durations[u]

            total_float = working_days_delta(es, ls)
            is_critical = total_float <= 0

            if is_critical:
                critical_path_tasks.append(u)

            task_obj = plan.tasks[u]
            is_overdue = task_obj.is_overdue(self.clock)

            scheduled_tasks[u] = ScheduledTask(
                task_id=u,
                early_start=es,
                early_finish=ef,
                late_start=ls,
                late_finish=lf,
                duration_days=dur,
                total_float=total_float,
                is_critical=is_critical,
                is_overdue=is_overdue,
            )

        member_workloads: dict[str, MemberWorkload] = {}
        member_daily_hours: dict[str, dict[date, float]] = defaultdict(lambda: defaultdict(float))

        for u, st in scheduled_tasks.items():
            task = plan.tasks[u]
            assignee_id = task.assigned_to_id
            if not assignee_id:
                continue

            cap = plan.get_member_capacity(assignee_id)
            dur_days = st.duration_days
            hours_per_day = task.estimated_hours / dur_days if dur_days > 0 else 0.0

            curr = st.early_start
            for _ in range(dur_days):
                member_daily_hours[assignee_id][curr] += hours_per_day
                curr = add_working_days(curr, 1)

        for m_id, member in plan.members.items():
            daily_hours = member_daily_hours.get(m_id, {})
            total_hours = sum(daily_hours.values())
            peak_hours = max(daily_hours.values()) if daily_hours else 0.0
            cap = member.daily_capacity_hours

            overallocated_dates = [d for d, h in sorted(daily_hours.items()) if h > cap]
            is_overallocated = len(overallocated_dates) > 0

            member_workloads[m_id] = MemberWorkload(
                member_id=m_id,
                capacity_hours_per_day=cap,
                total_assigned_hours=round(total_hours, 2),
                daily_allocated_hours={d: round(h, 2) for d, h in sorted(daily_hours.items())},
                peak_daily_hours=round(peak_hours, 2),
                is_overallocated=is_overallocated,
                overallocated_dates=overallocated_dates,
            )

        is_feasible = True
        if plan.target_completion_date is not None:
            is_feasible = project_finish <= plan.target_completion_date

        return ScheduleResult(
            project_start_date=proj_start,
            project_finish_date=project_finish,
            target_completion_date=plan.target_completion_date,
            scheduled_tasks=scheduled_tasks,
            critical_path=critical_path_tasks,
            member_workloads=member_workloads,
            is_feasible=is_feasible,
        )
