"""Deterministic risk evaluation rules.

Pure Python: takes ProjectPlan, ScheduleResult, Clock, and TaskGraph. Zero I/O.
"""

from collections import deque

from backend.app.domain.calendar import (
    working_days_between,
    working_days_delta,
)
from backend.app.domain.clock import Clock
from backend.app.domain.graph import TaskGraph
from backend.app.domain.models import ProjectPlan, TaskStatus
from backend.app.domain.risk.models import (
    DetectedRisk,
    RiskSeverity,
    RiskType,
)
from backend.app.domain.scheduler import ScheduleResult


def evaluate_critical_path_delays(
    plan: ProjectPlan,
    schedule: ScheduleResult,
    clock: Clock,
) -> list[DetectedRisk]:
    """Flag tasks on the critical path that are overdue or currently BLOCKED."""
    risks: list[DetectedRisk] = []
    crit_set = set(schedule.critical_path)

    for task_id in sorted(crit_set):
        task = plan.tasks.get(task_id)
        if not task:
            continue

        if task.is_overdue(clock):
            overdue_days = 0
            if task.due_date:
                overdue_days = max(1, working_days_between(task.due_date, clock.today()) - 1)
            risks.append(
                DetectedRisk(
                    risk_type=RiskType.CRITICAL_PATH_DELAY,
                    severity=RiskSeverity.CRITICAL,
                    description=(
                        f"Critical path task '{task.title}' ({task_id}) is overdue by "
                        f"{overdue_days} working days."
                    ),
                    affected_task_ids=[task_id],
                    metrics={"task_id": task_id, "overdue_working_days": overdue_days},
                )
            )
        elif task.status == TaskStatus.BLOCKED:
            risks.append(
                DetectedRisk(
                    risk_type=RiskType.CRITICAL_PATH_DELAY,
                    severity=RiskSeverity.HIGH,
                    description=(
                        f"Critical path task '{task.title}' ({task_id}) is marked as BLOCKED."
                    ),
                    affected_task_ids=[task_id],
                    metrics={"task_id": task_id, "status": "BLOCKED"},
                )
            )

    return risks


def evaluate_capacity_overloads(
    schedule: ScheduleResult,
) -> list[DetectedRisk]:
    """Flag team members whose allocated workload exceeds daily working capacity."""
    risks: list[DetectedRisk] = []

    for m_id, mw in sorted(schedule.member_workloads.items()):
        if mw.is_overallocated:
            overloaded_count = len(mw.overallocated_dates)
            overload_ratio = mw.peak_daily_hours / max(1.0, mw.capacity_hours_per_day)
            severity = RiskSeverity.CRITICAL if overload_ratio >= 1.5 else RiskSeverity.HIGH

            risks.append(
                DetectedRisk(
                    risk_type=RiskType.CAPACITY_OVERLOAD,
                    severity=severity,
                    description=(
                        f"Member '{m_id}' is over-allocated on {overloaded_count} working days, "
                        f"peaking at {mw.peak_daily_hours:.1f}h/day "
                        f"(capacity is {mw.capacity_hours_per_day:.1f}h/day)."
                    ),
                    metrics={
                        "member_id": m_id,
                        "peak_daily_hours": mw.peak_daily_hours,
                        "capacity_hours": mw.capacity_hours_per_day,
                        "overloaded_days_count": overloaded_count,
                    },
                )
            )

    return risks


def evaluate_blocked_cascades(
    plan: ProjectPlan,
    graph: TaskGraph,
) -> list[DetectedRisk]:
    """Identify blocked tasks and quantify their cascading downstream impact."""
    risks: list[DetectedRisk] = []

    for task_id, task in sorted(plan.tasks.items()):
        if task.status != TaskStatus.BLOCKED:
            continue

        # BFS downstream reachability
        downstream: set[str] = set()
        queue = deque(graph.successors[task_id])
        while queue:
            curr = queue.popleft()
            if curr not in downstream:
                downstream.add(curr)
                queue.extend(graph.successors[curr])

        if downstream:
            severity = RiskSeverity.HIGH if len(downstream) >= 3 else RiskSeverity.MEDIUM
            risks.append(
                DetectedRisk(
                    risk_type=RiskType.BLOCKED_CASCADE,
                    severity=severity,
                    description=(
                        f"Blocked task '{task.title}' ({task_id}) halts "
                        f"{len(downstream)} downstream dependent tasks."
                    ),
                    affected_task_ids=[task_id, *sorted(downstream)],
                    metrics={
                        "task_id": task_id,
                        "downstream_count": len(downstream),
                    },
                )
            )

    return risks


def evaluate_deadline_breach(
    plan: ProjectPlan,
    schedule: ScheduleResult,
) -> list[DetectedRisk]:
    """Check if the deterministic project finish date breaches the target completion date."""
    risks: list[DetectedRisk] = []
    if plan.target_completion_date is None:
        return risks

    if schedule.project_finish_date > plan.target_completion_date:
        breach_days = working_days_delta(
            plan.target_completion_date,
            schedule.project_finish_date,
        )
        risks.append(
            DetectedRisk(
                risk_type=RiskType.DEADLINE_BREACH,
                severity=RiskSeverity.CRITICAL,
                description=(
                    f"Project finish date ({schedule.project_finish_date}) exceeds target "
                    f"completion date ({plan.target_completion_date}) by "
                    f"{breach_days} working days."
                ),
                metrics={
                    "target_date": plan.target_completion_date.isoformat(),
                    "project_finish_date": schedule.project_finish_date.isoformat(),
                    "breach_working_days": breach_days,
                },
            )
        )

    return risks
