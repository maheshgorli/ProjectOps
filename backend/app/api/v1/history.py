"""API endpoints for append-only audit trails: progress, decisions, and risks."""

from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_async_session
from backend.app.repositories.history_repository import HistoryRepository
from backend.app.repositories.project_repository import ProjectRepository
from backend.app.schemas.history import (
    DecisionCreateRequest,
    DecisionResponse,
    ProgressEventCreateRequest,
    ProgressEventResponse,
    RiskEventCreateRequest,
    RiskEventResponse,
)

router = APIRouter(prefix="/projects/{project_id}", tags=["history"])


@router.post(
    "/history/progress",
    response_model=ProgressEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_progress_event(
    project_id: str,
    req: ProgressEventCreateRequest,
    session: AsyncSession = Depends(get_async_session),
) -> ProgressEventResponse:
    """Append a task progress event to the audit trail (Rule 5: append-only)."""
    project_repo = ProjectRepository(session)
    project = await project_repo.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )

    history_repo = HistoryRepository(session)
    event = await history_repo.record_progress(
        project_id=project_id,
        task_id=req.task_id,
        new_status=req.new_status,
        previous_status=req.previous_status,
        evidence_notes=req.evidence_notes,
        recorded_by=req.recorded_by,
    )
    await session.commit()
    return ProgressEventResponse.model_validate(event)


@router.get("/history/progress", response_model=list[ProgressEventResponse])
async def list_progress_history(
    project_id: str,
    task_id: str | None = Query(None, description="Filter by task ID"),
    session: AsyncSession = Depends(get_async_session),
) -> Sequence[ProgressEventResponse]:
    """Retrieve chronological progress history for a project or specific task."""
    history_repo = HistoryRepository(session)
    events = await history_repo.get_progress_history(project_id, task_id=task_id)
    return [ProgressEventResponse.model_validate(e) for e in events]


@router.post(
    "/decisions",
    response_model=DecisionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_decision(
    project_id: str,
    req: DecisionCreateRequest,
    session: AsyncSession = Depends(get_async_session),
) -> DecisionResponse:
    """Record a replan or governance decision (Rule 4: Replanning requires approval)."""
    project_repo = ProjectRepository(session)
    project = await project_repo.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )

    history_repo = HistoryRepository(session)
    decision = await history_repo.record_decision(
        project_id=project_id,
        plan_id=req.plan_id,
        decision_type=req.decision_type,
        summary=req.summary,
        rationale=req.rationale,
        decided_by=req.decided_by,
    )
    await session.commit()
    return DecisionResponse.model_validate(decision)


@router.get("/decisions", response_model=list[DecisionResponse])
async def list_decisions(
    project_id: str,
    session: AsyncSession = Depends(get_async_session),
) -> Sequence[DecisionResponse]:
    """Retrieve all governance and replan decisions for a project."""
    history_repo = HistoryRepository(session)
    decisions = await history_repo.get_decisions(project_id)
    return [DecisionResponse.model_validate(d) for d in decisions]


@router.post(
    "/risks",
    response_model=RiskEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_risk(
    project_id: str,
    req: RiskEventCreateRequest,
    session: AsyncSession = Depends(get_async_session),
) -> RiskEventResponse:
    """Record a detected risk anomaly in the immutable risk register."""
    project_repo = ProjectRepository(session)
    project = await project_repo.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )

    history_repo = HistoryRepository(session)
    risk = await history_repo.record_risk_event(
        project_id=project_id,
        risk_type=req.risk_type,
        severity=req.severity,
        description=req.description,
        payload_json=req.payload_json,
    )
    await session.commit()
    return RiskEventResponse.model_validate(risk)


@router.get("/risks", response_model=list[RiskEventResponse])
async def list_risks(
    project_id: str,
    min_severity: str | None = Query(None, description="Filter by minimum severity"),
    session: AsyncSession = Depends(get_async_session),
) -> Sequence[RiskEventResponse]:
    """Retrieve all risk anomaly events recorded for a project."""
    history_repo = HistoryRepository(session)
    risks = await history_repo.get_risk_events(project_id, min_severity=min_severity)
    return [RiskEventResponse.model_validate(r) for r in risks]
