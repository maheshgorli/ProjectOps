"""API endpoints for deterministic CPM scheduling and what-if simulation."""

from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_async_session
from backend.app.domain.calendar import working_days_delta
from backend.app.domain.clock import SystemClock
from backend.app.domain.graph import CycleDetectedError, TaskNotFoundError
from backend.app.domain.models import (
    Dependency,
    ProjectPlan,
    Task,
)
from backend.app.domain.scheduler import DeterministicScheduler, ScheduleResult
from backend.app.repositories.plan_repository import PlanRepository
from backend.app.schemas.schedule import (
    MemberWorkloadResponse,
    ScheduledTaskResponse,
    ScheduleResponse,
    ScheduleSimulationRequest,
    ScheduleSimulationResponse,
)

router = APIRouter(prefix="/projects/{project_id}/schedule", tags=["schedule"])


def _to_schedule_response(result: ScheduleResult) -> ScheduleResponse:
    scheduled_tasks = [
        ScheduledTaskResponse(
            task_id=st.task_id,
            early_start=st.early_start,
            early_finish=st.early_finish,
            late_start=st.late_start,
            late_finish=st.late_finish,
            duration_days=st.duration_days,
            total_float=st.total_float,
            is_critical=st.is_critical,
            is_overdue=st.is_overdue,
        )
        for st in result.scheduled_tasks.values()
    ]
    member_workloads = [
        MemberWorkloadResponse(
            member_id=mw.member_id,
            capacity_hours_per_day=mw.capacity_hours_per_day,
            total_assigned_hours=mw.total_assigned_hours,
            daily_allocated_hours={
                d.isoformat(): hours for d, hours in mw.daily_allocated_hours.items()
            },
            peak_daily_hours=mw.peak_daily_hours,
            is_overallocated=mw.is_overallocated,
            overallocated_dates=mw.overallocated_dates,
        )
        for mw in result.member_workloads.values()
    ]
    return ScheduleResponse(
        project_start_date=result.project_start_date,
        project_finish_date=result.project_finish_date,
        target_completion_date=result.target_completion_date,
        scheduled_tasks=scheduled_tasks,
        critical_path=result.critical_path,
        member_workloads=member_workloads,
        is_feasible=result.is_feasible,
    )


@router.get("", response_model=ScheduleResponse)
async def get_schedule(
    project_id: str,
    version: int | None = Query(None, description="Specific plan version; defaults to active"),
    start_date: date | None = Query(None, description="Override project start date"),
    session: AsyncSession = Depends(get_async_session),
) -> ScheduleResponse:
    """Run deterministic CPM schedule on active or versioned plan."""
    plan_repo = PlanRepository(session)
    if version is not None:
        plan = await plan_repo.get_plan_by_version(project_id, version)
    else:
        plan = await plan_repo.get_active_plan(project_id)

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan not found for project '{project_id}'.",
        )

    scheduler = DeterministicScheduler(SystemClock())
    try:
        result = scheduler.schedule(plan, start_date=start_date)
    except (CycleDetectedError, TaskNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return _to_schedule_response(result)


@router.post("/simulate", response_model=ScheduleSimulationResponse)
async def simulate_schedule(
    project_id: str,
    req: ScheduleSimulationRequest,
    session: AsyncSession = Depends(get_async_session),
) -> ScheduleSimulationResponse:
    """
    Run what-if scenario simulation without saving to database.

    Core Principle 3: Replans are simulated by the deterministic scheduler.
    """
    plan_repo = PlanRepository(session)
    active_plan = await plan_repo.get_active_plan(project_id)
    if not active_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active baseline plan found for project '{project_id}'.",
        )

    scheduler = DeterministicScheduler(SystemClock())
    baseline_result = scheduler.schedule(active_plan, start_date=req.start_date)

    # Build simulated domain plan
    sim_tasks: dict[str, Task] = {
        t.id: Task(
            id=t.id,
            title=t.title,
            description=t.description,
            status=t.status,
            estimated_hours=t.estimated_hours,
            assigned_to_id=t.assigned_to_id,
            due_date=t.due_date,
            start_date=t.start_date,
        )
        for t in req.candidate_tasks
    }
    sim_deps: list[Dependency] = [
        Dependency(
            predecessor_id=d.predecessor_id,
            successor_id=d.successor_id,
            dep_type=d.dep_type,
            lag_days=d.lag_days,
        )
        for d in req.candidate_dependencies
    ]

    simulated_plan = ProjectPlan(
        id="SIMULATED",
        project_id=project_id,
        version=active_plan.version + 1,
        name=f"Simulated what-if on v{active_plan.version}",
        created_at=datetime.now(UTC),
        tasks=sim_tasks,
        dependencies=sim_deps,
        members=active_plan.members,
        target_completion_date=req.target_completion_date or active_plan.target_completion_date,
    )

    try:
        sim_result = scheduler.schedule(simulated_plan, start_date=req.start_date)
    except (CycleDetectedError, TaskNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    delta_days = working_days_delta(
        baseline_result.project_finish_date, sim_result.project_finish_date
    )
    critical_changed = baseline_result.critical_path != sim_result.critical_path

    return ScheduleSimulationResponse(
        baseline_finish_date=baseline_result.project_finish_date,
        simulated_finish_date=sim_result.project_finish_date,
        finish_date_delta_working_days=delta_days,
        critical_path_changed=critical_changed,
        simulation=_to_schedule_response(sim_result),
    )
