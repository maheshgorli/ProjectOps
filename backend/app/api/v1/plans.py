"""API endpoints for immutable versioned plan snapshots and activation."""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import (
    require_project_member,
    require_project_owner,
)
from backend.app.db.session import get_async_session
from backend.app.domain.graph import CycleDetectedError, TaskGraph, TaskNotFoundError
from backend.app.domain.models import (
    Dependency,
    Member,
    ProjectPlan,
    Task,
)
from backend.app.models.auth import ProjectMembershipORM
from backend.app.models.plan import ProjectPlanORM
from backend.app.repositories.execution_repository import ExecutionRepository
from backend.app.repositories.history_repository import HistoryRepository
from backend.app.repositories.plan_repository import (
    PlanImmutableError,
    PlanRepository,
)
from backend.app.repositories.project_repository import ProjectRepository
from backend.app.schemas.mappers import domain_plan_to_response
from backend.app.schemas.plan import (
    PlanActivateRequest,
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
    _membership: ProjectMembershipORM = Depends(require_project_owner),
    session: AsyncSession = Depends(get_async_session),
) -> PlanResponseSchema:
    """
    Submit a new immutable plan snapshot in DRAFT state (activate=False).

    Server assigns monotonically increasing version number (max existing + 1).
    Rule 4 & 5: Creating a plan never silently activates it.
    Owner role required.
    """
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

    # Server assigns monotonically increasing version
    plan_repo = PlanRepository(session)
    next_version = (await plan_repo.get_latest_version_number(project_id)) + 1

    domain_plan = ProjectPlan(
        id=str(uuid4()),
        project_id=project_id,
        version=next_version,
        name=req.name,
        created_at=datetime.now(UTC),
        tasks=domain_tasks,
        dependencies=domain_deps,
        members=members,
        target_completion_date=req.target_completion_date,
        created_by=_membership.user_id,
    )

    # 3. Save snapshot to repository as inactive draft
    try:
        await plan_repo.save_plan_snapshot(domain_plan, activate=False)
        await session.commit()
    except PlanImmutableError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return _domain_plan_to_response(domain_plan)


@router.post("/{version}/activate", response_model=PlanResponseSchema)
async def activate_initial_plan(
    project_id: str,
    version: int,
    req: PlanActivateRequest,
    _membership: ProjectMembershipORM = Depends(require_project_owner),
    session: AsyncSession = Depends(get_async_session),
) -> PlanResponseSchema:
    """
    Officially activate an initial plan snapshot (Owner only).

    Allowed ONLY when the project currently has NO active plan.
    If an active plan already exists, changes must go through /replan proposals.
    Records PLAN_ACTIVATED decision, progress audit event, agent-run APPROVE entry,
    and backfills task execution states in one atomic transaction.
    """
    plan_repo = PlanRepository(session)

    # 1. Reject if an active plan already exists
    active_plan = await plan_repo.get_active_plan(project_id)
    if active_plan is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Project already has an active plan. Changes to an active plan "
                "must go through /replan proposals."
            ),
        )

    # 2. Verify target plan version exists
    target_plan = await plan_repo.get_plan_by_version(project_id, version)
    if not target_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan version {version} not found for project '{project_id}'.",
        )

    # 3. Activate target plan version in database
    activate_stmt = (
        update(ProjectPlanORM)
        .where(
            ProjectPlanORM.project_id == project_id,
            ProjectPlanORM.version == version,
        )
        .values(is_active=True)
    )
    await session.execute(activate_stmt)

    # 4. Record governance decision
    history_repo = HistoryRepository(session)
    await history_repo.record_decision(
        project_id=project_id,
        plan_id=target_plan.id,
        decision_type="PLAN_ACTIVATED",
        summary=f"Activated initial plan v{version}: {target_plan.name}",
        rationale=req.rationale,
        decided_by=_membership.user_id,
    )

    # 5. Record progress event
    await history_repo.record_progress(
        project_id=project_id,
        task_id="PROJECT_PLAN",
        previous_status="DRAFT",
        new_status=f"v{version}",
        evidence_notes=(
            f"Initial plan v{version} activated by {_membership.user_id}. "
            f"Rationale: {req.rationale}"
        ),
        recorded_by=_membership.user_id,
    )

    # 6. Record agent run APPROVE entry
    await history_repo.record_agent_run(
        project_id=project_id,
        loop_stage="APPROVE",
        status="SUCCESS",
        summary=f"Initial plan v{version} activated by {_membership.user_id}.",
        triggered_by=f"user:{_membership.user_id}",
    )

    # 7. Backfill execution states from newly activated plan
    exec_repo = ExecutionRepository(session)
    await exec_repo.backfill_execution_states_from_plan(project_id, target_plan)

    await session.commit()

    # Re-fetch active plan to return accurate state
    activated_domain_plan = await plan_repo.get_plan_by_version(project_id, version)
    return _domain_plan_to_response(activated_domain_plan or target_plan)


@router.get("/active", response_model=PlanResponseSchema)
async def get_active_plan(
    project_id: str,
    _membership: ProjectMembershipORM = Depends(require_project_member),
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
    _membership: ProjectMembershipORM = Depends(require_project_member),
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
    _membership: ProjectMembershipORM = Depends(require_project_member),
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
