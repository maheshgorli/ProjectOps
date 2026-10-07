"""API endpoints for Projects and Members."""

from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_async_session
from backend.app.repositories.project_repository import ProjectRepository
from backend.app.schemas.project import (
    MemberCreateRequest,
    MemberResponse,
    ProjectCreateRequest,
    ProjectResponse,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    req: ProjectCreateRequest,
    session: AsyncSession = Depends(get_async_session),
) -> ProjectResponse:
    """Create a new project."""
    repo = ProjectRepository(session)
    project = await repo.create_project(name=req.name, description=req.description)
    response = ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        updated_at=project.updated_at,
        members=[],
    )
    await session.commit()
    return response


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    session: AsyncSession = Depends(get_async_session),
) -> Sequence[ProjectResponse]:
    """List all projects."""
    repo = ProjectRepository(session)
    projects = await repo.list_projects()
    return [
        ProjectResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            created_at=p.created_at,
            updated_at=p.updated_at,
            members=[MemberResponse.model_validate(m) for m in p.members],
        )
        for p in projects
    ]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
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
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        updated_at=project.updated_at,
        members=[MemberResponse.model_validate(m) for m in project.members],
    )


@router.post(
    "/{project_id}/members",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_project_member(
    project_id: str,
    req: MemberCreateRequest,
    session: AsyncSession = Depends(get_async_session),
) -> MemberResponse:
    """Add a team member to a project."""
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
