"""API endpoints for AI assistance: Goal Decomposition and Replan Explanations."""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.auth.deps import get_current_user, require_project_member
from backend.app.core.config import settings
from backend.app.llm.goal_decomposer import GoalDecomposer
from backend.app.llm.provider import get_llm_provider
from backend.app.llm.replan_explainer import ReplanExplainer
from backend.app.models.auth import ProjectMembershipORM, UserORM
from backend.app.schemas.ai import (
    AIInfoResponse,
    GoalDecompositionRequest,
    GoalDecompositionResponse,
    ReplanExplanationRequest,
    ReplanExplanationResponse,
)

router = APIRouter(tags=["ai"])


@router.get(
    "/ai/info",
    response_model=AIInfoResponse,
    status_code=status.HTTP_200_OK,
)
async def get_ai_info(
    _user: UserORM = Depends(get_current_user),
) -> AIInfoResponse:
    """Return active AI provider and model metadata (authenticated users)."""
    provider_name = (settings.llm_provider or "").lower().strip()
    is_mock = provider_name == "mock"
    if is_mock:
        active_model = "mock-provider"
    elif provider_name in ("grok", "xai"):
        active_model = settings.xai_model
    else:
        active_model = settings.anthropic_model

    return AIInfoResponse(
        provider=provider_name,
        model=active_model,
        is_mock=is_mock,
    )


@router.post(
    "/ai/decompose-goal",
    response_model=GoalDecompositionResponse,
    status_code=status.HTTP_200_OK,
)
async def decompose_goal_endpoint(
    req: GoalDecompositionRequest,
    _user: UserORM = Depends(get_current_user),
) -> GoalDecompositionResponse:
    """
    Decompose a high-level project goal into structured tasks and dependencies.

    Rule 2: Validated via Pydantic v2 and TaskGraph. Never writes to DB directly.
    Requires authentication to protect API credits.
    """
    try:
        provider = get_llm_provider()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    decomposer = GoalDecomposer(provider)

    try:
        return await decomposer.decompose_goal(goal=req.goal, context=req.context)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except TimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.post(
    "/projects/{project_id}/ai/decompose-goal",
    response_model=GoalDecompositionResponse,
    status_code=status.HTTP_200_OK,
)
async def decompose_goal_for_project_endpoint(
    project_id: str,
    req: GoalDecompositionRequest,
    _membership: ProjectMembershipORM = Depends(require_project_member),
) -> GoalDecompositionResponse:
    """Project-scoped route alias for goal decomposition (requires membership)."""
    return await decompose_goal_endpoint(req, _membership.user)


@router.post(
    "/projects/{project_id}/replan/explain",
    response_model=ReplanExplanationResponse,
    status_code=status.HTTP_200_OK,
)
async def explain_replan_endpoint(
    project_id: str,
    req: ReplanExplanationRequest,
    _membership: ProjectMembershipORM = Depends(require_project_member),
) -> ReplanExplanationResponse:
    """
    Generate an executive explanation grounded in deterministic replan metrics.

    Rule 3: The LLM explains computed numbers; it never invents them.
    Requires project membership.
    """
    try:
        provider = get_llm_provider()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    explainer = ReplanExplainer(provider)

    try:
        explanation_text = await explainer.explain_replan(
            baseline_version=req.baseline_version,
            proposed_version=req.proposed_version,
            baseline_finish_date=req.baseline_finish_date,
            proposed_finish_date=req.proposed_finish_date,
            finish_date_delta_days=req.finish_date_delta_days,
            mitigation_notes=req.mitigation_notes,
        )
    except TimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return ReplanExplanationResponse(
        project_id=project_id,
        explanation=explanation_text,
    )
