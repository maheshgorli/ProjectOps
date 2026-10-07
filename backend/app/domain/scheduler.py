"""Deterministic Critical Path Method (CPM) and Capacity Scheduler.

Rules:
- Deterministic code owns truth: dates, graphs, critical path, scheduling, workload.
- Pure Python: No I/O, no DB, no LLM. Takes injectable Clock.
"""

from dataclasses import dataclass, field
from datetime import date

from backend.app.domain.calendar import (
    add_working_days,
    calculate_task_finish_date,
    calculate_task_start_date,
    next_working_day,
    working_days_delta,
)
from backend.app.domain.clock import Clock
from backend.app.domain.graph import TaskGraph
from backend.app.domain.models import ProjectPlan


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
        # 1. Base project start date
        base_start = start_date if start_date is not None else self.clock.today()
        proj_start = next_working_day(base_start)

        # Handle empty plan gracefully
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

        # 2. Build graph and validate DAG (detect cycles deterministically)
        graph = TaskGraph(tasks=plan.tasks.values(), dependencies=plan.dependencies)
        topo_order = graph.topological_sort()

        # 3. Calculate task durations
        task_durations: dict[str, int] = {}
        for t_id, task in plan.tasks.items():
            member_cap = plan.get_member_capacity(task.assigned_to_id)
            task_durations[t_id] = task.duration_days(member_cap)

        # 4. Forward Pass (Early Start & Early Finish)
        early_start: dict[str, date] = {}
        early_finish: dict[str, date] = {}

        # Map dependencies for quick lookup
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
                    # Successor starts on next working day after predecessor finishes + lag
                    p_next = add_working_days(early_finish[p], 1 + lag)
                    earliest_possible.append(p_next)
                es = max(earliest_possible)

            early_start[u] = es
            dur = task_durations[u]
            early_finish[u] = calculate_task_finish_date(es, dur)

        # 5. Determine Project Finish Date
        project_finish = max(early_finish.values())

        # Determine target finish for backward pass
        effective_target = plan.target_completion_date or project_finish
        if effective_target < project_finish:
            # Target is tighter than earliest feasible finish
            backward_finish_bound = effective_target
        else:
            backward_finish_bound = max(project_finish, effective_target)

        # 6. Backward Pass (Late Finish & Late Start)
        late_finish: dict[str, date] = {}
        late_start: dict[str, date] = {}

        # Reverse topological order for backward pass
        rev_topo_order = list(reversed(topo_order))

        for u in rev_topo_order:
            succs = graph.successors[u]
            if not succs:
                lf = backward_finish_bound
            else:
                latest_possible = []
                for s in succs:
                    lag = dep_map.get((u, s), 0)
                    # Late start minus 1 minus lag
                    u_latest = add_working_days(late_start[s], -(1 + lag))
                    latest_possible.append(u_latest)
                lf = min(latest_possible)

            late_finish[u] = lf
            dur = task_durations[u]
            late_start[u] = calculate_task_start_date(lf, dur)

        # 7. Total Float & Critical Path Identification
        scheduled_tasks: dict[str, ScheduledTask] = {}
        critical_task_ids: set[str] = set()

        for t_id in topo_order:
            es = early_start[t_id]
            ls = late_start[t_id]
            float_days = working_days_delta(es, ls)
            # A task is on the critical path if float is zero (or <= 0 if behind target)
            is_critical = float_days <= 0
            if is_critical:
                critical_task_ids.add(t_id)

            task_obj = plan.tasks[t_id]
            overdue = task_obj.is_overdue(self.clock)

            scheduled_tasks[t_id] = ScheduledTask(
                task_id=t_id,
                early_start=es,
                early_finish=early_finish[t_id],
                late_start=ls,
                late_finish=late_finish[t_id],
                duration_days=task_durations[t_id],
                total_float=float_days,
                is_critical=is_critical,
                is_overdue=overdue,
            )

        # Critical path ordered by topological sequence
        ordered_critical_path = [t_id for t_id in topo_order if t_id in critical_task_ids]

        # 8. Member Workload & Capacity Allocation
        member_workloads = self._compute_member_workloads(plan, scheduled_tasks)

        # Feasibility check: project finish <= target completion date (if target set)
        is_feasible = True
        if plan.target_completion_date is not None and project_finish > plan.target_completion_date:
            is_feasible = False

        return ScheduleResult(
            project_start_date=proj_start,
            project_finish_date=project_finish,
            target_completion_date=plan.target_completion_date,
            scheduled_tasks=scheduled_tasks,
            critical_path=ordered_critical_path,
            member_workloads=member_workloads,
            is_feasible=is_feasible,
        )

    def _compute_member_workloads(
        self,
        plan: ProjectPlan,
        scheduled_tasks: dict[str, ScheduledTask],
    ) -> dict[str, MemberWorkload]:
        """Compute per-member daily capacity utilization and flag over-allocations."""
        workloads: dict[str, MemberWorkload] = {}

        # Initialize workloads for all known members in plan
        for m_id, member in plan.members.items():
            workloads[m_id] = MemberWorkload(
                member_id=m_id,
                capacity_hours_per_day=member.daily_capacity_hours,
            )

        # Accumulate daily hours from scheduled tasks
        for t_id, st in scheduled_tasks.items():
            task = plan.tasks[t_id]
            if not task.assigned_to_id:
                continue

            m_id = task.assigned_to_id
            if m_id not in workloads:
                workloads[m_id] = MemberWorkload(
                    member_id=m_id,
                    capacity_hours_per_day=plan.get_member_capacity(m_id),
                )

            mw = workloads[m_id]
            mw.total_assigned_hours += task.estimated_hours

            dur = max(1, st.duration_days)
            daily_rate = task.estimated_hours / dur

            # Distribute rate over each working day from early_start to early_finish
            curr = st.early_start
            while curr <= st.early_finish:
                existing = mw.daily_allocated_hours.get(curr, 0.0)
                mw.daily_allocated_hours[curr] = existing + daily_rate
                curr = add_working_days(curr, 1)

        # Analyze over-allocations and peaks
        for mw in workloads.values():
            for day, hours in mw.daily_allocated_hours.items():
                if hours > mw.peak_daily_hours:
                    mw.peak_daily_hours = hours
                if hours > mw.capacity_hours_per_day + 1e-6:
                    mw.is_overallocated = True
                    mw.overallocated_dates.append(day)
            mw.overallocated_dates.sort()

        return workloads
