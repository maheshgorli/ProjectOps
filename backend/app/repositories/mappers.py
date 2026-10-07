"""Bi-directional mappers between pure domain models and SQLAlchemy ORM entities."""

from uuid import uuid4

from backend.app.domain.models import (
    Dependency,
    DependencyType,
    Member,
    ProjectPlan,
    Task,
    TaskStatus,
)
from backend.app.models.plan import (
    PlanDependencyORM,
    PlanTaskORM,
    ProjectPlanORM,
)
from backend.app.models.project import (
    MemberORM,
)


def domain_to_orm_plan(plan: ProjectPlan, is_active: bool = True) -> ProjectPlanORM:
    """Convert a pure domain ProjectPlan into a ProjectPlanORM graph."""
    plan_id = plan.id or str(uuid4())
    orm_plan = ProjectPlanORM(
        id=plan_id,
        project_id=plan.project_id,
        version=plan.version,
        name=plan.name,
        target_completion_date=plan.target_completion_date,
        created_at=plan.created_at,
        created_by=plan.created_by,
        is_active=is_active,
    )

    for task in plan.tasks.values():
        orm_task = PlanTaskORM(
            id=str(uuid4()),
            plan_id=plan_id,
            task_id=task.id,
            title=task.title,
            description=task.description,
            status=task.status.value,
            estimated_hours=task.estimated_hours,
            assigned_to_id=task.assigned_to_id,
            due_date=task.due_date,
            start_date=task.start_date,
            completed_at=task.completed_at,
        )
        orm_plan.tasks.append(orm_task)

    for dep in plan.dependencies:
        orm_dep = PlanDependencyORM(
            id=str(uuid4()),
            plan_id=plan_id,
            predecessor_id=dep.predecessor_id,
            successor_id=dep.successor_id,
            dep_type=dep.dep_type.value,
            lag_days=dep.lag_days,
        )
        orm_plan.dependencies.append(orm_dep)

    return orm_plan


def orm_to_domain_plan(
    orm_plan: ProjectPlanORM,
    members: dict[str, Member] | None = None,
) -> ProjectPlan:
    """Convert a ProjectPlanORM entity into an immutable pure domain ProjectPlan."""
    domain_tasks: dict[str, Task] = {}
    for t in orm_plan.tasks:
        domain_tasks[t.task_id] = Task(
            id=t.task_id,
            title=t.title,
            description=t.description,
            status=TaskStatus(t.status),
            estimated_hours=t.estimated_hours,
            assigned_to_id=t.assigned_to_id,
            due_date=t.due_date,
            start_date=t.start_date,
            completed_at=t.completed_at,
        )

    domain_dependencies: list[Dependency] = []
    for d in orm_plan.dependencies:
        domain_dependencies.append(
            Dependency(
                predecessor_id=d.predecessor_id,
                successor_id=d.successor_id,
                dep_type=DependencyType(d.dep_type),
                lag_days=d.lag_days,
            )
        )

    return ProjectPlan(
        id=orm_plan.id,
        project_id=orm_plan.project_id,
        version=orm_plan.version,
        name=orm_plan.name,
        created_at=orm_plan.created_at,
        tasks=domain_tasks,
        dependencies=domain_dependencies,
        members=members or {},
        target_completion_date=orm_plan.target_completion_date,
        created_by=orm_plan.created_by,
    )


def orm_to_domain_member(orm_member: MemberORM) -> Member:
    """Convert MemberORM to domain Member entity."""
    return Member(
        id=orm_member.id,
        name=orm_member.name,
        role=orm_member.role,
        daily_capacity_hours=orm_member.daily_capacity_hours,
    )


def domain_to_orm_member(member: Member, project_id: str) -> MemberORM:
    """Convert domain Member entity to MemberORM."""
    return MemberORM(
        id=member.id,
        project_id=project_id,
        name=member.name,
        role=member.role,
        daily_capacity_hours=member.daily_capacity_hours,
    )
