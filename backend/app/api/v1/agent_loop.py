"""API endpoints for Autonomous Multi-Agent Loop control and status."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_async_session
from backend.app.domain.clock import SystemClock
from backend.app.engine.execution_loop import ExecutionLoopEngine
from backend.app.repositories.history_repository import HistoryRepository
from backend.app.repositories.plan_repository import PlanRepository
from backend.app.repositories.project_repository import ProjectRepository
from backend.app.schemas.agent_loop import (
    AgentLoopStatusResponse,
    AgentRunSchema,
    LoopStepResponse,
)

router = APIRouter(prefix="/projects/{project_id}/agent-loop", tags=["agent-loop"])


@router.post("/step", response_model=LoopStepResponse)
async def run_agent_loop_step(
    project_id: str,
    triggered_by: str = Query("manual", description="Trigger source (manual, timer, webhook)"),
    session: AsyncSession = Depends(get_async_session),
) -> LoopStepResponse:
    """
    Execute one cycle of the autonomous multi-agent execution loop.

    Flow: PLAN -> EXECUTE -> OBSERVE -> REASON -> (REPLAN -> AWAITING_APPROVAL | CONTINUE)
    Enforces Rule 4: If risks are identified, generates candidate replan and pauses at
    AWAITING_APPROVAL for explicit human governance.
    """
    project_repo = ProjectRepository(session)
    project = await project_repo.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )

    engine = ExecutionLoopEngine(SystemClock())
    result = await engine.run_step(
        project_id=project_id,
        session=session,
        triggered_by=triggered_by,
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
    session: AsyncSession = Depends(get_async_session),
) -> AgentLoopStatusResponse:
    """Retrieve current loop state and recent agent run audit history."""
    project_repo = ProjectRepository(session)
    project = await project_repo.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )

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
