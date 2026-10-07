"""API endpoints for deterministic risk analysis and candidate replan propositions."""

import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.plans import _domain_plan_to_response
from backend.app.db.session import get_async_session
from backend.app.domain.clock import SystemClock
from backend.app.domain.risk.engine import DeterministicRiskEngine
from backend.app.domain.risk.replan_generator import ReplanCandidateGenerator
from backend.app.repositories.history_repository import HistoryRepository
from backend.app.repositories.plan_repository import PlanRepository
from backend.app.schemas.risk import (
    DetectedRiskSchema,
    ReplanCandidateResponse,
    RiskAnalysisResponse,
)

router = APIRouter(prefix="/projects/{project_id}", tags=["risks"])


@router.get("/risks/analyze", response_model=RiskAnalysisResponse)
async def analyze_project_risks(
    project_id: str,
    version: int | None = Query(None, description="Specific plan version; defaults to active"),
    session: AsyncSession = Depends(get_async_session),
) -> RiskAnalysisResponse:
    """
    Run deterministic risk rules, compute project health, and log events.

    Rule 1 & 5: Deterministic risk rules, append-only risk event recording.
    """
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

    risk_engine = DeterministicRiskEngine(SystemClock())
    eval_result = risk_engine.analyze_risks(plan)

    # Persist newly detected risks to append-only risk audit log
    history_repo = HistoryRepository(session)
    for risk in eval_result.risks:
        await history_repo.record_risk_event(
            project_id=project_id,
            risk_type=risk.risk_type.value,
            severity=risk.severity.value,
            description=risk.description,
            payload_json=json.dumps(risk.metrics),
        )
    await session.commit()

    return RiskAnalysisResponse(
        project_id=project_id,
        plan_version=plan.version,
        health_score=eval_result.health_score,
        is_at_risk=eval_result.is_at_risk,
        summary=eval_result.summary,
        risks=[
            DetectedRiskSchema(
                risk_type=r.risk_type,
                severity=r.severity,
                description=r.description,
                affected_task_ids=r.affected_task_ids,
                metrics=r.metrics,
            )
            for r in eval_result.risks
        ],
    )


@router.post("/replan/propose", response_model=ReplanCandidateResponse)
async def propose_replan_mitigation(
    project_id: str,
    session: AsyncSession = Depends(get_async_session),
) -> ReplanCandidateResponse:
    """
    Generate a deterministically simulated replan candidate to mitigate risks.

    Rule 3 & 4: Replans are simulated by deterministic scheduler; require human approval.
    Does NOT write new plan version to DB.
    """
    plan_repo = PlanRepository(session)
    active_plan = await plan_repo.get_active_plan(project_id)
    if not active_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active plan found for project '{project_id}'.",
        )

    generator = ReplanCandidateGenerator(SystemClock())
    candidate = generator.generate_mitigation_candidate(active_plan)

    return ReplanCandidateResponse(
        project_id=project_id,
        baseline_version=active_plan.version,
        proposed_version=candidate.candidate_plan.version,
        baseline_finish_date=candidate.baseline_finish_date,
        proposed_finish_date=candidate.candidate_finish_date,
        finish_date_delta_days=candidate.finish_date_delta_days,
        resolved_risks_count=candidate.resolved_risks_count,
        mitigation_notes=candidate.mitigation_notes,
        proposed_plan=_domain_plan_to_response(candidate.candidate_plan),
    )
