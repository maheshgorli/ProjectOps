"""Integration tests for AI Goal Decomposition and Replan Explanation API endpoints."""

import httpx
import pytest


@pytest.mark.asyncio
async def test_decompose_goal_api(client: httpx.AsyncClient):
    payload = {
        "goal": "Build responsive billing and invoicing checkout portal",
        "context": "Needs Stripe integration and PDF invoice generation",
    }
    res = await client.post("/api/v1/ai/decompose-goal", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["goal"] == payload["goal"]
    assert len(data["tasks"]) >= 2
    assert len(data["dependencies"]) >= 1
    assert data["estimated_total_hours"] > 0
    assert data["is_valid_dag"] is True


@pytest.mark.asyncio
async def test_explain_replan_api(client: httpx.AsyncClient):
    # Create project first
    p_res = await client.post("/api/v1/projects", json={"name": "AI Explainer Project"})
    assert p_res.status_code == 201
    project_id = p_res.json()["id"]

    replan_payload = {
        "baseline_version": 1,
        "proposed_version": 2,
        "baseline_finish_date": "2026-10-15",
        "proposed_finish_date": "2026-10-20",
        "finish_date_delta_days": 3,
        "mitigation_notes": ["Shifted deadline due to critical path delays"],
    }
    res = await client.post(
        f"/api/v1/projects/{project_id}/replan/explain",
        json=replan_payload,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["project_id"] == project_id
    assert len(data["explanation"]) > 0
