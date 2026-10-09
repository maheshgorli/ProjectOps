"""Integration tests for Server-Side Replan Proposals Lifecycle (P0-1 Fix)."""

import httpx
import pytest


@pytest.mark.asyncio
async def test_proposals_lifecycle_and_superseding(client: httpx.AsyncClient):
    # 1. Create project and team member
    p_res = await client.post("/api/v1/projects", json={"name": "Proposal Lifecycle Project"})
    project_id = p_res.json()["id"]

    m_res = await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"name": "Dev Alice", "role": "engineer", "daily_capacity_hours": 8.0},
    )
    alice_id = m_res.json()["id"]

    # 2. Create baseline plan v1
    v1_payload = {
        "version": 1,
        "name": "Sprint 1 Baseline",
        "tasks": [
            {
                "id": "T1",
                "title": "Backend Architecture",
                "estimated_hours": 8.0,
                "status": "TODO",
                "assigned_to_id": alice_id,
            }
        ],
        "dependencies": [],
    }
    await client.post(f"/api/v1/projects/{project_id}/plans", json=v1_payload)

    # 3. Generate proposal 1
    p1_res = await client.post(f"/api/v1/projects/{project_id}/replan/propose")
    assert p1_res.status_code == 200
    prop1_id = p1_res.json()["proposal_id"]

    # Check proposal 1 is PENDING
    prop1_detail = await client.get(f"/api/v1/projects/{project_id}/replan/proposals/{prop1_id}")
    assert prop1_detail.status_code == 200
    assert prop1_detail.json()["status"] == "PENDING"

    # 4. Generate proposal 2 -> Proposal 1 should be SUPERSEDED
    p2_res = await client.post(f"/api/v1/projects/{project_id}/replan/propose")
    assert p2_res.status_code == 200
    prop2_id = p2_res.json()["proposal_id"]
    assert prop2_id != prop1_id

    prop1_after = await client.get(f"/api/v1/projects/{project_id}/replan/proposals/{prop1_id}")
    assert prop1_after.json()["status"] == "SUPERSEDED"

    prop2_after = await client.get(f"/api/v1/projects/{project_id}/replan/proposals/{prop2_id}")
    assert prop2_after.json()["status"] == "PENDING"

    # 5. List with filters
    pending_list = await client.get(
        f"/api/v1/projects/{project_id}/replan/proposals",
        params={"status": "PENDING"},
    )
    assert pending_list.status_code == 200
    assert len(pending_list.json()) == 1
    assert pending_list.json()[0]["id"] == prop2_id

    superseded_list = await client.get(
        f"/api/v1/projects/{project_id}/replan/proposals",
        params={"status": "SUPERSEDED"},
    )
    assert superseded_list.status_code == 200
    assert any(p["id"] == prop1_id for p in superseded_list.json())

    # 6. Attempting to approve SUPERSEDED proposal 1 fails with 409
    super_approve = await client.post(
        f"/api/v1/projects/{project_id}/replan/approve",
        json={
            "proposal_id": prop1_id,
            "decision_rationale": "Trying to approve superseded proposal",
            "decided_by": "lead",
        },
    )
    assert super_approve.status_code == 409
    assert "cannot be approved" in super_approve.json()["detail"].lower()


@pytest.mark.asyncio
async def test_replan_approval_carries_forward_execution_states(client: httpx.AsyncClient):
    """Verify that approving a new plan version carries forward existing task execution states."""
    # 1. Setup project, member, plan v1
    p_res = await client.post("/api/v1/projects", json={"name": "Carry Forward Project"})
    project_id = p_res.json()["id"]

    m_res = await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"name": "Dev Alice", "role": "engineer", "daily_capacity_hours": 8.0},
    )
    alice_id = m_res.json()["id"]

    v1_payload = {
        "version": 1,
        "name": "Plan v1",
        "tasks": [
            {
                "id": "T1",
                "title": "Core Module",
                "estimated_hours": 8.0,
                "status": "TODO",
                "assigned_to_id": alice_id,
            }
        ],
        "dependencies": [],
    }
    await client.post(f"/api/v1/projects/{project_id}/plans", json=v1_payload)

    # 2. Update T1 execution state to IN_PROGRESS with actual hours
    patch_res = await client.patch(
        f"/api/v1/projects/{project_id}/tasks/T1/status",
        json={
            "status": "IN_PROGRESS",
            "actual_hours": 3.5,
            "percent_complete": 40,
            "evidence_notes": "Work underway",
            "updated_by": "alice",
        },
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "IN_PROGRESS"
    assert patch_res.json()["actual_hours"] == 3.5

    # 3. Propose replan and approve
    prop_res = await client.post(f"/api/v1/projects/{project_id}/replan/propose")
    proposal_id = prop_res.json()["proposal_id"]

    app_res = await client.post(
        f"/api/v1/projects/{project_id}/replan/approve",
        json={
            "proposal_id": proposal_id,
            "decision_rationale": "Approved mitigation",
            "decided_by": "manager",
        },
    )
    assert app_res.status_code == 200
    assert app_res.json()["new_version"] == 2

    # 4. Verify merged tasks on active plan v2 retained runtime execution state
    tasks_res = await client.get(f"/api/v1/projects/{project_id}/tasks")
    assert tasks_res.status_code == 200
    tasks = tasks_res.json()
    t1 = next(t for t in tasks if t["id"] == "T1")
    assert t1["status"] == "IN_PROGRESS"
    assert t1["actual_hours"] == 3.5
    assert t1["percent_complete"] == 40
