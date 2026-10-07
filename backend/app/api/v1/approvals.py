"""API endpoints for Human Approval Gateway."""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.plans import _domain_plan_to_response
from backend.app.db.session import get_async_session
from backend.app.domain.graph import CycleDetectedError, TaskGraph, TaskNotFoundError
from backend.app.domain.models import Dependency, Member, ProjectPlan, Task
from backend.app.repositories.history_repository import HistoryRepository
from backend.app.repositories.plan_repository import PlanImmutableError, PlanRepository
from backend.app.repositories.project_repository import ProjectRepository
from backend.app.schemas.approval import (
    ReplanApprovalRequest,
    ReplanApprovalResponse,
    ReplanRejectionRequest,
    ReplanRejectionResponse,
)

router = APIRouter(prefix="/projects/{project_id}/replan", tags=["approvals"])


@router.post("/approve", response_model=ReplanApprovalResponse)
async def approve_candidate_replan(
    project_id: str,
    req: ReplanApprovalRequest,
    session: AsyncSession = Depends(get_async_session),
) -> ReplanApprovalResponse:
    """
    Approve and activate a proposed candidate replan snapshot.

    Enforces:
    - Rule 4: Replanning requires human approval. Never silently change a plan.
    - Rule 5: Plans are immutable, versioned snapshots. Never overwrite history.
    - Appends decision record and progress history.
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
    prev_version = active_plan.version if active_plan else 0
    candidate = req.candidate_plan

    # Rule 5: Immutable version check
    existing_versions = await plan_repo.list_plan_versions(project_id)
    if candidate.version in existing_versions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Plan version {candidate.version} for project '{project_id}' already exists "
                "and cannot be overwritten."
            ),
        )

    new_version = candidate.version if candidate.version > prev_version else prev_version + 1

    # Convert candidate tasks and dependencies into domain entities
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
        for t in candidate.tasks
    }
    domain_deps: list[Dependency] = [
        Dependency(
            predecessor_id=d.predecessor_id,
            successor_id=d.successor_id,
            dep_type=d.dep_type,
            lag_days=d.lag_days,
        )
        for d in candidate.dependencies
    ]

    # Validate DAG deterministically
    try:
        graph = TaskGraph(tasks=domain_tasks.values(), dependencies=domain_deps)
        graph.validate_dag()
    except (TaskNotFoundError, CycleDetectedError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    # Retrieve project members for capacity modeling
    members_list = await project_repo.list_members(project_id)
    domain_members: dict[str, Member] = {
        m.id: Member(
            id=m.id,
            name=m.name,
            role=m.role,
            daily_capacity_hours=m.daily_capacity_hours,
        )
        for m in members_list
    }

    new_plan_id = str(uuid4())
    new_plan = ProjectPlan(
        id=new_plan_id,
        project_id=project_id,
        version=new_version,
        name=candidate.name or f"Plan v{new_version}",
        target_completion_date=candidate.target_completion_date,
        tasks=domain_tasks,
        dependencies=domain_deps,
        members=domain_members,
        created_at=datetime.now(UTC),
        created_by=req.decided_by,
    )

    try:
        saved_plan = await plan_repo.save_plan_snapshot(new_plan, activate=True)
    except PlanImmutableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    # Rule 5: Record immutable governance decision record
    history_repo = HistoryRepository(session)
    decision = await history_repo.record_decision(
        project_id=project_id,
        plan_id=saved_plan.id,
        decision_type="REPLAN_APPROVED",
        summary=f"Approved Replan from v{prev_version} to v{saved_plan.version}",
        rationale=req.decision_rationale,
        decided_by=req.decided_by,
    )

    # Append progress audit trail event
    await history_repo.record_progress(
        project_id=project_id,
        task_id="PROJECT_PLAN",
        previous_status=f"v{prev_version}",
        new_status=f"v{saved_plan.version}",
        evidence_notes=(
            f"Candidate replan approved and activated by {req.decided_by}. "
            f"Rationale: {req.decision_rationale}"
        ),
        recorded_by=req.decided_by,
    )

    # Record APPROVE loop stage in agent runs
    await history_repo.record_agent_run(
        project_id=project_id,
        loop_stage="APPROVE",
        status="SUCCESS",
        summary=f"Replan v{saved_plan.version} approved by {req.decided_by}.",
        triggered_by="human_approval",
    )

    await session.commit()

    return ReplanApprovalResponse(
        project_id=project_id,
        previous_version=prev_version,
        new_version=saved_plan.version,
        decision_id=decision.id,
        status="APPROVED",
        summary=f"Plan upgraded to v{saved_plan.version}",
        plan=_domain_plan_to_response(saved_plan),
    )


@router.post("/reject", response_model=ReplanRejectionResponse)
async def reject_candidate_replan(
    project_id: str,
    req: ReplanRejectionRequest,
    session: AsyncSession = Depends(get_async_session),
) -> ReplanRejectionResponse:
    """
    Reject a proposed candidate replan proposition.

    Enforces:
    - Rule 4: Replanning requires human approval.
    - Rule 5: Records the rejection in the immutable decision audit trail.
    - Active plan remains unchanged.
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
    current_version = active_plan.version if active_plan else 0

    history_repo = HistoryRepository(session)
    decision = await history_repo.record_decision(
        project_id=project_id,
        plan_id=active_plan.id if active_plan else None,
        decision_type="REPLAN_REJECTED",
        summary=f"Rejected candidate replan proposition by {req.decided_by}",
        rationale=req.rationale,
        decided_by=req.decided_by,
    )

    # Record APPROVE loop stage rejection in agent runs
    await history_repo.record_agent_run(
        project_id=project_id,
        loop_stage="APPROVE",
        status="REJECTED",
        summary=f"Replan candidate rejected by {req.decided_by}.",
        triggered_by="human_approval",
    )

    await session.commit()

    return ReplanRejectionResponse(
        project_id=project_id,
        current_version=current_version,
        decision_id=decision.id,
        status="REJECTED",
        rationale=req.rationale,
    )
