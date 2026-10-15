from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import get_current_user, require_project_member
from backend.app.core.config import settings
from backend.app.db.session import get_async_session
from backend.app.domain.models import Dependency, ProjectPlan, Task, TaskStatus
from backend.app.llm.goal_decomposer import GoalDecomposer
from backend.app.llm.provider import get_llm_provider
from backend.app.llm.replan_explainer import ReplanExplainer
from backend.app.models.auth import ProjectMembershipORM, UserORM
from backend.app.models.project import MemberORM
from backend.app.repositories.history_repository import HistoryRepository
from backend.app.repositories.plan_repository import PlanRepository
from backend.app.repositories.project_repository import ProjectRepository
from backend.app.schemas.ai import (
    AIInfoResponse,
    GeneratePlanRequest,
    GeneratePlanResponse,
    GoalDecompositionRequest,
    GoalDecompositionResponse,
    ReplanExplanationRequest,
    ReplanExplanationResponse,
)
from backend.app.services.document_parser import (
    DocumentParser,
    DocumentParsingError,
    ExtractedDocument,
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
    elif provider_name == "groq":
        active_model = settings.groq_model
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


async def _generate_plan_internal(
    project_id: str,
    requirements: str,
    github_url: str,
    save_as_draft: bool,
    extracted_docs: list[ExtractedDocument],
    user_id: str,
    session: AsyncSession,
) -> GeneratePlanResponse:
    project_repo = ProjectRepository(session)
    project = await project_repo.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )

    # 1. Fetch available members / roles
    members_stmt = select(MemberORM).where(MemberORM.project_id == project_id)
    members_res = await session.execute(members_stmt)
    members = list(members_res.scalars().all())
    available_roles = [m.role for m in members if m.role] or [
        "Project Manager",
        "Frontend Developer",
        "Backend Developer",
        "Full Stack Developer",
        "QA / Tester",
        "DevOps Engineer",
    ]

    # 2. Build goal and context
    goal_text = requirements.strip() if requirements.strip() else f"Deliver {project.name}"

    context_parts = [
        f"Project Name: {project.name}",
        f"Project Description: {project.description or 'No description provided'}",
        f"Available Roles: {', '.join(set(available_roles))}",
    ]
    if github_url.strip():
        context_parts.append(f"Repository URL: {github_url.strip()}")

    parser = DocumentParser()
    if extracted_docs:
        docs_formatted = parser.format_for_prompt(extracted_docs)
        context_parts.append(f"Attached Specifications:\n{docs_formatted}")

    context_str = "\n\n".join(context_parts)

    # 3. Call LLM provider
    try:
        provider = get_llm_provider()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    decomposer = GoalDecomposer(provider)
    try:
        decomp = await decomposer.decompose_goal(goal=goal_text, context=context_str)
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

    # 4. Extract metrics
    total_hours = sum(t.estimated_hours for t in decomp.tasks)
    duration_days = max(1, round(total_hours / 8.0))
    milestones = list(dict.fromkeys(t.milestone for t in decomp.tasks if t.milestone))
    if not milestones:
        milestones = [
            "Planning",
            "Foundation",
            "Development",
            "Integration",
            "Testing",
            "Release",
        ]

    plan_id = None
    version_num = None

    # 5. Persist as DRAFT snapshot if requested
    if save_as_draft:
        plan_repo = PlanRepository(session)
        latest_version = await plan_repo.get_latest_version_number(project_id)
        version_num = latest_version + 1
        plan_id = str(uuid4())

        domain_tasks = {
            t.id: Task(
                id=t.id,
                title=t.title,
                description=t.description,
                status=TaskStatus.TODO,
                estimated_hours=t.estimated_hours,
            )
            for t in decomp.tasks
        }
        domain_deps = [
            Dependency(
                predecessor_id=d.predecessor_id,
                successor_id=d.successor_id,
                dep_type=d.dep_type,
                lag_days=d.lag_days,
            )
            for d in decomp.dependencies
        ]
        domain_plan = ProjectPlan(
            id=plan_id,
            project_id=project_id,
            version=version_num,
            name=f"{project.name} - AI Execution Plan v{version_num}",
            created_at=datetime.now(UTC),
            tasks=domain_tasks,
            dependencies=domain_deps,
            created_by=user_id,
        )
        await plan_repo.save_plan_snapshot(domain_plan, activate=False)

        history_repo = HistoryRepository(session)
        await history_repo.record_progress(
            project_id=project_id,
            task_id="AI_PLAN_GENERATION",
            previous_status="NONE",
            new_status="DRAFT",
            evidence_notes=(
                f"Generated draft execution plan v{version_num} ({len(decomp.tasks)} tasks, "
                f"{total_hours:.1f}h) from requirements and {len(extracted_docs)} documents."
            ),
            recorded_by=user_id,
        )
        await session.commit()

    return GeneratePlanResponse(
        project_id=project_id,
        plan_id=plan_id,
        version=version_num,
        name=project.name,
        goal_summary=goal_text,
        tasks=decomp.tasks,
        dependencies=decomp.dependencies,
        estimated_total_hours=total_hours,
        duration_days=duration_days,
        milestones=milestones,
        documents_processed=[d.filename for d in extracted_docs],
        is_valid_dag=True,
        status="DRAFT",
    )


@router.post(
    "/projects/{project_id}/ai/generate-plan",
    response_model=GeneratePlanResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_plan_for_project_endpoint(
    project_id: str,
    requirements: str = Form(""),
    github_url: str = Form(""),
    save_as_draft: bool = Form(True),
    files: list[UploadFile] = File(default_factory=list),
    _membership: ProjectMembershipORM = Depends(require_project_member),
    session: AsyncSession = Depends(get_async_session),
) -> GeneratePlanResponse:
    """Generate structured execution plan from requirements and uploaded files (multipart)."""
    parser = DocumentParser()
    extracted_docs: list[ExtractedDocument] = []

    for file in files:
        if not file.filename:
            continue
        try:
            content_bytes = await file.read()
            doc = parser.parse_document(file.filename, content_bytes)
            extracted_docs.append(doc)
        except DocumentParsingError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(exc),
            ) from exc

    return await _generate_plan_internal(
        project_id=project_id,
        requirements=requirements,
        github_url=github_url,
        save_as_draft=save_as_draft,
        extracted_docs=extracted_docs,
        user_id=_membership.user_id,
        session=session,
    )


@router.post(
    "/projects/{project_id}/ai/generate-plan-json",
    response_model=GeneratePlanResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_plan_json_for_project_endpoint(
    project_id: str,
    req: GeneratePlanRequest,
    _membership: ProjectMembershipORM = Depends(require_project_member),
    session: AsyncSession = Depends(get_async_session),
) -> GeneratePlanResponse:
    """Generate structured execution plan from requirements and document objects (JSON)."""
    parser = DocumentParser()
    extracted_docs: list[ExtractedDocument] = []

    for item in req.documents:
        try:
            raw_bytes = item.content.encode("utf-8")
            doc = parser.parse_document(item.filename, raw_bytes)
            extracted_docs.append(doc)
        except DocumentParsingError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(exc),
            ) from exc

    return await _generate_plan_internal(
        project_id=project_id,
        requirements=req.requirements,
        github_url=req.github_url,
        save_as_draft=req.save_as_draft,
        extracted_docs=extracted_docs,
        user_id=_membership.user_id,
        session=session,
    )
