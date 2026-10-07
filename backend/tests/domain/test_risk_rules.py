"""Unit and architectural tests for deterministic risk evaluation rules and engine."""

import ast
from datetime import UTC, date, datetime
from pathlib import Path

from backend.app.domain.clock import FrozenClock
from backend.app.domain.graph import TaskGraph
from backend.app.domain.models import (
    Dependency,
    Member,
    ProjectPlan,
    Task,
    TaskStatus,
)
from backend.app.domain.risk.engine import DeterministicRiskEngine
from backend.app.domain.risk.models import RiskSeverity, RiskType
from backend.app.domain.risk.rules import (
    evaluate_blocked_cascades,
    evaluate_capacity_overloads,
    evaluate_critical_path_delays,
    evaluate_deadline_breach,
)
from backend.app.domain.scheduler import DeterministicScheduler


def test_evaluate_critical_path_delays():
    clock = FrozenClock(date(2026, 10, 7))
    tasks = {
        "CP1": Task(
            id="CP1",
            title="Overdue Critical Task",
            status=TaskStatus.TODO,
            due_date=date(2026, 10, 5),  # 2 days overdue
            estimated_hours=8.0,
        ),
        "CP2": Task(
            id="CP2",
            title="Blocked Critical Task",
            status=TaskStatus.BLOCKED,
            due_date=date(2026, 10, 9),
            estimated_hours=8.0,
        ),
        "NORM": Task(
            id="NORM",
            title="Normal Non-Critical Task",
            status=TaskStatus.TODO,
            due_date=date(2026, 10, 9),
            estimated_hours=8.0,
        ),
    }
    dependencies = [Dependency(predecessor_id="CP1", successor_id="CP2")]
    plan = ProjectPlan(
        id="P1",
        project_id="PROJ",
        version=1,
        name="Risk Plan",
        created_at=datetime.now(UTC),
        tasks=tasks,
        dependencies=dependencies,
    )

    scheduler = DeterministicScheduler(clock)
    schedule = scheduler.schedule(plan, start_date=date(2026, 10, 5))

    risks = evaluate_critical_path_delays(plan, schedule, clock)
    assert len(risks) == 2
    types = [r.risk_type for r in risks]
    assert types == [RiskType.CRITICAL_PATH_DELAY, RiskType.CRITICAL_PATH_DELAY]
    severities = [r.severity for r in risks]
    assert RiskSeverity.CRITICAL in severities  # for overdue
    assert RiskSeverity.HIGH in severities  # for blocked


def test_evaluate_capacity_overloads():
    clock = FrozenClock(date(2026, 10, 5))
    scheduler = DeterministicScheduler(clock)

    member = Member(id="M1", name="Overworked Dev", daily_capacity_hours=8.0)
    tasks = {
        "T1": Task(id="T1", title="Task 1", estimated_hours=8.0, assigned_to_id="M1"),
        "T2": Task(id="T2", title="Task 2", estimated_hours=8.0, assigned_to_id="M1"),
    }
    plan = ProjectPlan(
        id="P2",
        project_id="PROJ",
        version=1,
        name="Capacity Risk Plan",
        created_at=datetime.now(UTC),
        tasks=tasks,
        dependencies=[],  # Run concurrently on day 1
        members={"M1": member},
    )

    schedule = scheduler.schedule(plan, start_date=date(2026, 10, 5))
    risks = evaluate_capacity_overloads(schedule)
    assert len(risks) == 1
    assert risks[0].risk_type == RiskType.CAPACITY_OVERLOAD
    assert risks[0].metrics["member_id"] == "M1"
    assert risks[0].metrics["peak_daily_hours"] == 16.0


def test_evaluate_blocked_cascades():
    tasks = {
        "A": Task(id="A", title="Blocked Root", status=TaskStatus.BLOCKED),
        "B": Task(id="B", title="Dependent 1", status=TaskStatus.TODO),
        "C": Task(id="C", title="Dependent 2", status=TaskStatus.TODO),
        "D": Task(id="D", title="Dependent 3", status=TaskStatus.TODO),
    }
    # A -> B -> C -> D
    deps = [
        Dependency(predecessor_id="A", successor_id="B"),
        Dependency(predecessor_id="B", successor_id="C"),
        Dependency(predecessor_id="C", successor_id="D"),
    ]
    plan = ProjectPlan(
        id="P3",
        project_id="PROJ",
        version=1,
        name="Cascade Plan",
        created_at=datetime.now(UTC),
        tasks=tasks,
        dependencies=deps,
    )
    graph = TaskGraph(tasks=tasks.values(), dependencies=deps)

    risks = evaluate_blocked_cascades(plan, graph)
    assert len(risks) == 1
    assert risks[0].risk_type == RiskType.BLOCKED_CASCADE
    assert risks[0].metrics["downstream_count"] == 3
    assert set(risks[0].affected_task_ids) == {"A", "B", "C", "D"}


def test_evaluate_deadline_breach():
    clock = FrozenClock(date(2026, 10, 5))
    scheduler = DeterministicScheduler(clock)

    # 10 working days of sequential work
    tasks = {
        "T1": Task(id="T1", title="Big Work", estimated_hours=80.0),  # 10 days
    }
    plan = ProjectPlan(
        id="P4",
        project_id="PROJ",
        version=1,
        name="Deadline Risk Plan",
        created_at=datetime.now(UTC),
        tasks=tasks,
        target_completion_date=date(2026, 10, 9),  # 5 working days deadline
    )
    schedule = scheduler.schedule(plan, start_date=date(2026, 10, 5))

    risks = evaluate_deadline_breach(plan, schedule)
    assert len(risks) == 1
    assert risks[0].risk_type == RiskType.DEADLINE_BREACH
    assert risks[0].severity == RiskSeverity.CRITICAL


def test_risk_engine_health_scoring():
    clock = FrozenClock(date(2026, 10, 5))
    engine = DeterministicRiskEngine(clock)

    # Healthy plan
    healthy_tasks = {"T1": Task(id="T1", title="Task 1", estimated_hours=8.0)}
    healthy_plan = ProjectPlan(
        id="P_healthy",
        project_id="PROJ",
        version=1,
        name="Healthy",
        created_at=datetime.now(UTC),
        tasks=healthy_tasks,
    )
    result = engine.analyze_risks(healthy_plan)
    assert result.health_score == 100
    assert result.is_at_risk is False

    # Risky plan with deadline breach and overload
    risky_tasks = {
        "T1": Task(id="T1", title="Overload 1", estimated_hours=80.0, assigned_to_id="M1"),
        "T2": Task(id="T2", title="Overload 2", estimated_hours=80.0, assigned_to_id="M1"),
    }
    risky_plan = ProjectPlan(
        id="P_risky",
        project_id="PROJ",
        version=1,
        name="Risky",
        created_at=datetime.now(UTC),
        tasks=risky_tasks,
        members={"M1": Member(id="M1", name="Dev", daily_capacity_hours=8.0)},
        target_completion_date=date(2026, 10, 7),
    )
    risky_result = engine.analyze_risks(risky_plan)
    assert risky_result.is_at_risk is True
    assert risky_result.health_score < 100


def test_risk_domain_has_zero_io_imports():
    """Verify via AST that backend/app/domain/risk contains zero external I/O imports."""
    risk_dir = Path(__file__).resolve().parents[2] / "app" / "domain" / "risk"
    assert risk_dir.exists() and risk_dir.is_dir()

    forbidden = {"sqlalchemy", "fastapi", "httpx", "requests", "anthropic", "openai"}

    for py_file in risk_dir.glob("*.py"):
        with open(py_file, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(py_file))

        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]

            for name in names:
                for bad in forbidden:
                    assert not (name == bad or name.startswith(f"{bad}.")), (
                        f"Forbidden import '{name}' found in domain risk file {py_file.name}"
                    )
