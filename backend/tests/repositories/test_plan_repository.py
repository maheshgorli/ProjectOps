"""Tests for PlanRepository and plan snapshot immutability guarantees."""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.clock import FrozenClock
from backend.app.domain.models import (
    Dependency,
    Member,
    ProjectPlan,
    Task,
    TaskStatus,
)
from backend.app.domain.scheduler import DeterministicScheduler
from backend.app.repositories.plan_repository import (
    PlanImmutableError,
    PlanRepository,
)
from backend.app.repositories.project_repository import ProjectRepository


@pytest.mark.asyncio
async def test_plan_repository_immutability_and_versioning(test_session: AsyncSession):
    project_repo = ProjectRepository(test_session)
    plan_repo = PlanRepository(test_session)

    # 1. Setup project and team members
    project = await project_repo.create_project(name="Project Falcon", description="Core System")
    member = await project_repo.add_member(
        project_id=project.id,
        name="Developer One",
        role="senior_eng",
        daily_capacity_hours=8.0,
    )

    project_id = str(project.id)
    member_id = str(member.id)

    members_dict = {
        member_id: Member(
            id=member_id,
            name=member.name,
            role=member.role,
            daily_capacity_hours=member.daily_capacity_hours,
        )
    }

    # 2. Save Plan Version 1
    tasks_v1 = {
        "T1": Task(
            id="T1",
            title="Design Architecture",
            status=TaskStatus.COMPLETED,
            estimated_hours=8.0,
            assigned_to_id=member_id,
        ),
        "T2": Task(
            id="T2",
            title="Implement Core",
            status=TaskStatus.IN_PROGRESS,
            estimated_hours=16.0,
            assigned_to_id=member_id,
        ),
    }
    deps_v1 = [Dependency(predecessor_id="T1", successor_id="T2")]
    plan_v1 = ProjectPlan(
        id="PLAN-V1",
        project_id=project_id,
        version=1,
        name="Baseline Plan",
        created_at=datetime(2026, 10, 1, 10, 0, tzinfo=UTC),
        tasks=tasks_v1,
        dependencies=deps_v1,
        members=members_dict,
    )

    await plan_repo.save_plan_snapshot(plan_v1, activate=True)
    await test_session.commit()

    # 3. Query Active Plan and Plan by Version
    active_plan = await plan_repo.get_active_plan(project_id)
    assert active_plan is not None
    assert active_plan.version == 1
    assert len(active_plan.tasks) == 2

    # 4. Enforce Immutability: Attempting to save v1 again MUST fail
    duplicate_v1 = ProjectPlan(
        id="PLAN-V1-MUTATED",
        project_id=project_id,
        version=1,  # Same version!
        name="Mutated Plan Attempt",
        created_at=datetime.now(UTC),
        tasks={},
    )
    with pytest.raises(PlanImmutableError, match="already exists and cannot be overwritten"):
        await plan_repo.save_plan_snapshot(duplicate_v1)
    await test_session.rollback()

    # 5. Save Plan Version 2 (Replan snapshot)
    tasks_v2 = {
        **tasks_v1,
        "T3": Task(
            id="T3",
            title="Add Security Audit",
            status=TaskStatus.TODO,
            estimated_hours=24.0,
            assigned_to_id=member_id,
        ),
    }
    deps_v2 = [*deps_v1, Dependency(predecessor_id="T2", successor_id="T3")]
    plan_v2 = ProjectPlan(
        id="PLAN-V2",
        project_id=project_id,
        version=2,
        name="Post-Review Replan",
        created_at=datetime(2026, 10, 5, 14, 0, tzinfo=UTC),
        tasks=tasks_v2,
        dependencies=deps_v2,
        members=members_dict,
    )

    await plan_repo.save_plan_snapshot(plan_v2, activate=True)
    await test_session.commit()

    # 6. Verify Active Plan is now Version 2, but Version 1 is strictly preserved
    active_now = await plan_repo.get_active_plan(project_id)
    assert active_now is not None
    assert active_now.version == 2
    assert len(active_now.tasks) == 3

    historical_v1 = await plan_repo.get_plan_by_version(project_id, 1)
    assert historical_v1 is not None
    assert historical_v1.version == 1
    assert len(historical_v1.tasks) == 2
    assert "T3" not in historical_v1.tasks  # Historical snapshot was NOT mutated!

    # 7. Check version listing
    versions = await plan_repo.list_plan_versions(project_id)
    assert versions == [1, 2]
    latest_ver = await plan_repo.get_latest_version_number(project_id)
    assert latest_ver == 2

    # 8. Deterministic CPM verification on fetched active plan
    clock = FrozenClock(date(2026, 10, 5))
    scheduler = DeterministicScheduler(clock)
    result = scheduler.schedule(active_now)
    assert result.critical_path == ["T1", "T2", "T3"]
    assert result.is_feasible is True
