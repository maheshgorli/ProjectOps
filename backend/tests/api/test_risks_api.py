"""Integration tests for Risks Analysis and Replan Propose API endpoints."""

import httpx
import pytest


@pytest.mark.asyncio
async def test_risk_analysis_and_replan_propose_api(client: httpx.AsyncClient):
    # 1. Create project with two team members
    p_res = await client.post("/api/v1/projects", json={"name": "Risk & Replan API Project"})
    assert p_res.status_code == 201
    project_id = p_res.json()["id"]

    m1_res = await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"name": "Alice Dev", "role": "lead", "daily_capacity_hours": 8.0},
    )
    alice_id = m1_res.json()["id"]

    # Bob is available with spare capacity
    await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"name": "Bob Dev", "role": "engineer", "daily_capacity_hours": 8.0},
    )

    # 2. Create baseline plan with an intentional capacity overload: Alice assigned 2 parallel tasks
    plan_payload = {
        "version": 1,
        "name": "Overloaded Baseline",
        "tasks": [
            {
                "id": "T1",
                "title": "DB Migration",
                "estimated_hours": 8.0,
                "assigned_to_id": alice_id,
            },
            {
                "id": "T2",
                "title": "Auth Setup",
                "estimated_hours": 8.0,
                "assigned_to_id": alice_id,
            },
        ],
        "dependencies": [],  # Both scheduled concurrently on day 1
    }
    await client.post(f"/api/v1/projects/{project_id}/plans", json=plan_payload)

    # 3. Analyze risks via GET /risks/analyze
    risk_res = await client.get(f"/api/v1/projects/{project_id}/risks/analyze")
    assert risk_res.status_code == 200
    risk_data = risk_res.json()
    assert risk_data["is_at_risk"] is True
    assert risk_data["health_score"] < 100
    assert len(risk_data["risks"]) >= 1
    assert risk_data["risks"][0]["risk_type"] == "CAPACITY_OVERLOAD"

    # 4. Confirm risk event was persisted to append-only risk log
    list_risks_res = await client.get(f"/api/v1/projects/{project_id}/risks")
    assert list_risks_res.status_code == 200
    recorded_risks = list_risks_res.json()
    assert len(recorded_risks) >= 1
    assert recorded_risks[0]["risk_type"] == "CAPACITY_OVERLOAD"

    # 5. Propose Replan via POST /replan/propose
    replan_res = await client.post(f"/api/v1/projects/{project_id}/replan/propose")
    assert replan_res.status_code == 200
    replan_data = replan_res.json()
    assert replan_data["baseline_version"] == 1
    assert replan_data["proposed_version"] == 2
    assert replan_data["resolved_risks_count"] >= 1
    assert len(replan_data["mitigation_notes"]) > 0

    # 6. Verify active plan in DB is still Version 1 (Rule 4: Approval required)
    active_res = await client.get(f"/api/v1/projects/{project_id}/plans/active")
    assert active_res.status_code == 200
    assert active_res.json()["version"] == 1
