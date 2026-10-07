"""Integration tests for Human Approval Gateway API endpoints."""

import httpx
import pytest


@pytest.mark.asyncio
async def test_approve_candidate_replan(client: httpx.AsyncClient):
    # 1. Create project and team member
    p_res = await client.post("/api/v1/projects", json={"name": "Approval Project"})
    assert p_res.status_code == 201
    project_id = p_res.json()["id"]

    m_res = await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"name": "Dev Alice", "role": "engineer", "daily_capacity_hours": 8.0},
    )
    alice_id = m_res.json()["id"]

    # 2. Create baseline plan v1
    v1_payload = {
        "version": 1,
        "name": "Plan v1",
        "tasks": [
            {
                "id": "T1",
                "title": "Backend Setup",
                "estimated_hours": 8.0,
                "assigned_to_id": alice_id,
            }
        ],
        "dependencies": [],
    }
    await client.post(f"/api/v1/projects/{project_id}/plans", json=v1_payload)

    # 3. Propose and approve candidate replan v2
    approval_payload = {
        "candidate_plan": {
            "version": 2,
            "name": "Mitigated Plan v2",
            "tasks": [
                {
                    "id": "T1",
                    "title": "Backend Setup",
                    "estimated_hours": 4.0,
                    "assigned_to_id": alice_id,
                },
                {
                    "id": "T2",
                    "title": "Integration Tests",
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
        },
        "decision_rationale": "Splitting task into setup and testing to de-risk delivery.",
        "decided_by": "Engineering Lead Jane",
    }
    res = await client.post(f"/api/v1/projects/{project_id}/replan/approve", json=approval_payload)
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "APPROVED"
    assert data["previous_version"] == 1
    assert data["new_version"] == 2
    assert "Jane" in data["summary"] or "upgraded" in data["summary"]
    assert len(data["plan"]["tasks"]) == 2

    # 4. Confirm new active plan is v2
    active_res = await client.get(f"/api/v1/projects/{project_id}/plans/active")
    assert active_res.status_code == 200
    assert active_res.json()["version"] == 2

    # 5. Rule 5: Verify decision audit trail record
    decisions_res = await client.get(f"/api/v1/projects/{project_id}/decisions")
    assert decisions_res.status_code == 200
    decisions = decisions_res.json()
    assert len(decisions) >= 1
    approval_decision = [d for d in decisions if d["decision_type"] == "REPLAN_APPROVED"][0]
    assert approval_decision["decided_by"] == "Engineering Lead Jane"
    assert "Splitting task" in approval_decision["rationale"]

    # 6. Verify progress history event recorded
    history_res = await client.get(f"/api/v1/projects/{project_id}/history/progress")
    assert history_res.status_code == 200
    history = history_res.json()
    assert any("v2" in h["new_status"] for h in history)


@pytest.mark.asyncio
async def test_approve_replan_with_cycle_fails_with_422(client: httpx.AsyncClient):
    p_res = await client.post("/api/v1/projects", json={"name": "Cyclic Replan Project"})
    project_id = p_res.json()["id"]

    # Attempt to approve replan with a cycle A -> B -> A
    cyclic_payload = {
        "candidate_plan": {
            "version": 2,
            "name": "Cyclic Candidate",
            "tasks": [
                {"id": "A", "title": "Task A", "estimated_hours": 8.0},
                {"id": "B", "title": "Task B", "estimated_hours": 8.0},
            ],
            "dependencies": [
                {"predecessor_id": "A", "successor_id": "B"},
                {"predecessor_id": "B", "successor_id": "A"},
            ],
        },
        "decision_rationale": "Invalid cyclic plan",
        "decided_by": "Tester",
    }
    res = await client.post(f"/api/v1/projects/{project_id}/replan/approve", json=cyclic_payload)
    assert res.status_code == 422
    err_detail = res.json()["detail"].lower()
    assert "cycle" in err_detail or "circular" in err_detail


@pytest.mark.asyncio
async def test_reject_candidate_replan(client: httpx.AsyncClient):
    p_res = await client.post("/api/v1/projects", json={"name": "Reject Project"})
    project_id = p_res.json()["id"]

    v1_payload = {
        "version": 1,
        "name": "Plan v1",
        "tasks": [{"id": "T1", "title": "Feature 1", "estimated_hours": 8.0}],
        "dependencies": [],
    }
    await client.post(f"/api/v1/projects/{project_id}/plans", json=v1_payload)

    # Reject a candidate proposition
    reject_payload = {
        "rationale": "Scope addition is unnecessary before client demo.",
        "decided_by": "Product Director Bob",
    }
    res = await client.post(f"/api/v1/projects/{project_id}/replan/reject", json=reject_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "REJECTED"
    assert data["current_version"] == 1

    # Active plan remains unchanged at v1
    active_res = await client.get(f"/api/v1/projects/{project_id}/plans/active")
    assert active_res.status_code == 200
    assert active_res.json()["version"] == 1

    # Verify decision record
    decisions_res = await client.get(f"/api/v1/projects/{project_id}/decisions")
    assert decisions_res.status_code == 200
    decisions = decisions_res.json()
    assert any(d["decision_type"] == "REPLAN_REJECTED" for d in decisions)


@pytest.mark.asyncio
async def test_approvals_api_project_not_found(client: httpx.AsyncClient):
    fake_id = "non_existent_project_uuid"
    res1 = await client.post(
        f"/api/v1/projects/{fake_id}/replan/approve",
        json={
            "candidate_plan": {"version": 2, "name": "Plan 2"},
            "decision_rationale": "Valid rationale for non-existent project",
            "decided_by": "admin",
        },
    )
    assert res1.status_code == 404

    res2 = await client.post(
        f"/api/v1/projects/{fake_id}/replan/reject",
        json={"rationale": "not needed", "decided_by": "admin"},
    )
    assert res2.status_code == 404


@pytest.mark.asyncio
async def test_approve_replan_version_collision_conflict(client: httpx.AsyncClient):
    """Rule 5: Saving already-existing plan version raises 409 Conflict."""
    p_res = await client.post("/api/v1/projects", json={"name": "Conflict Project"})
    project_id = p_res.json()["id"]

    v1_payload = {
        "version": 1,
        "name": "Plan v1",
        "tasks": [{"id": "T1", "title": "Task 1", "estimated_hours": 8.0}],
        "dependencies": [],
    }
    await client.post(f"/api/v1/projects/{project_id}/plans", json=v1_payload)
    v2_payload = {
        "version": 2,
        "name": "Plan v2",
        "tasks": [{"id": "T1", "title": "Task 1", "estimated_hours": 8.0}],
        "dependencies": [],
    }
    await client.post(f"/api/v1/projects/{project_id}/plans", json=v2_payload)

    # Now attempt to approve candidate plan specifying already-existing version 2
    approval_payload = {
        "candidate_plan": {
            "version": 2,
            "name": "Collision Plan v2",
            "tasks": [{"id": "T1", "title": "Task 1", "estimated_hours": 8.0}],
            "dependencies": [],
        },
        "decision_rationale": "Attempting duplicate version 2",
        "decided_by": "admin",
    }
    res = await client.post(f"/api/v1/projects/{project_id}/replan/approve", json=approval_payload)
    assert res.status_code == 409
    assert "already exists" in res.json()["detail"]
