"""Repository for immutable versioned plan snapshots."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.domain.models import ProjectPlan
from backend.app.models.plan import ProjectPlanORM
from backend.app.models.project import MemberORM
from backend.app.repositories.mappers import (
    domain_to_orm_plan,
    orm_to_domain_member,
    orm_to_domain_plan,
)


class PlanImmutableError(Exception):
    """Raised when an attempt is made to overwrite an existing immutable plan snapshot."""

    pass


class PlanRepository:
    """Provides persistence operations for immutable versioned plan snapshots."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_latest_version_number(self, project_id: str) -> int:
        """Return the highest version number for the given project, or 0 if none exist."""
        stmt = (
            select(ProjectPlanORM.version)
            .where(ProjectPlanORM.project_id == project_id)
            .order_by(ProjectPlanORM.version.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        val = result.scalar_one_or_none()
        return val if val is not None else 0

    async def list_plan_versions(self, project_id: str) -> list[int]:
        """Return all available version numbers for a project in ascending order."""
        stmt = (
            select(ProjectPlanORM.version)
            .where(ProjectPlanORM.project_id == project_id)
            .order_by(ProjectPlanORM.version.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_plan_by_version(self, project_id: str, version: int) -> ProjectPlan | None:
        """Fetch a specific historical plan snapshot by its version number."""
        stmt = (
            select(ProjectPlanORM)
            .where(
                ProjectPlanORM.project_id == project_id,
                ProjectPlanORM.version == version,
            )
            .options(
                selectinload(ProjectPlanORM.tasks),
                selectinload(ProjectPlanORM.dependencies),
            )
        )
        result = await self.session.execute(stmt)
        orm_plan = result.scalar_one_or_none()
        if not orm_plan:
            return None

        # Fetch project members
        members_stmt = select(MemberORM).where(MemberORM.project_id == project_id)
        members_result = await self.session.execute(members_stmt)
        members = {m.id: orm_to_domain_member(m) for m in members_result.scalars().all()}

        return orm_to_domain_plan(orm_plan, members=members)

    async def get_active_plan(self, project_id: str) -> ProjectPlan | None:
        """Fetch the currently active plan snapshot for a project."""
        stmt = (
            select(ProjectPlanORM)
            .where(
                ProjectPlanORM.project_id == project_id,
                ProjectPlanORM.is_active.is_(True),
            )
            .order_by(ProjectPlanORM.version.desc())
            .limit(1)
            .options(
                selectinload(ProjectPlanORM.tasks),
                selectinload(ProjectPlanORM.dependencies),
            )
        )
        result = await self.session.execute(stmt)
        orm_plan = result.scalar_one_or_none()
        if not orm_plan:
            return None

        members_stmt = select(MemberORM).where(MemberORM.project_id == project_id)
        members_result = await self.session.execute(members_stmt)
        members = {m.id: orm_to_domain_member(m) for m in members_result.scalars().all()}

        return orm_to_domain_plan(orm_plan, members=members)

    async def save_plan_snapshot(
        self,
        plan: ProjectPlan,
        activate: bool = True,
    ) -> ProjectPlan:
        """
        Save a new immutable plan snapshot.

        Enforces Rule 5: If a snapshot for this version already exists, raises PlanImmutableError.
        If `activate` is True, updates preceding plans to is_active=False.
        """
        # 1. Enforce immutability: check if (project_id, version) exists
        check_stmt = select(ProjectPlanORM.id).where(
            ProjectPlanORM.project_id == plan.project_id,
            ProjectPlanORM.version == plan.version,
        )
        check_result = await self.session.execute(check_stmt)
        if check_result.scalar_one_or_none() is not None:
            raise PlanImmutableError(
                f"Plan version {plan.version} for project '{plan.project_id}' already exists "
                "and cannot be overwritten."
            )

        # 2. If activating, deactivate other plans
        if activate:
            deactivate_stmt = (
                update(ProjectPlanORM)
                .where(
                    ProjectPlanORM.project_id == plan.project_id,
                    ProjectPlanORM.is_active.is_(True),
                )
                .values(is_active=False)
            )
            await self.session.execute(deactivate_stmt)

        # 3. Insert new plan snapshot
        orm_plan = domain_to_orm_plan(plan, is_active=activate)
        self.session.add(orm_plan)
        await self.session.flush()

        return plan
