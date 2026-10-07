"""Tests for bi-directional domain to ORM mappers."""

from datetime import UTC, date, datetime

from backend.app.domain.clock import FrozenClock
from backend.app.domain.models import (
    Dependency,
    DependencyType,
    Member,
    ProjectPlan,
    Task,
    TaskStatus,
)
from backend.app.domain.scheduler import DeterministicScheduler
from backend.app.repositories.mappers import (
    domain_to_orm_member,
    domain_to_orm_plan,
    orm_to_domain_member,
    orm_to_domain_plan,
)


def test_member_mapper_roundtrip():
    original = Member(id="M1", name="Alice Smith", role="tech_lead", daily_capacity_hours=7.5)
    orm_member = domain_to_orm_member(original, project_id="PROJ-1")
    assert orm_member.id == "M1"
    assert orm_member.project_id == "PROJ-1"
    assert orm_member.name == "Alice Smith"
    assert orm_member.role == "tech_lead"
    assert orm_member.daily_capacity_hours == 7.5

    reconstructed = orm_to_domain_member(orm_member)
    assert reconstructed == original


def test_plan_mapper_roundtrip_fidelity():
    clock = FrozenClock(date(2026, 10, 5))
    scheduler = DeterministicScheduler(clock)

    # Construct complete domain plan
    members = {
        "M1": Member(id="M1", name="Bob", daily_capacity_hours=8.0),
    }
    tasks = {
        "T1": Task(
            id="T1",
            title="Design System",
            description="Setup typography and colors",
            status=TaskStatus.IN_PROGRESS,
            estimated_hours=16.0,
            assigned_to_id="M1",
            start_date=date(2026, 10, 5),
            due_date=date(2026, 10, 8),
        ),
        "T2": Task(
            id="T2",
            title="Implement Components",
            description="Build buttons and modals",
            status=TaskStatus.TODO,
            estimated_hours=24.0,
            assigned_to_id="M1",
            due_date=date(2026, 10, 15),
        ),
    }
    dependencies = [
        Dependency(
            predecessor_id="T1",
            successor_id="T2",
            dep_type=DependencyType.FINISH_TO_START,
            lag_days=1,
        )
    ]
    original_plan = ProjectPlan(
        id="PLAN-V1",
        project_id="PROJ-ALPHA",
        version=1,
        name="Phase 1 Plan",
        created_at=datetime.now(UTC),
        tasks=tasks,
        dependencies=dependencies,
        members=members,
        target_completion_date=date(2026, 10, 20),
        created_by="lead_agent",
    )

    # 1. Map domain -> ORM
    orm_plan = domain_to_orm_plan(original_plan, is_active=True)
    assert orm_plan.id == "PLAN-V1"
    assert orm_plan.project_id == "PROJ-ALPHA"
    assert orm_plan.version == 1
    assert orm_plan.is_active is True
    assert len(orm_plan.tasks) == 2
    assert len(orm_plan.dependencies) == 1

    # 2. Map ORM -> domain
    reconstructed_plan = orm_to_domain_plan(orm_plan, members=members)

    assert reconstructed_plan.id == original_plan.id
    assert reconstructed_plan.project_id == original_plan.project_id
    assert reconstructed_plan.version == original_plan.version
    assert reconstructed_plan.name == original_plan.name
    assert reconstructed_plan.target_completion_date == original_plan.target_completion_date
    assert reconstructed_plan.created_by == original_plan.created_by
    assert len(reconstructed_plan.tasks) == 2
    assert len(reconstructed_plan.dependencies) == 1

    # 3. Verify scheduling output on reconstructed plan is identical to original plan
    res_orig = scheduler.schedule(original_plan)
    res_recon = scheduler.schedule(reconstructed_plan)

    assert res_orig.project_start_date == res_recon.project_start_date
    assert res_orig.project_finish_date == res_recon.project_finish_date
    assert res_orig.critical_path == res_recon.critical_path
    assert res_orig.is_feasible == res_recon.is_feasible
    for t_id in original_plan.tasks:
        assert res_orig.scheduled_tasks[t_id] == res_recon.scheduled_tasks[t_id]
