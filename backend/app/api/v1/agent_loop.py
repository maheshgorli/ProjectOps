"""API endpoints for Autonomous Multi-Agent Loop control and status."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import require_project_member
from backend.app.db.session import get_async_session
from backend.app.domain.clock import SystemClock
from backend.app.engine.execution_loop import ExecutionLoopEngine
from backend.app.models.auth import ProjectMembershipORM
from backend.app.repositories.history_repository import HistoryRepository
from backend.app.repositories.plan_repository import PlanRepository
from backend.app.schemas.agent_loop import (
    AgentLoopStatusResponse,
    AgentRunSchema,
    LoopStepResponse,
)

router = APIRouter(prefix="/projects/{project_id}/agent-loop", tags=["agent-loop"])


@router.post("/step", response_model=LoopStepResponse)
async def run_agent_loop_step(
    project_id: str,
    _membership: ProjectMembershipORM = Depends(require_project_member),
    session: AsyncSession = Depends(get_async_session),
) -> LoopStepResponse:
    """
    Execute one cycle of the autonomous multi-agent execution loop.

    Flow: PLAN -> EXECUTE -> OBSERVE -> REASON -> (REPLAN -> AWAITING_APPROVAL | CONTINUE)
    Enforces Rule 4: If risks are identified, generates candidate replan and pauses at
    AWAITING_APPROVAL for explicit human governance.
    Triggered source is server-derived as user:<user_id>.
    """
    actor_trigger = f"user:{_membership.user_id}"

    engine = ExecutionLoopEngine(SystemClock())
    result = await engine.run_step(
        project_id=project_id,
        session=session,
        triggered_by=actor_trigger,
    )

    await session.commit()

    return LoopStepResponse(
        project_id=result.project_id,
        current_stage=result.stage,
        status=result.status,
        health_score=result.health_score,
        is_at_risk=result.is_at_risk,
        summary=result.summary,
        detected_risks_count=result.detected_risks_count,
        actionable_tasks=result.actionable_tasks,
        replan_candidate=result.replan_candidate,
        requires_human_approval=result.requires_human_approval,
    )


@router.get("/status", response_model=AgentLoopStatusResponse)
async def get_agent_loop_status(
    project_id: str,
    limit: int = Query(20, ge=1, le=100),
    _membership: ProjectMembershipORM = Depends(require_project_member),
    session: AsyncSession = Depends(get_async_session),
) -> AgentLoopStatusResponse:
    """Retrieve current loop state and recent agent run audit history."""
    plan_repo = PlanRepository(session)
    active_plan = await plan_repo.get_active_plan(project_id)
    active_version = active_plan.version if active_plan else None

    history_repo = HistoryRepository(session)
    runs = await history_repo.get_agent_runs(project_id=project_id, limit=limit)

    current_status = runs[0].status if runs else "IDLE"
    requires_approval = current_status == "AWAITING_APPROVAL"

    return AgentLoopStatusResponse(
        project_id=project_id,
        active_plan_version=active_version,
        current_status=current_status,
        requires_human_approval=requires_approval,
        recent_runs=[
            AgentRunSchema(
                id=r.id,
                project_id=r.project_id,
                loop_stage=r.loop_stage,
                status=r.status,
                summary=r.summary,
                details_json=r.details_json,
                triggered_by=r.triggered_by,
                recorded_at=r.recorded_at,
            )
            for r in runs
        ],
    )
