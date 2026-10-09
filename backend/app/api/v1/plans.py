"""API endpoints for immutable versioned plan snapshots."""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_async_session
from backend.app.domain.graph import CycleDetectedError, TaskGraph, TaskNotFoundError
from backend.app.domain.models import (
    Dependency,
    Member,
    ProjectPlan,
    Task,
)
from backend.app.repositories.plan_repository import (
    PlanImmutableError,
    PlanRepository,
)
from backend.app.repositories.project_repository import ProjectRepository
from backend.app.schemas.mappers import domain_plan_to_response
from backend.app.schemas.plan import (
    PlanCreateRequest,
    PlanResponseSchema,
    PlanVersionListResponse,
)

router = APIRouter(prefix="/projects/{project_id}/plans", tags=["plans"])

_domain_plan_to_response = domain_plan_to_response


@router.post("", response_model=PlanResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_plan_snapshot(
    project_id: str,
    req: PlanCreateRequest,
    session: AsyncSession = Depends(get_async_session),
) -> PlanResponseSchema:
    """Submit a new immutable plan snapshot (Rule 5: version increment, no overwrite)."""
    project_repo = ProjectRepository(session)
    project = await project_repo.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )

    # 1. Build domain tasks and dependencies
    domain_tasks: dict[str, Task] = {
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
        for t in req.tasks
    }
    domain_deps: list[Dependency] = [
        Dependency(
            predecessor_id=d.predecessor_id,
            successor_id=d.successor_id,
            dep_type=d.dep_type,
            lag_days=d.lag_days,
        )
        for d in req.dependencies
    ]

    # 2. Deterministic validation: verify DAG integrity and cycles
    try:
        graph = TaskGraph(tasks=domain_tasks.values(), dependencies=domain_deps)
        graph.validate_dag()
    except TaskNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except CycleDetectedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": str(exc),
                "cycle": exc.cycle_path,
            },
        ) from exc

    # Load members
    members = {
        m.id: Member(
            id=m.id,
            name=m.name,
            role=m.role,
            daily_capacity_hours=m.daily_capacity_hours,
        )
        for m in project.members
    }

    domain_plan = ProjectPlan(
        id=str(uuid4()),
        project_id=project_id,
        version=req.version,
        name=req.name,
        created_at=datetime.now(UTC),
        tasks=domain_tasks,
        dependencies=domain_deps,
        members=members,
        target_completion_date=req.target_completion_date,
        created_by=req.created_by,
    )

    # 3. Save snapshot to repository
    plan_repo = PlanRepository(session)
    try:
        await plan_repo.save_plan_snapshot(domain_plan, activate=True)
        await session.commit()
    except PlanImmutableError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return _domain_plan_to_response(domain_plan)


@router.get("/active", response_model=PlanResponseSchema)
async def get_active_plan(
    project_id: str,
    session: AsyncSession = Depends(get_async_session),
) -> PlanResponseSchema:
    """Fetch the currently active plan snapshot."""
    plan_repo = PlanRepository(session)
    plan = await plan_repo.get_active_plan(project_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active plan found for project '{project_id}'.",
        )
    return _domain_plan_to_response(plan)


@router.get("/versions", response_model=PlanVersionListResponse)
async def list_plan_versions(
    project_id: str,
    session: AsyncSession = Depends(get_async_session),
) -> PlanVersionListResponse:
    """List all immutable version numbers available for a project."""
    plan_repo = PlanRepository(session)
    versions = await plan_repo.list_plan_versions(project_id)
    active = await plan_repo.get_active_plan(project_id)
    return PlanVersionListResponse(
        project_id=project_id,
        versions=versions,
        active_version=active.version if active else None,
    )


@router.get("/{version}", response_model=PlanResponseSchema)
async def get_plan_by_version(
    project_id: str,
    version: int,
    session: AsyncSession = Depends(get_async_session),
) -> PlanResponseSchema:
    """Retrieve an immutable historical plan snapshot by its version number."""
    plan_repo = PlanRepository(session)
    plan = await plan_repo.get_plan_by_version(project_id, version)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan version {version} not found for project '{project_id}'.",
        )
    return _domain_plan_to_response(plan)
