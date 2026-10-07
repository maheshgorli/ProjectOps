"""Seed realistic demo project and plan into ProjectOps database."""

import asyncio
import os
import sys
from datetime import UTC, datetime, timedelta
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.db.session import async_session_maker, create_all_tables
from backend.app.domain.clock import SystemClock
from backend.app.domain.models import (
    Dependency,
    DependencyType,
    Member,
    ProjectPlan,
    Task,
    TaskStatus,
)
from backend.app.models.project import MemberORM, ProjectORM
from backend.app.repositories.history_repository import HistoryRepository
from backend.app.repositories.plan_repository import PlanRepository


async def seed_data():
    await create_all_tables()
    async with async_session_maker() as session:
        clock = SystemClock()
        plan_repo = PlanRepository(session)
        history_repo = HistoryRepository(session)

        # 1. Create Demo Project
        project = ProjectORM(
            name="Project Phoenix: Cloud Modernization",
            description=(
                "Autonomous cloud migration, microservices architecture, and "
                "API gateway deployment."
            ),
        )
        session.add(project)
        await session.flush()

        # 2. Add Team Members
        alice = MemberORM(
            project_id=project.id,
            name="Alice Walker",
            role="Lead Architect",
            daily_capacity_hours=8.0,
        )
        bob = MemberORM(
            project_id=project.id,
            name="Bob Smith",
            role="Backend Engineer",
            daily_capacity_hours=8.0,
        )
        carol = MemberORM(
            project_id=project.id,
            name="Carol Danvers",
            role="DevOps & SRE",
            daily_capacity_hours=8.0,
        )
        dave = MemberORM(
            project_id=project.id,
            name="Dave Miller",
            role="Frontend Specialist",
            daily_capacity_hours=8.0,
        )
        session.add_all([alice, bob, carol, dave])
        await session.flush()

        # 3. Create Baseline Plan (Version 1)
        today = clock.today()
        tasks = {
            "TASK-01": Task(
                id="TASK-01",
                title="Cloud Architecture & Spec",
                description="Design VPC topology, security boundaries, and service mesh spec.",
                status=TaskStatus.COMPLETED,
                estimated_hours=16.0,
                assigned_to_id=alice.id,
                start_date=today - timedelta(days=5),
                due_date=today - timedelta(days=3),
                completed_at=datetime.now(UTC) - timedelta(days=3),
            ),
            "TASK-02": Task(
                id="TASK-02",
                title="Infrastructure as Code (Terraform)",
                description="Provision EKS cluster, IAM roles, RDS instances, and VPC peering.",
                status=TaskStatus.IN_PROGRESS,
                estimated_hours=32.0,
                assigned_to_id=carol.id,
                start_date=today - timedelta(days=2),
                due_date=today + timedelta(days=4),
            ),
            "TASK-03": Task(
                id="TASK-03",
                title="Auth & Identity Microservice",
                description="Implement JWT issuance, OAuth2 providers, and RBAC middleware.",
                status=TaskStatus.IN_PROGRESS,
                estimated_hours=24.0,
                assigned_to_id=bob.id,
                start_date=today - timedelta(days=1),
                due_date=today + timedelta(days=3),
            ),
            "TASK-04": Task(
                id="TASK-04",
                title="API Gateway & Rate Limiter",
                description=(
                    "Deploy Kong API Gateway, configure Redis rate limiting and JWT plugins."
                ),
                status=TaskStatus.TODO,
                estimated_hours=24.0,
                assigned_to_id=bob.id,
                start_date=today + timedelta(days=3),
                due_date=today + timedelta(days=7),
            ),
            "TASK-05": Task(
                id="TASK-05",
                title="Management Dashboard UI",
                description="Build React TypeScript admin dashboard with telemetry widgets.",
                status=TaskStatus.TODO,
                estimated_hours=40.0,
                assigned_to_id=dave.id,
                start_date=today + timedelta(days=4),
                due_date=today + timedelta(days=10),
            ),
            "TASK-06": Task(
                id="TASK-06",
                title="Integration Testing & CI/CD",
                description=(
                    "End-to-end integration test suite and automated GitHub Actions pipeline."
                ),
                status=TaskStatus.TODO,
                estimated_hours=24.0,
                assigned_to_id=carol.id,
                start_date=today + timedelta(days=8),
                due_date=today + timedelta(days=12),
            ),
            "TASK-07": Task(
                id="TASK-07",
                title="Production Cutover & Verification",
                description=(
                    "Blue/green DNS switch, canary release validation, and rollback checklist."
                ),
                status=TaskStatus.TODO,
                estimated_hours=16.0,
                assigned_to_id=alice.id,
                start_date=today + timedelta(days=13),
                due_date=today + timedelta(days=15),
            ),
        }

        dependencies = [
            Dependency(
                predecessor_id="TASK-01",
                successor_id="TASK-02",
                dep_type=DependencyType.FINISH_TO_START,
            ),
            Dependency(
                predecessor_id="TASK-01",
                successor_id="TASK-03",
                dep_type=DependencyType.FINISH_TO_START,
            ),
            Dependency(
                predecessor_id="TASK-02",
                successor_id="TASK-04",
                dep_type=DependencyType.FINISH_TO_START,
            ),
            Dependency(
                predecessor_id="TASK-03",
                successor_id="TASK-04",
                dep_type=DependencyType.FINISH_TO_START,
            ),
            Dependency(
                predecessor_id="TASK-04",
                successor_id="TASK-05",
                dep_type=DependencyType.FINISH_TO_START,
            ),
            Dependency(
                predecessor_id="TASK-04",
                successor_id="TASK-06",
                dep_type=DependencyType.FINISH_TO_START,
            ),
            Dependency(
                predecessor_id="TASK-05",
                successor_id="TASK-07",
                dep_type=DependencyType.FINISH_TO_START,
            ),
            Dependency(
                predecessor_id="TASK-06",
                successor_id="TASK-07",
                dep_type=DependencyType.FINISH_TO_START,
            ),
        ]

        members = {
            alice.id: Member(
                id=alice.id,
                name=alice.name,
                role=alice.role,
                daily_capacity_hours=alice.daily_capacity_hours,
            ),
            bob.id: Member(
                id=bob.id,
                name=bob.name,
                role=bob.role,
                daily_capacity_hours=bob.daily_capacity_hours,
            ),
            carol.id: Member(
                id=carol.id,
                name=carol.name,
                role=carol.role,
                daily_capacity_hours=carol.daily_capacity_hours,
            ),
            dave.id: Member(
                id=dave.id,
                name=dave.name,
                role=dave.role,
                daily_capacity_hours=dave.daily_capacity_hours,
            ),
        }

        plan = ProjectPlan(
            id=str(uuid4()),
            project_id=project.id,
            version=1,
            name="Baseline Execution Plan v1",
            tasks=tasks,
            dependencies=dependencies,
            members=members,
            target_completion_date=today + timedelta(days=20),
            created_at=datetime.now(UTC),
            created_by="system_bootstrap",
        )

        saved_plan = await plan_repo.save_plan_snapshot(plan, activate=True)

        # 4. Add Initial Audit Records
        await history_repo.record_progress(
            project_id=project.id,
            task_id="TASK-01",
            previous_status="IN_PROGRESS",
            new_status="COMPLETED",
            evidence_notes="Architecture design document approved by team lead.",
            recorded_by="Alice Walker",
        )
        await history_repo.record_decision(
            project_id=project.id,
            plan_id=saved_plan.id,
            decision_type="BASELINE_APPROVED",
            summary="Approved Baseline Plan v1",
            rationale="Deterministic scheduling confirms feasible path within target date.",
            decided_by="Alice Walker (Lead Architect)",
        )
        await history_repo.record_agent_run(
            project_id=project.id,
            loop_stage="PLAN",
            status="SUCCESS",
            summary="Plan v1 verified: 7 tasks, 8 precedence edges, 0 cycles detected.",
            triggered_by="bootstrap",
        )

        await session.commit()
        print(f"Successfully seeded demo project: '{project.name}' (ID: {project.id})")


if __name__ == "__main__":
    asyncio.run(seed_data())
