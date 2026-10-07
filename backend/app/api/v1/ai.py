"""API endpoints for AI assistance: Goal Decomposition and Replan Explanations."""

from fastapi import APIRouter, HTTPException, status

from backend.app.llm.goal_decomposer import GoalDecomposer
from backend.app.llm.provider import get_llm_provider
from backend.app.llm.replan_explainer import ReplanExplainer
from backend.app.schemas.ai import (
    GoalDecompositionRequest,
    GoalDecompositionResponse,
    ReplanExplanationRequest,
    ReplanExplanationResponse,
)

router = APIRouter(tags=["ai"])


@router.post(
    "/ai/decompose-goal",
    response_model=GoalDecompositionResponse,
    status_code=status.HTTP_200_OK,
)
async def decompose_goal_endpoint(
    req: GoalDecompositionRequest,
) -> GoalDecompositionResponse:
    """
    Decompose a high-level project goal into structured tasks and dependencies.

    Rule 2: Validated via Pydantic v2 and TaskGraph. Never writes to DB directly.
    """
    provider = get_llm_provider()
    decomposer = GoalDecomposer(provider)

    try:
        return await decomposer.decompose_goal(goal=req.goal, context=req.context)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


@router.post(
    "/projects/{project_id}/replan/explain",
    response_model=ReplanExplanationResponse,
    status_code=status.HTTP_200_OK,
)
async def explain_replan_endpoint(
    project_id: str,
    req: ReplanExplanationRequest,
) -> ReplanExplanationResponse:
    """
    Generate an executive explanation grounded in deterministic replan metrics.

    Rule 3: The LLM explains computed numbers; it never invents them.
    """
    provider = get_llm_provider()
    explainer = ReplanExplainer(provider)

    explanation_text = await explainer.explain_replan(
        baseline_version=req.baseline_version,
        proposed_version=req.proposed_version,
        baseline_finish_date=req.baseline_finish_date,
        proposed_finish_date=req.proposed_finish_date,
        finish_date_delta_days=req.finish_date_delta_days,
        mitigation_notes=req.mitigation_notes,
    )

    return ReplanExplanationResponse(
        project_id=project_id,
        explanation=explanation_text,
    )
