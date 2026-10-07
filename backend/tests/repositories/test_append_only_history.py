"""Tests for append-only audit trail repositories."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.repositories.history_repository import HistoryRepository
from backend.app.repositories.project_repository import ProjectRepository


@pytest.mark.asyncio
async def test_append_only_progress_history(test_session: AsyncSession):
    project_repo = ProjectRepository(test_session)
    history_repo = HistoryRepository(test_session)

    project = await project_repo.create_project(name="Audit Test Project")

    # Record two sequential progress events for task T1
    event1 = await history_repo.record_progress(
        project_id=project.id,
        task_id="T1",
        previous_status="TODO",
        new_status="IN_PROGRESS",
        evidence_notes="Branch created and PR opened",
        recorded_by="agent-orchestrator",
        recorded_at=datetime(2026, 10, 5, 9, 0, tzinfo=UTC),
    )
    assert event1.id is not None

    event2 = await history_repo.record_progress(
        project_id=project.id,
        task_id="T1",
        previous_status="IN_PROGRESS",
        new_status="COMPLETED",
        evidence_notes="PR merged to main and CI passed",
        recorded_by="human-reviewer",
        recorded_at=datetime(2026, 10, 5, 17, 0, tzinfo=UTC),
    )
    assert event2.id is not None

    await test_session.commit()

    # Query history
    history = await history_repo.get_progress_history(project.id, task_id="T1")
    assert len(history) == 2
    assert history[0].previous_status == "TODO"
    assert history[0].new_status == "IN_PROGRESS"
    assert history[1].previous_status == "IN_PROGRESS"
    assert history[1].new_status == "COMPLETED"


@pytest.mark.asyncio
async def test_append_only_decisions_and_risks(test_session: AsyncSession):
    project_repo = ProjectRepository(test_session)
    history_repo = HistoryRepository(test_session)

    project = await project_repo.create_project(name="Governance Project")

    # Record decision
    decision = await history_repo.record_decision(
        project_id=project.id,
        plan_id=None,
        decision_type="REPLAN_APPROVED",
        summary="Approved 2-day buffer extension for frontend tasks",
        rationale="Unforeseen third-party API deprecation required wrapper refactoring",
        decided_by="project_lead_human",
    )
    assert decision.id is not None

    # Record risk event
    risk = await history_repo.record_risk_event(
        project_id=project.id,
        risk_type="CRITICAL_PATH_SLIPPAGE",
        severity="HIGH",
        description="Task T2 is 1 day behind schedule on critical path",
        payload_json='{"task_id": "T2", "delay_working_days": 1}',
    )
    assert risk.id is not None

    await test_session.commit()

    # Verify query
    decisions = await history_repo.get_decisions(project.id)
    assert len(decisions) == 1
    assert decisions[0].decision_type == "REPLAN_APPROVED"
    assert "Unforeseen third-party API" in decisions[0].rationale

    risks = await history_repo.get_risk_events(project.id, min_severity="HIGH")
    assert len(risks) == 1
    assert risks[0].risk_type == "CRITICAL_PATH_SLIPPAGE"
    assert risks[0].severity == "HIGH"


@pytest.mark.asyncio
async def test_append_only_agent_runs_and_github_events(test_session: AsyncSession):
    project_repo = ProjectRepository(test_session)
    history_repo = HistoryRepository(test_session)

    project = await project_repo.create_project(name="Agent Loop & GH History Project")

    # Record agent runs
    run1 = await history_repo.record_agent_run(
        project_id=project.id,
        loop_stage="PLAN",
        status="SUCCESS",
        summary="Plan stage complete",
    )
    run2 = await history_repo.record_agent_run(
        project_id=project.id,
        loop_stage="REPLAN",
        status="AWAITING_APPROVAL",
        summary="Replan candidate requires approval",
    )
    assert run1.id is not None
    assert run2.id is not None

    # Record github event
    gh_event = await history_repo.record_github_event(
        project_id=project.id,
        event_type="push",
        sender="octocat",
        summary="Push event by octocat",
        ref="refs/heads/main",
        commit_sha="11223344",
        raw_payload_json='{"ref": "refs/heads/main"}',
    )
    assert gh_event.id is not None

    await test_session.commit()

    # Query agent runs (sorted newest first)
    runs = await history_repo.get_agent_runs(project.id, limit=10)
    assert len(runs) == 2
    assert runs[0].loop_stage == "REPLAN"
    assert runs[1].loop_stage == "PLAN"

    # Query github events
    gh_events = await history_repo.get_github_events(project.id, limit=10)
    assert len(gh_events) == 1
    assert gh_events[0].sender == "octocat"
    assert gh_events[0].commit_sha == "11223344"
