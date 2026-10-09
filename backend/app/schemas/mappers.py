"""Mappers between pure domain models and Pydantic response schemas."""

from backend.app.domain.clock import SystemClock
from backend.app.domain.models import ProjectPlan
from backend.app.schemas.plan import (
    DependencySchema,
    PlanResponseSchema,
    TaskResponseSchema,
)


def domain_plan_to_response(plan: ProjectPlan) -> PlanResponseSchema:
    """Convert a pure domain ProjectPlan into a PlanResponseSchema."""
    clock = SystemClock()
    task_responses = [
        TaskResponseSchema(
            id=t.id,
            title=t.title,
            description=t.description,
            status=t.status,
            estimated_hours=t.estimated_hours,
            assigned_to_id=t.assigned_to_id,
            due_date=t.due_date,
            start_date=t.start_date,
            completed_at=t.completed_at,
            is_overdue=t.is_overdue(clock),
        )
        for t in plan.tasks.values()
    ]
    dep_responses = [
        DependencySchema(
            predecessor_id=d.predecessor_id,
            successor_id=d.successor_id,
            dep_type=d.dep_type,
            lag_days=d.lag_days,
        )
        for d in plan.dependencies
    ]
    return PlanResponseSchema(
        id=plan.id,
        project_id=plan.project_id,
        version=plan.version,
        name=plan.name,
        target_completion_date=plan.target_completion_date,
        created_at=plan.created_at,
        created_by=plan.created_by,
        tasks=task_responses,
        dependencies=dep_responses,
    )
