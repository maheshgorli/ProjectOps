"""Identity-forgery tests: Ensure client-supplied actor fields are rejected with 422
and attribution is server-derived.
"""

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.auth import UserORM
from backend.app.models.execution import TaskExecutionStateORM
from backend.app.models.history import AgentRunORM, DecisionRecordORM, ProgressHistoryORM


@pytest.mark.asyncio
async def test_identity_forgery_rejected_with_422(
    auth_client: httpx.AsyncClient,
    test_session: AsyncSession,
):
    # Setup project
    p_res = await auth_client.post("/api/v1/projects", json={"name": "Forgery Defense Project"})
    project_id = p_res.json()["id"]

    # 1. Plan creation sending created_by is rejected with 422
    forged_plan_1 = {
        "name": "Forged Plan",
        "created_by": "attacker",
        "tasks": [{"id": "T1", "title": "Task 1", "estimated_hours": 8.0}],
        "dependencies": [],
    }
    res = await auth_client.post(f"/api/v1/projects/{project_id}/plans", json=forged_plan_1)
    assert res.status_code == 422
    assert "extra_forbidden" in str(res.json()).lower() or "extra fields" in str(res.json()).lower()

    # 2. Plan creation sending version is rejected with 422
    forged_plan_2 = {
        "name": "Forged Version Plan",
        "version": 10,
        "tasks": [{"id": "T1", "title": "Task 1", "estimated_hours": 8.0}],
        "dependencies": [],
    }
    res = await auth_client.post(f"/api/v1/projects/{project_id}/plans", json=forged_plan_2)
    assert res.status_code == 422

    # Create valid plan and activate it
    valid_plan = {
        "name": "Valid Baseline",
        "tasks": [{"id": "T1", "title": "Task 1", "estimated_hours": 8.0}],
        "dependencies": [],
    }
    p_valid = await auth_client.post(f"/api/v1/projects/{project_id}/plans", json=valid_plan)
    assert p_valid.status_code == 201
    await auth_client.post(
        f"/api/v1/projects/{project_id}/plans/1/activate",
        json={"rationale": "Initial activation"},
    )

    # 3. Task status update sending updated_by is rejected with 422
    forged_task = {
        "status": "IN_PROGRESS",
        "updated_by": "impersonated_user",
    }
    res = await auth_client.patch(
        f"/api/v1/projects/{project_id}/tasks/T1/status", json=forged_task
    )
    assert res.status_code == 422

    # 4. Generate proposal for approval/rejection tests
    prop_res = await auth_client.post(f"/api/v1/projects/{project_id}/replan/propose")
    proposal_id = prop_res.json()["proposal_id"]

    # 5. Replan approval sending decided_by is rejected with 422
    forged_approval = {
        "proposal_id": proposal_id,
        "decision_rationale": "Valid text",
        "decided_by": "forged_lead",
    }
    res = await auth_client.post(
        f"/api/v1/projects/{project_id}/replan/approve", json=forged_approval
    )
    assert res.status_code == 422

    # 6. Replan rejection sending decided_by is rejected with 422
    forged_rejection = {
        "proposal_id": proposal_id,
        "rationale": "Valid rejection",
        "decided_by": "forged_lead",
    }
    res = await auth_client.post(
        f"/api/v1/projects/{project_id}/replan/reject", json=forged_rejection
    )
    assert res.status_code == 422

    # 7. Decision record creation sending decided_by is rejected with 422
    forged_decision = {
        "decision_type": "REPLAN_APPROVAL",
        "summary": "Summary",
        "rationale": "Rationale",
        "decided_by": "forged_actor",
    }
    res = await auth_client.post(f"/api/v1/projects/{project_id}/decisions", json=forged_decision)
    assert res.status_code == 422

    # 8. Progress event creation sending recorded_by is rejected with 422
    forged_progress = {
        "task_id": "T1",
        "new_status": "IN_PROGRESS",
        "recorded_by": "forged_system",
    }
    res = await auth_client.post(
        f"/api/v1/projects/{project_id}/history/progress", json=forged_progress
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_server_derives_identity_and_ignores_query_params(
    auth_client: httpx.AsyncClient,
    auth_user: UserORM,
    test_session: AsyncSession,
):
    # Setup project and plan
    p_res = await auth_client.post("/api/v1/projects", json={"name": "Attribution Project"})
    project_id = p_res.json()["id"]

    valid_plan = {
        "name": "Baseline",
        "tasks": [{"id": "T1", "title": "Task 1", "estimated_hours": 8.0}],
        "dependencies": [],
    }
    await auth_client.post(f"/api/v1/projects/{project_id}/plans", json=valid_plan)
    await auth_client.post(
        f"/api/v1/projects/{project_id}/plans/1/activate",
        json={"rationale": "Initial activation"},
    )

    # 1. Trigger agent loop with forged query param ?triggered_by=attacker
    loop_res = await auth_client.post(
        f"/api/v1/projects/{project_id}/agent-loop/step?triggered_by=attacker"
    )
    assert loop_res.status_code == 200

    # Verify agent run record in DB carries user:<auth_user.id>, NOT "attacker"
    result = await test_session.execute(
        select(AgentRunORM).where(AgentRunORM.project_id == project_id)
    )
    runs = result.scalars().all()
    assert len(runs) >= 1
    for run in runs:
        assert run.triggered_by == f"user:{auth_user.id}"
        assert "attacker" not in run.triggered_by

    # 2. Update task status without client actor -> DB record has auth_user.id
    update_res = await auth_client.patch(
        f"/api/v1/projects/{project_id}/tasks/T1/status",
        json={"status": "IN_PROGRESS", "evidence_notes": "Valid update"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["updated_by"] == auth_user.id

    exec_res = await test_session.execute(
        select(TaskExecutionStateORM).where(
            TaskExecutionStateORM.project_id == project_id,
            TaskExecutionStateORM.task_id == "T1",
        )
    )
    exec_state = exec_res.scalar_one_or_none()
    assert exec_state is not None
    assert exec_state.updated_by == auth_user.id

    # 3. Decision recorded carries auth_user.id
    dec_res = await auth_client.post(
        f"/api/v1/projects/{project_id}/decisions",
        json={"decision_type": "ARCHITECTURE_CHOICE", "summary": "Chose Postgres"},
    )
    assert dec_res.status_code == 201
    assert dec_res.json()["decided_by"] == auth_user.id

    dec_record = await test_session.get(DecisionRecordORM, dec_res.json()["id"])
    assert dec_record is not None
    assert dec_record.decided_by == auth_user.id

    # 4. Progress history event recorded carries auth_user.id
    prog_res = await auth_client.post(
        f"/api/v1/projects/{project_id}/history/progress",
        json={"task_id": "T1", "new_status": "BLOCKED", "evidence_notes": "Vendor down"},
    )
    assert prog_res.status_code == 201
    assert prog_res.json()["recorded_by"] == auth_user.id

    prog_record = await test_session.get(ProgressHistoryORM, prog_res.json()["id"])
    assert prog_record is not None
    assert prog_record.recorded_by == auth_user.id
