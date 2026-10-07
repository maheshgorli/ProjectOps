"""Repository for Project and Member entities."""

from collections.abc import Sequence
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.project import MemberORM, ProjectORM


class ProjectRepository:
    """Provides persistence operations for Projects and their Members."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_project(
        self,
        name: str,
        description: str = "",
        project_id: str | None = None,
    ) -> ProjectORM:
        """Create a new project entity."""
        pid = project_id or str(uuid4())
        project = ProjectORM(
            id=pid,
            name=name,
            description=description,
        )
        project.members = []
        self.session.add(project)
        await self.session.flush()
        return project

    async def get_project(self, project_id: str) -> ProjectORM | None:
        """Fetch project by ID including members."""
        stmt = (
            select(ProjectORM)
            .where(ProjectORM.id == project_id)
            .options(selectinload(ProjectORM.members))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_projects(self) -> Sequence[ProjectORM]:
        """List all projects with members loaded."""
        stmt = (
            select(ProjectORM)
            .options(selectinload(ProjectORM.members))
            .order_by(ProjectORM.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def add_member(
        self,
        project_id: str,
        name: str,
        role: str = "engineer",
        daily_capacity_hours: float = 8.0,
        member_id: str | None = None,
    ) -> MemberORM:
        """Add a team member to a project."""
        member = MemberORM(
            id=member_id or str(uuid4()),
            project_id=project_id,
            name=name,
            role=role,
            daily_capacity_hours=daily_capacity_hours,
        )
        self.session.add(member)
        await self.session.flush()
        return member

    async def list_members(self, project_id: str) -> Sequence[MemberORM]:
        """List all members assigned to a project."""
        stmt = select(MemberORM).where(MemberORM.project_id == project_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()
