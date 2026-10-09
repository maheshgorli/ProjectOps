"""API endpoints for task execution state and progress updates."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_async_session
from backend.app.domain.clock import SystemClock
from backend.app.domain.models import TaskStatus
from backend.app.repositories.execution_repository import ExecutionRepository
from backend.app.repositories.history_repository import HistoryRepository
from backend.app.repositories.plan_repository import PlanRepository
from backend.app.repositories.project_repository import ProjectRepository
from backend.app.schemas.task import (
    ALLOWED_STATUS_TRANSITIONS,
    TaskMergedResponse,
    TaskStatusUpdateRequest,
)

router = APIRouter(prefix="/projects/{project_id}/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskMergedResponse], status_code=status.HTTP_200_OK)
async def list_project_tasks(
    project_id: str,
    session: AsyncSession = Depends(get_async_session),
) -> list[TaskMergedResponse]:
    """
    List all tasks from the active plan merged with runtime execution state.

    Enforces:
    - Immutable plan snapshots remain the planned baseline truth.
    - Mutable task execution state provides actual runtime progress.
    - OVERDUE is derived dynamically against system clock.
    """
    project_repo = ProjectRepository(session)
    project = await project_repo.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )

    plan_repo = PlanRepository(session)
    active_plan = await plan_repo.get_active_plan(project_id)
    if not active_plan:
        return []

    exec_repo = ExecutionRepository(session)
    return await exec_repo.get_merged_tasks(project_id, active_plan, SystemClock())


@router.get("/{task_id}", response_model=TaskMergedResponse, status_code=status.HTTP_200_OK)
async def get_project_task(
    project_id: str,
    task_id: str,
    session: AsyncSession = Depends(get_async_session),
) -> TaskMergedResponse:
    """Retrieve an individual task with its runtime execution state."""
    project_repo = ProjectRepository(session)
    project = await project_repo.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )

    plan_repo = PlanRepository(session)
    active_plan = await plan_repo.get_active_plan(project_id)
    if not active_plan or task_id not in active_plan.tasks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found in active plan of project '{project_id}'.",
        )

    exec_repo = ExecutionRepository(session)
    merged_tasks = await exec_repo.get_merged_tasks(project_id, active_plan, SystemClock())
    for t in merged_tasks:
        if t.id == task_id:
            return t

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task '{task_id}' not found.",
    )


@router.patch(
    "/{task_id}/status",
    response_model=TaskMergedResponse,
    status_code=status.HTTP_200_OK,
)
async def update_task_status(
    project_id: str,
    task_id: str,
    req: TaskStatusUpdateRequest,
    session: AsyncSession = Depends(get_async_session),
) -> TaskMergedResponse:
    """
    Update the execution state of an existing task.

    Enforces:
    - State transition validation (e.g. TODO -> IN_PROGRESS -> COMPLETED).
    - Every status mutation appends a progress-history audit record (Rule 5).
    - OVERDUE is derived, never stored.
    """
    project_repo = ProjectRepository(session)
    project = await project_repo.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )

    plan_repo = PlanRepository(session)
    active_plan = await plan_repo.get_active_plan(project_id)
    if not active_plan or task_id not in active_plan.tasks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found in active plan of project '{project_id}'.",
        )

    # Validate target status value
    target_status = req.status.upper().strip()
    valid_statuses = {s.value for s in TaskStatus}
    if target_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid task status '{req.status}'. Must be one of: {sorted(valid_statuses)}.",
        )

    exec_repo = ExecutionRepository(session)
    existing_state = await exec_repo.get_task_state(project_id, task_id)
    current_status = (
        existing_state.status if existing_state else active_plan.tasks[task_id].status.value
    )

    # Validate transition
    if target_status != current_status:
        allowed = ALLOWED_STATUS_TRANSITIONS.get(current_status, set())
        if target_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Illegal task status transition from '{current_status}' to '{target_status}'. "
                    f"Allowed transitions from '{current_status}': {sorted(allowed)}."
                ),
            )

    # Update execution state
    await exec_repo.upsert_task_state(
        project_id=project_id,
        task_id=task_id,
        status=target_status,
        actual_start=req.actual_start,
        actual_finish=req.actual_finish,
        actual_hours=req.actual_hours,
        percent_complete=req.percent_complete,
        blocked_reason=req.blocked_reason,
        updated_by=req.updated_by,
    )

    # Append progress event to audit history trail (Rule 5)
    history_repo = HistoryRepository(session)
    await history_repo.record_progress(
        project_id=project_id,
        task_id=task_id,
        new_status=target_status,
        previous_status=current_status,
        evidence_notes=(
            req.evidence_notes or f"Updated status to {target_status} by {req.updated_by}."
        ),
        recorded_by=req.updated_by,
    )

    await session.commit()

    merged_tasks = await exec_repo.get_merged_tasks(project_id, active_plan, SystemClock())
    for t in merged_tasks:
        if t.id == task_id:
            return t

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task '{task_id}' not found after update.",
    )
