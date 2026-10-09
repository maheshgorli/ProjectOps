"""Integration tests for the Autonomous Multi-Agent Execution Loop."""

import httpx
import pytest


@pytest.mark.asyncio
async def test_execution_loop_healthy_project(client: httpx.AsyncClient):
    # 1. Setup project with 2 tasks: T1 (TODO) -> T2 (TODO)
    p_res = await client.post("/api/v1/projects", json={"name": "Healthy Loop Project"})
    project_id = p_res.json()["id"]

    m_res = await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"name": "Dev Alice", "role": "engineer", "daily_capacity_hours": 8.0},
    )
    alice_id = m_res.json()["id"]

    plan_payload = {
        "version": 1,
        "name": "Linear Sprint",
        "tasks": [
            {
                "id": "T1",
                "title": "Design Specs",
                "status": "TODO",
                "estimated_hours": 4.0,
                "assigned_to_id": alice_id,
            },
            {
                "id": "T2",
                "title": "Implement Specs",
                "status": "TODO",
                "estimated_hours": 4.0,
                "assigned_to_id": alice_id,
            },
        ],
        "dependencies": [
            {
                "predecessor_id": "T1",
                "successor_id": "T2",
                "dep_type": "FINISH_TO_START",
                "lag_days": 0,
            }
        ],
    }
    p_plan_res = await client.post(f"/api/v1/projects/{project_id}/plans", json=plan_payload)
    assert p_plan_res.status_code == 201

    # 2. Trigger agent loop step
    step_res = await client.post(f"/api/v1/projects/{project_id}/agent-loop/step")
    assert step_res.status_code == 200
    data = step_res.json()

    assert data["status"] == "HEALTHY"
    assert data["is_at_risk"] is False
    assert data["health_score"] == 100.0
    assert data["requires_human_approval"] is False
    assert data["replan_candidate"] is None

    # T2 depends on T1 (which is TODO), so only T1 is currently actionable!
    assert data["actionable_tasks"] == ["T1"]

    # 3. Verify agent loop run history recorded
    status_res = await client.get(f"/api/v1/projects/{project_id}/agent-loop/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["active_plan_version"] == 1
    assert status_data["requires_human_approval"] is False
    assert len(status_data["recent_runs"]) >= 4  # PLAN, EXECUTE, OBSERVE, REASON, APPROVE


@pytest.mark.asyncio
async def test_execution_loop_at_risk_halts_for_approval_and_resumes(
    client: httpx.AsyncClient,
):
    """
    Test full loop cycle with risk detection:
    PLAN -> EXECUTE -> OBSERVE -> REASON -> REPLAN (halts at AWAITING_APPROVAL) -> APPROVE -> RESUME
    """
    # 1. Create project with Alice (overloaded) and Bob (available)
    p_res = await client.post("/api/v1/projects", json={"name": "Risk Loop Project"})
    project_id = p_res.json()["id"]

    m1_res = await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"name": "Alice Lead", "role": "lead", "daily_capacity_hours": 8.0},
    )
    alice_id = m1_res.json()["id"]

    m2_res = await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"name": "Bob Support", "role": "engineer", "daily_capacity_hours": 8.0},
    )
    assert m2_res.json()["id"] is not None

    # Alice assigned 2 parallel 8h tasks scheduled concurrently -> capacity overload!
    plan_payload = {
        "version": 1,
        "name": "Overallocated Baseline",
        "tasks": [
            {
                "id": "T1",
                "title": "Backend Core",
                "status": "TODO",
                "estimated_hours": 8.0,
                "assigned_to_id": alice_id,
            },
            {
                "id": "T2",
                "title": "Frontend Core",
                "status": "TODO",
                "estimated_hours": 8.0,
                "assigned_to_id": alice_id,
            },
        ],
        "dependencies": [],
    }
    await client.post(f"/api/v1/projects/{project_id}/plans", json=plan_payload)

    # 2. Run agent loop step -> should detect risk and halt at AWAITING_APPROVAL
    step_res = await client.post(f"/api/v1/projects/{project_id}/agent-loop/step")
    assert step_res.status_code == 200
    data = step_res.json()

    assert data["current_stage"] == "REPLAN"
    assert data["status"] == "AWAITING_APPROVAL"
    assert data["is_at_risk"] is True
    assert data["requires_human_approval"] is True
    assert data["replan_candidate"] is not None
    assert data["replan_candidate"]["resolved_risks_count"] >= 1

    candidate = data["replan_candidate"]

    # 3. Check loop status
    loop_status_res = await client.get(f"/api/v1/projects/{project_id}/agent-loop/status")
    assert loop_status_res.status_code == 200
    loop_status = loop_status_res.json()
    assert loop_status["current_status"] == "AWAITING_APPROVAL"
    assert loop_status["requires_human_approval"] is True

    # 4. Human Approval Gateway: Approve server-stored candidate replan
    proposal_id = candidate["proposal_id"]
    assert proposal_id is not None
    approval_payload = {
        "proposal_id": proposal_id,
        "decision_rationale": "Reassigning T2 to Bob to alleviate Alice's capacity overload.",
        "decided_by": "Engineering Manager Dave",
    }
    approve_res = await client.post(
        f"/api/v1/projects/{project_id}/replan/approve", json=approval_payload
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["new_version"] == 2

    # 5. Run next loop step -> should resume and execute healthy plan
    next_step_res = await client.post(f"/api/v1/projects/{project_id}/agent-loop/step")
    assert next_step_res.status_code == 200
    next_data = next_step_res.json()
    assert next_data["status"] == "HEALTHY"
    assert next_data["is_at_risk"] is False
    assert next_data["requires_human_approval"] is False
    assert len(next_data["actionable_tasks"]) == 2  # Both T1 and T2 now actionable without overload


@pytest.mark.asyncio
async def test_agent_loop_project_not_found(client: httpx.AsyncClient):
    fake_id = "non_existent_loop_project"
    res1 = await client.post(f"/api/v1/projects/{fake_id}/agent-loop/step")
    assert res1.status_code == 404

    res2 = await client.get(f"/api/v1/projects/{fake_id}/agent-loop/status")
    assert res2.status_code == 404
