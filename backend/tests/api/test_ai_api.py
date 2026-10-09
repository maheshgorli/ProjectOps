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


@pytest.mark.asyncio
async def test_ai_info_endpoint(client: httpx.AsyncClient):
    res = await client.get("/api/v1/ai/info")
    assert res.status_code == 200
    data = res.json()
    assert data["provider"] == "mock"
    assert data["is_mock"] is True
    assert "model" in data


@pytest.mark.asyncio
async def test_decompose_goal_project_alias(client: httpx.AsyncClient):
    # Ensure project-scoped URL also works (fixing P0-3)
    p_res = await client.post("/api/v1/projects", json={"name": "Alias Test Project"})
    assert p_res.status_code == 201
    project_id = p_res.json()["id"]

    payload = {
        "goal": "Build responsive billing and invoicing checkout portal",
        "context": "Needs Stripe integration",
    }
    res = await client.post(f"/api/v1/projects/{project_id}/ai/decompose-goal", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["goal"] == payload["goal"]
    assert len(data["tasks"]) >= 1


@pytest.mark.asyncio
async def test_claude_provider_requires_api_key_when_configured(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    from backend.app.core.config import settings
    from backend.app.llm.provider import get_llm_provider

    monkeypatch.setattr(settings, "llm_provider", "claude")
    monkeypatch.setattr(settings, "anthropic_api_key", None)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is not configured"):
        get_llm_provider()

    # Calling endpoint returns 503 Service Unavailable with clear detail
    res = await client.post("/api/v1/ai/decompose-goal", json={"goal": "Valid project goal"})
    assert res.status_code == 503
    assert "ANTHROPIC_API_KEY is not configured" in res.json()["detail"]
