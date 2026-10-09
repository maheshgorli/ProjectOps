"""Integration tests for Human Approval Gateway API endpoints (Core Principle 4 & P0-1 fix)."""

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

    # 3. Propose candidate replan via server-side engine
    prop_res = await client.post(f"/api/v1/projects/{project_id}/replan/propose")
    assert prop_res.status_code == 200
    prop_data = prop_res.json()
    proposal_id = prop_data["proposal_id"]
    assert proposal_id is not None

    # Verify proposal is listed in proposals API
    list_res = await client.get(f"/api/v1/projects/{project_id}/replan/proposals")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1
    assert any(p["id"] == proposal_id for p in list_res.json())

    # 4. Officially approve candidate replan using proposal_id only (P0-1 Fix)
    approval_payload = {
        "proposal_id": proposal_id,
        "decision_rationale": "Splitting task into setup and testing to de-risk delivery.",
        "decided_by": "Engineering Lead Jane",
    }
    res = await client.post(f"/api/v1/projects/{project_id}/replan/approve", json=approval_payload)
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "APPROVED"
    assert data["previous_version"] == 1
    assert data["new_version"] == 2
    assert data["proposal_id"] == proposal_id
    assert "upgraded to v2" in data["summary"].lower()

    # 5. Confirm new active plan is v2
    active_res = await client.get(f"/api/v1/projects/{project_id}/plans/active")
    assert active_res.status_code == 200
    assert active_res.json()["version"] == 2

    # 6. Rule 5: Verify decision audit trail record
    decisions_res = await client.get(f"/api/v1/projects/{project_id}/decisions")
    assert decisions_res.status_code == 200
    decisions = decisions_res.json()
    assert len(decisions) >= 1
    approval_decision = [d for d in decisions if d["decision_type"] == "REPLAN_APPROVED"][0]
    assert approval_decision["decided_by"] == "Engineering Lead Jane"
    assert "Splitting task" in approval_decision["rationale"]

    # 7. Verify progress history event recorded
    history_res = await client.get(f"/api/v1/projects/{project_id}/history/progress")
    assert history_res.status_code == 200
    history = history_res.json()
    assert any("v2" in h["new_status"] for h in history)


@pytest.mark.asyncio
async def test_client_tampered_plan_body_fails_validation_p0_1(client: httpx.AsyncClient):
    """
    P0-1 Security Test: Clients can no longer supply custom JSON candidate_plan payloads.
    Direct injection of arbitrary plans must fail schema validation (HTTP 422).
    """
    p_res = await client.post("/api/v1/projects", json={"name": "Tamper Test Project"})
    project_id = p_res.json()["id"]

    tampered_payload = {
        "candidate_plan": {
            "version": 50,
            "name": "Tampered Plan Never Proposed",
            "tasks": [
                {
                    "id": "TASK-999",
                    "title": "Hacked Task",
                    "status": "COMPLETED",
                    "estimated_hours": 4.0,
                }
            ],
            "dependencies": [],
        },
        "decision_rationale": "Attacker attempting to inject plan",
        "decided_by": "malicious_actor",
    }
    res = await client.post(f"/api/v1/projects/{project_id}/replan/approve", json=tampered_payload)
    assert res.status_code == 422


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

    # Generate server proposal
    prop_res = await client.post(f"/api/v1/projects/{project_id}/replan/propose")
    assert prop_res.status_code == 200
    proposal_id = prop_res.json()["proposal_id"]

    # Reject the server proposition
    reject_payload = {
        "proposal_id": proposal_id,
        "rationale": "Scope addition is unnecessary before client demo.",
        "decided_by": "Product Director Bob",
    }
    res = await client.post(f"/api/v1/projects/{project_id}/replan/reject", json=reject_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "REJECTED"
    assert data["current_version"] == 1
    assert data["proposal_id"] == proposal_id

    # Active plan remains unchanged at v1
    active_res = await client.get(f"/api/v1/projects/{project_id}/plans/active")
    assert active_res.status_code == 200
    assert active_res.json()["version"] == 1

    # Verify decision record
    decisions_res = await client.get(f"/api/v1/projects/{project_id}/decisions")
    assert decisions_res.status_code == 200
    decisions = decisions_res.json()
    assert any(d["decision_type"] == "REPLAN_REJECTED" for d in decisions)

    # Verify proposal status in DB is REJECTED
    prop_status_res = await client.get(
        f"/api/v1/projects/{project_id}/replan/proposals/{proposal_id}"
    )
    assert prop_status_res.status_code == 200
    assert prop_status_res.json()["status"] == "REJECTED"


@pytest.mark.asyncio
async def test_approvals_api_project_not_found(client: httpx.AsyncClient):
    fake_id = "non_existent_project_uuid"
    res1 = await client.post(
        f"/api/v1/projects/{fake_id}/replan/approve",
        json={
            "proposal_id": "non-existent-prop-id",
            "decision_rationale": "Valid rationale for non-existent project",
            "decided_by": "admin",
        },
    )
    assert res1.status_code == 404

    res2 = await client.post(
        f"/api/v1/projects/{fake_id}/replan/reject",
        json={
            "proposal_id": "non-existent-prop-id",
            "rationale": "not needed",
            "decided_by": "admin",
        },
    )
    assert res2.status_code == 404


@pytest.mark.asyncio
async def test_stale_baseline_proposal_raises_409(client: httpx.AsyncClient):
    """Proposals generated against an older plan version are rejected with 409 Conflict."""
    p_res = await client.post("/api/v1/projects", json={"name": "Stale Proposal Project"})
    project_id = p_res.json()["id"]

    v1_payload = {
        "version": 1,
        "name": "Plan v1",
        "tasks": [{"id": "T1", "title": "Task 1", "estimated_hours": 8.0}],
        "dependencies": [],
    }
    await client.post(f"/api/v1/projects/{project_id}/plans", json=v1_payload)

    # Generate proposal against v1
    prop_res = await client.post(f"/api/v1/projects/{project_id}/replan/propose")
    proposal_id = prop_res.json()["proposal_id"]

    # Directly create and activate plan v2
    v2_payload = {
        "version": 2,
        "name": "Direct Plan v2",
        "tasks": [{"id": "T1", "title": "Task 1", "estimated_hours": 8.0}],
        "dependencies": [],
    }
    await client.post(f"/api/v1/projects/{project_id}/plans", json=v2_payload)

    # Attempting to approve proposal from v1 while active plan is now v2 should raise 409
    res = await client.post(
        f"/api/v1/projects/{project_id}/replan/approve",
        json={
            "proposal_id": proposal_id,
            "decision_rationale": "Trying to approve outdated proposal",
            "decided_by": "admin",
        },
    )
    assert res.status_code == 409
    assert "stale" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_non_pending_proposal_raises_409(client: httpx.AsyncClient):
    """Proposals that are already APPROVED, REJECTED, or SUPERSEDED cannot be approved again."""
    p_res = await client.post("/api/v1/projects", json={"name": "Re-approval Project"})
    project_id = p_res.json()["id"]

    v1_payload = {
        "version": 1,
        "name": "Plan v1",
        "tasks": [{"id": "T1", "title": "Task 1", "estimated_hours": 8.0}],
        "dependencies": [],
    }
    await client.post(f"/api/v1/projects/{project_id}/plans", json=v1_payload)

    prop_res = await client.post(f"/api/v1/projects/{project_id}/replan/propose")
    proposal_id = prop_res.json()["proposal_id"]

    # Approve proposal once
    app_res = await client.post(
        f"/api/v1/projects/{project_id}/replan/approve",
        json={
            "proposal_id": proposal_id,
            "decision_rationale": "First approval",
            "decided_by": "lead",
        },
    )
    assert app_res.status_code == 200

    # Attempt to approve again -> 409 Conflict
    re_app_res = await client.post(
        f"/api/v1/projects/{project_id}/replan/approve",
        json={
            "proposal_id": proposal_id,
            "decision_rationale": "Second approval attempt",
            "decided_by": "lead",
        },
    )
    assert re_app_res.status_code == 409
    assert "cannot be approved" in re_app_res.json()["detail"].lower()
