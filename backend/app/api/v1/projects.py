"""API endpoints for Projects and Members."""

from collections.abc import Sequence
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import (
    get_current_user,
    require_project_member,
    require_project_owner,
)
from backend.app.db.session import get_async_session
from backend.app.models.auth import ProjectMembershipORM, UserORM
from backend.app.models.project import ProjectORM
from backend.app.repositories.project_repository import ProjectRepository
from backend.app.schemas.project import (
    MemberCreateRequest,
    MemberResponse,
    ProjectCreateRequest,
    ProjectResponse,
)

router = APIRouter(prefix="/projects", tags=["projects"])


def _build_project_response(project: ProjectORM) -> ProjectResponse:
    """Format ProjectORM into ProjectResponse with active plan metadata."""
    state = inspect(project)
    active_plan = None
    if "plans" not in state.unloaded and project.plans:
        active_plan = next((p for p in project.plans if p.is_active), None)

    task_count = 0
    if active_plan:
        plan_state = inspect(active_plan)
        if "tasks" not in plan_state.unloaded and active_plan.tasks:
            task_count = len(active_plan.tasks)

    active_plan_version = active_plan.version if active_plan else None
    target_completion_date = (
        active_plan.target_completion_date if active_plan else None
    )

    members_list = []
    if "members" not in state.unloaded and project.members:
        members_list = [MemberResponse.model_validate(m) for m in project.members]

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        updated_at=project.updated_at,
        members=members_list,
        task_count=task_count,
        active_plan_version=active_plan_version,
        target_completion_date=target_completion_date,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    req: ProjectCreateRequest,
    current_user: UserORM = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ProjectResponse:
    """Create a new project and assign caller as owner in the same transaction."""
    repo = ProjectRepository(session)
    project = await repo.create_project(name=req.name, description=req.description)

    # Automatically grant creator owner membership
    membership = ProjectMembershipORM(
        id=str(uuid4()),
        project_id=project.id,
        user_id=current_user.id,
        role="owner",
    )
    session.add(membership)

    response = _build_project_response(project)
    await session.commit()
    return response


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    current_user: UserORM = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> Sequence[ProjectResponse]:
    """List only projects accessible to the authenticated caller."""
    repo = ProjectRepository(session)
    projects = await repo.list_user_projects(current_user.id)
    return [_build_project_response(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    _membership: ProjectMembershipORM = Depends(require_project_member),
    session: AsyncSession = Depends(get_async_session),
) -> ProjectResponse:
    """Get project details including members."""
    repo = ProjectRepository(session)
    project = await repo.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )
    return _build_project_response(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    _membership: ProjectMembershipORM = Depends(require_project_owner),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    """Delete a project (Owner only)."""
    repo = ProjectRepository(session)
    project = await repo.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )
    await session.delete(project)
    await session.commit()


@router.post(
    "/{project_id}/members",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_project_member(
    project_id: str,
    req: MemberCreateRequest,
    _membership: ProjectMembershipORM = Depends(require_project_owner),
    session: AsyncSession = Depends(get_async_session),
) -> MemberResponse:
    """Add a team member to a project (Owner only)."""
    repo = ProjectRepository(session)
    project = await repo.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )

    member = await repo.add_member(
        project_id=project_id,
        name=req.name,
        role=req.role,
        daily_capacity_hours=req.daily_capacity_hours,
    )
    await session.commit()
    return MemberResponse.model_validate(member)


@router.get("/{project_id}/members", response_model=list[MemberResponse])
async def list_project_members(
    project_id: str,
    _membership: ProjectMembershipORM = Depends(require_project_member),
    session: AsyncSession = Depends(get_async_session),
) -> Sequence[MemberResponse]:
    """List members assigned to a project."""
    repo = ProjectRepository(session)
    project = await repo.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )

    members = await repo.list_members(project_id)
    return [MemberResponse.model_validate(m) for m in members]
