"""Integration tests for Plan draft creation, server-assigned versioning, and gated activation."""

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.auth import UserORM
from backend.app.models.execution import TaskExecutionStateORM
from backend.app.models.history import AgentRunORM, DecisionRecordORM, ProgressHistoryORM


@pytest.mark.asyncio
async def test_plan_activation_flow_and_constraints(
    auth_client: httpx.AsyncClient,
    auth_user: UserORM,
    test_session: AsyncSession,
):
    # 1. Create project
    p_res = await auth_client.post("/api/v1/projects", json={"name": "Gated Plan Project"})
    assert p_res.status_code == 201
    project_id = p_res.json()["id"]

    # 2. First POST /plans -> creates draft v1 (server assigns version=1, is_active=False)
    plan_v1_payload = {
        "name": "Draft Plan 1",
        "tasks": [
            {"id": "T1", "title": "Setup", "estimated_hours": 8.0, "status": "TODO"},
            {"id": "T2", "title": "Build", "estimated_hours": 16.0, "status": "TODO"},
        ],
        "dependencies": [{"predecessor_id": "T1", "successor_id": "T2"}],
    }
    res_v1 = await auth_client.post(f"/api/v1/projects/{project_id}/plans", json=plan_v1_payload)
    assert res_v1.status_code == 201
    assert res_v1.json()["version"] == 1

    # 3. Second POST /plans -> creates draft v2 (server assigns version=2)
    plan_v2_payload = {
        "name": "Draft Plan 2",
        "tasks": [
            {"id": "T1", "title": "Setup Revised", "estimated_hours": 6.0, "status": "TODO"},
            {"id": "T2", "title": "Build Revised", "estimated_hours": 12.0, "status": "TODO"},
        ],
        "dependencies": [{"predecessor_id": "T1", "successor_id": "T2"}],
    }
    res_v2 = await auth_client.post(f"/api/v1/projects/{project_id}/plans", json=plan_v2_payload)
    assert res_v2.status_code == 201
    assert res_v2.json()["version"] == 2

    # Versions list shows [1, 2] but active_version is None!
    ver_res_initial = await auth_client.get(f"/api/v1/projects/{project_id}/plans/versions")
    assert ver_res_initial.status_code == 200
    assert ver_res_initial.json()["versions"] == [1, 2]
    assert ver_res_initial.json()["active_version"] is None

    # Neither plan is active yet -> GET /plans/active returns 404
    active_check = await auth_client.get(f"/api/v1/projects/{project_id}/plans/active")
    assert active_check.status_code == 404

    # 4. Attempt activation with empty rationale -> 422
    empty_rat_res = await auth_client.post(
        f"/api/v1/projects/{project_id}/plans/1/activate",
        json={"rationale": "   "},
    )
    assert empty_rat_res.status_code == 422

    # 5. Attempt activation on non-existent version -> 404
    missing_ver_res = await auth_client.post(
        f"/api/v1/projects/{project_id}/plans/999/activate",
        json={"rationale": "Valid rationale"},
    )
    assert missing_ver_res.status_code == 404

    # 6. Initial plan activation: activate Version 1
    act_res = await auth_client.post(
        f"/api/v1/projects/{project_id}/plans/1/activate",
        json={"rationale": "Approved initial baseline deployment plan"},
    )
    assert act_res.status_code == 200
    assert act_res.json()["version"] == 1

    # Confirm active plan is now v1
    active_plan = await auth_client.get(f"/api/v1/projects/{project_id}/plans/active")
    assert active_plan.status_code == 200
    assert active_plan.json()["version"] == 1

    # Verify decision record was written with decision_type="PLAN_ACTIVATED"
    dec_result = await test_session.execute(
        select(DecisionRecordORM).where(
            DecisionRecordORM.project_id == project_id,
            DecisionRecordORM.decision_type == "PLAN_ACTIVATED",
        )
    )
    decision = dec_result.scalar_one_or_none()
    assert decision is not None
    assert decision.decided_by == auth_user.id
    assert "Approved initial baseline" in decision.rationale

    # Verify progress event recorded
    prog_result = await test_session.execute(
        select(ProgressHistoryORM).where(
            ProgressHistoryORM.project_id == project_id,
            ProgressHistoryORM.task_id == "PROJECT_PLAN",
        )
    )
    prog = prog_result.scalar_one_or_none()
    assert prog is not None
    assert prog.new_status == "v1"
    assert prog.recorded_by == auth_user.id

    # Verify AgentRun APPROVE entry
    run_result = await test_session.execute(
        select(AgentRunORM).where(
            AgentRunORM.project_id == project_id,
            AgentRunORM.loop_stage == "APPROVE",
        )
    )
    run = run_result.scalar_one_or_none()
    assert run is not None
    assert run.status == "SUCCESS"

    # Verify execution states were backfilled for T1 and T2
    exec_result = await test_session.execute(
        select(TaskExecutionStateORM).where(TaskExecutionStateORM.project_id == project_id)
    )
    states = exec_result.scalars().all()
    assert len(states) == 2
    task_ids = {s.task_id for s in states}
    assert task_ids == {"T1", "T2"}

    # 7. Attempting to activate again when an active plan exists -> 409 Conflict
    re_act_res = await auth_client.post(
        f"/api/v1/projects/{project_id}/plans/1/activate",
        json={"rationale": "Attempting second activation of already active plan"},
    )
    assert re_act_res.status_code == 409
    assert "already has an active plan" in re_act_res.json()["detail"].lower()

    # Attempting to activate draft v2 directly when v1 is active -> 409 Conflict
    v2_act_res = await auth_client.post(
        f"/api/v1/projects/{project_id}/plans/2/activate",
        json={"rationale": "Directly activating v2"},
    )
    assert v2_act_res.status_code == 409
    assert "replan" in v2_act_res.json()["detail"].lower()

    # 8. Posting a "version 3" directly cannot change the active plan
    plan_v3_payload = {
        "name": "Draft Plan 3 Attempting Takeover",
        "tasks": [{"id": "T1", "title": "Setup", "estimated_hours": 8.0}],
        "dependencies": [],
    }
    res_v3 = await auth_client.post(f"/api/v1/projects/{project_id}/plans", json=plan_v3_payload)
    assert res_v3.status_code == 201
    assert res_v3.json()["version"] == 3

    # Active plan is STILL version 1!
    active_still_v1 = await auth_client.get(f"/api/v1/projects/{project_id}/plans/active")
    assert active_still_v1.status_code == 200
    assert active_still_v1.json()["version"] == 1

    # 9. Approved proposal path still works end to end on an active plan
    p2_res = await auth_client.post("/api/v1/projects", json={"name": "Proposal Flow Project"})
    assert p2_res.status_code == 201
    p2_id = p2_res.json()["id"]

    await auth_client.post(
        f"/api/v1/projects/{p2_id}/plans",
        json={
            "name": "P2 Baseline",
            "tasks": [{"id": "T1", "title": "Setup", "estimated_hours": 8.0}],
            "dependencies": [],
        },
    )
    await auth_client.post(
        f"/api/v1/projects/{p2_id}/plans/1/activate",
        json={"rationale": "Initial activation for replan flow"},
    )

    prop_res = await auth_client.post(f"/api/v1/projects/{p2_id}/replan/propose")
    assert prop_res.status_code == 200
    proposal_id = prop_res.json()["proposal_id"]

    approve_res = await auth_client.post(
        f"/api/v1/projects/{p2_id}/replan/approve",
        json={"proposal_id": proposal_id, "decision_rationale": "Legitimate replan upgrade"},
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "APPROVED"
    assert approve_res.json()["new_version"] == 2

    active_now_v2 = await auth_client.get(f"/api/v1/projects/{p2_id}/plans/active")
    assert active_now_v2.status_code == 200
    assert active_now_v2.json()["version"] == 2
