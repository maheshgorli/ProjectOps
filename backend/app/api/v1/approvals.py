"""API endpoints for Human Approval Gateway (Core Principle 4 & P0-1 fix)."""

from datetime import UTC, date, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_async_session
from backend.app.domain.graph import CycleDetectedError, TaskGraph, TaskNotFoundError
from backend.app.domain.models import (
    Dependency,
    DependencyType,
    Member,
    ProjectPlan,
    Task,
    TaskStatus,
)
from backend.app.models.proposal import ReplanProposalORM
from backend.app.repositories.execution_repository import ExecutionRepository
from backend.app.repositories.history_repository import HistoryRepository
from backend.app.repositories.plan_repository import PlanImmutableError, PlanRepository
from backend.app.repositories.project_repository import ProjectRepository
from backend.app.repositories.proposal_repository import ProposalRepository
from backend.app.schemas.approval import (
    ReplanApprovalRequest,
    ReplanApprovalResponse,
    ReplanProposalResponse,
    ReplanRejectionRequest,
    ReplanRejectionResponse,
)
from backend.app.schemas.mappers import domain_plan_to_response as _domain_plan_to_response
from backend.app.schemas.plan import PlanResponseSchema

router = APIRouter(prefix="/projects/{project_id}/replan", tags=["approvals"])


def _to_proposal_response(p: ReplanProposalORM) -> ReplanProposalResponse:
    return ReplanProposalResponse(
        id=p.id,
        project_id=p.project_id,
        baseline_version=p.baseline_version,
        candidate_plan=PlanResponseSchema.model_validate(p.candidate_plan),
        risks_addressed=p.risks_addressed or [],
        explanation=p.explanation or "",
        status=p.status,
        created_by=p.created_by,
        created_at=p.created_at,
        decided_by=p.decided_by,
        decided_at=p.decided_at,
        rationale=p.rationale,
    )


@router.get("/proposals", response_model=list[ReplanProposalResponse])
async def list_replan_proposals(
    project_id: str,
    status: str | None = Query(
        None, description="Filter by status: PENDING, APPROVED, REJECTED, SUPERSEDED"
    ),
    session: AsyncSession = Depends(get_async_session),
) -> list[ReplanProposalResponse]:
    """List all replan proposals for a project, optionally filtered by status."""
    project_repo = ProjectRepository(session)
    project = await project_repo.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if hasattr(status, "HTTP_404_NOT_FOUND") else 404,
            detail=f"Project '{project_id}' not found.",
        )

    proposal_repo = ProposalRepository(session)
    proposals = await proposal_repo.list_proposals(project_id, status=status)
    return [_to_proposal_response(p) for p in proposals]


@router.get("/proposals/{proposal_id}", response_model=ReplanProposalResponse)
async def get_replan_proposal(
    project_id: str,
    proposal_id: str,
    session: AsyncSession = Depends(get_async_session),
) -> ReplanProposalResponse:
    """Retrieve details of an individual server-stored replan proposal."""
    project_repo = ProjectRepository(session)
    project = await project_repo.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project_id}' not found.",
        )

    proposal_repo = ProposalRepository(session)
    proposal = await proposal_repo.get_proposal(project_id, proposal_id)
    if not proposal:
        raise HTTPException(
            status_code=404,
            detail=f"Replan proposal '{proposal_id}' not found for project '{project_id}'.",
        )
    return _to_proposal_response(proposal)


@router.post("/approve", response_model=ReplanApprovalResponse)
async def approve_candidate_replan(
    project_id: str,
    req: ReplanApprovalRequest,
    session: AsyncSession = Depends(get_async_session),
) -> ReplanApprovalResponse:
    """
    Approve and activate a server-stored candidate replan snapshot.

    Enforces:
    - P0-1 Fix: Approval operates only on pre-stored server proposals, never client body plans.
    - Rule 4: Replanning requires human approval. Never silently change a plan.
    - Rule 5: Plans are immutable, versioned snapshots. Never overwrite history.
    - Proposal must exist and have status PENDING.
    - Proposal baseline_version must match the currently active plan version (reject stale).
    - Carries forward task execution states into the new plan version.
    """
    project_repo = ProjectRepository(session)
    project = await project_repo.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project_id}' not found.",
        )

    proposal_repo = ProposalRepository(session)
    proposal = await proposal_repo.get_proposal(project_id, req.proposal_id)
    if not proposal:
        raise HTTPException(
            status_code=404,
            detail=f"Replan proposal '{req.proposal_id}' not found.",
        )

    if proposal.status != "PENDING":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Proposal '{proposal.id}' has status '{proposal.status}' "
                "and cannot be approved. Only PENDING proposals can be approved."
            ),
        )

    plan_repo = PlanRepository(session)
    active_plan = await plan_repo.get_active_plan(project_id)
    prev_version = active_plan.version if active_plan else 0

    # Stale baseline check: ensure proposal was simulated against the active version
    if proposal.baseline_version != prev_version:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Proposal is stale: baseline version {proposal.baseline_version} "
                f"does not match current active plan version {prev_version}."
            ),
        )

    # Reconstruct domain entities from server-stored proposal snapshot
    candidate_data = proposal.candidate_plan
    raw_tasks = candidate_data.get("tasks", [])
    raw_deps = candidate_data.get("dependencies", [])

    domain_tasks: dict[str, Task] = {
        t["id"]: Task(
            id=t["id"],
            title=t["title"],
            description=t.get("description", ""),
            status=TaskStatus(t["status"]) if "status" in t else TaskStatus.TODO,
            estimated_hours=float(t.get("estimated_hours", 8.0)),
            assigned_to_id=t.get("assigned_to_id"),
            due_date=date.fromisoformat(t["due_date"]) if t.get("due_date") else None,
            start_date=date.fromisoformat(t["start_date"]) if t.get("start_date") else None,
        )
        for t in raw_tasks
    }
    domain_deps: list[Dependency] = [
        Dependency(
            predecessor_id=d["predecessor_id"],
            successor_id=d["successor_id"],
            dep_type=(
                DependencyType(d["dep_type"]) if "dep_type" in d else DependencyType.FINISH_TO_START
            ),
            lag_days=int(d.get("lag_days", 0)),
        )
        for d in raw_deps
    ]

    # Validate DAG deterministically
    try:
        graph = TaskGraph(tasks=domain_tasks.values(), dependencies=domain_deps)
        graph.validate_dag()
    except (TaskNotFoundError, CycleDetectedError) as exc:
        raise HTTPException(
            status_code=422,
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

    new_version = prev_version + 1
    new_plan_id = str(uuid4())
    target_date_str = candidate_data.get("target_completion_date")
    target_date = date.fromisoformat(target_date_str) if target_date_str else None

    new_plan = ProjectPlan(
        id=new_plan_id,
        project_id=project_id,
        version=new_version,
        name=candidate_data.get("name") or f"Plan v{new_version}",
        target_completion_date=target_date,
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
            status_code=409,
            detail=str(exc),
        ) from exc

    # Carry forward and backfill task execution states for the new plan
    exec_repo = ExecutionRepository(session)
    await exec_repo.backfill_execution_states_from_plan(project_id, saved_plan)

    # Mark proposal APPROVED
    await proposal_repo.mark_approved(
        proposal=proposal,
        decided_by=req.decided_by,
        rationale=req.decision_rationale,
    )

    # Rule 5: Record immutable governance decision record
    history_repo = HistoryRepository(session)
    decision = await history_repo.record_decision(
        project_id=project_id,
        plan_id=saved_plan.id,
        decision_type="REPLAN_APPROVED",
        summary=(
            f"Approved Replan proposal {proposal.id} from v{prev_version} to v{saved_plan.version}"
        ),
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
            f"Candidate replan proposal {proposal.id} approved and activated by {req.decided_by}. "
            f"Rationale: {req.decision_rationale}"
        ),
        recorded_by=req.decided_by,
    )

    # Record APPROVE loop stage in agent runs
    await history_repo.record_agent_run(
        project_id=project_id,
        loop_stage="APPROVE",
        status="SUCCESS",
        summary=f"Replan proposal {proposal.id} approved by {req.decided_by}.",
        triggered_by="human_approval",
    )

    await session.commit()

    return ReplanApprovalResponse(
        project_id=project_id,
        proposal_id=proposal.id,
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
            status_code=404,
            detail=f"Project '{project_id}' not found.",
        )

    proposal_repo = ProposalRepository(session)
    proposal = await proposal_repo.get_proposal(project_id, req.proposal_id)
    if not proposal:
        raise HTTPException(
            status_code=404,
            detail=f"Replan proposal '{req.proposal_id}' not found.",
        )

    if proposal.status != "PENDING":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Proposal '{proposal.id}' has status '{proposal.status}' "
                "and cannot be rejected. Only PENDING proposals can be rejected."
            ),
        )

    plan_repo = PlanRepository(session)
    active_plan = await plan_repo.get_active_plan(project_id)
    current_version = active_plan.version if active_plan else 0

    # Mark proposal REJECTED in database
    await proposal_repo.mark_rejected(
        proposal=proposal,
        decided_by=req.decided_by,
        rationale=req.rationale,
    )

    history_repo = HistoryRepository(session)
    decision = await history_repo.record_decision(
        project_id=project_id,
        plan_id=active_plan.id if active_plan else None,
        decision_type="REPLAN_REJECTED",
        summary=f"Rejected candidate replan proposal {proposal.id} by {req.decided_by}",
        rationale=req.rationale,
        decided_by=req.decided_by,
    )

    # Record APPROVE loop stage rejection in agent runs
    await history_repo.record_agent_run(
        project_id=project_id,
        loop_stage="APPROVE",
        status="REJECTED",
        summary=f"Replan candidate proposal {proposal.id} rejected by {req.decided_by}.",
        triggered_by="human_approval",
    )

    await session.commit()

    return ReplanRejectionResponse(
        project_id=project_id,
        proposal_id=proposal.id,
        current_version=current_version,
        decision_id=decision.id,
        status="REJECTED",
        rationale=req.rationale,
    )
