"""Integration tests for AI Goal Decomposition and Replan Explanation API endpoints."""

import httpx
import pytest


@pytest.mark.asyncio
async def test_decompose_goal_api(auth_client: httpx.AsyncClient):
    payload = {
        "goal": "Build responsive billing and invoicing checkout portal",
        "context": "Needs Stripe integration and PDF invoice generation",
    }
    res = await auth_client.post("/api/v1/ai/decompose-goal", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["goal"] == payload["goal"]
    assert len(data["tasks"]) >= 2
    assert len(data["dependencies"]) >= 1
    assert data["estimated_total_hours"] > 0
    assert data["is_valid_dag"] is True


@pytest.mark.asyncio
async def test_explain_replan_api(auth_client: httpx.AsyncClient):
    # Create project first
    p_res = await auth_client.post("/api/v1/projects", json={"name": "AI Explainer Project"})
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
    res = await auth_client.post(
        f"/api/v1/projects/{project_id}/replan/explain",
        json=replan_payload,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["project_id"] == project_id
    assert len(data["explanation"]) > 0


@pytest.mark.asyncio
async def test_ai_info_endpoint(auth_client: httpx.AsyncClient):
    res = await auth_client.get("/api/v1/ai/info")
    assert res.status_code == 200
    data = res.json()
    assert data["provider"] == "mock"
    assert data["is_mock"] is True
    assert "model" in data


@pytest.mark.asyncio
async def test_decompose_goal_project_alias(auth_client: httpx.AsyncClient):
    # Ensure project-scoped URL also works (fixing P0-3)
    p_res = await auth_client.post("/api/v1/projects", json={"name": "Alias Test Project"})
    assert p_res.status_code == 201
    project_id = p_res.json()["id"]

    payload = {
        "goal": "Build responsive billing and invoicing checkout portal",
        "context": "Needs Stripe integration",
    }
    res = await auth_client.post(f"/api/v1/projects/{project_id}/ai/decompose-goal", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["goal"] == payload["goal"]
    assert len(data["tasks"]) >= 1


@pytest.mark.asyncio
async def test_claude_provider_requires_api_key_when_configured(
    auth_client: httpx.AsyncClient,
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
    res = await auth_client.post("/api/v1/ai/decompose-goal", json={"goal": "Valid project goal"})
    assert res.status_code == 503
    assert "ANTHROPIC_API_KEY is not configured" in res.json()["detail"]


@pytest.mark.asyncio
async def test_grok_provider_requires_api_key_when_configured(
    auth_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    from backend.app.core.config import settings
    from backend.app.llm.provider import get_llm_provider

    monkeypatch.setattr(settings, "llm_provider", "grok")
    monkeypatch.setattr(settings, "xai_api_key", None)
    monkeypatch.delenv("XAI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="XAI_API_KEY is not configured"):
        get_llm_provider()

    res = await auth_client.post("/api/v1/ai/decompose-goal", json={"goal": "Valid project goal"})
    assert res.status_code == 503
    assert "XAI_API_KEY is not configured" in res.json()["detail"]


@pytest.mark.asyncio
async def test_ai_info_endpoint_grok(
    auth_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    from backend.app.core.config import settings

    monkeypatch.setattr(settings, "llm_provider", "grok")
    monkeypatch.setattr(settings, "xai_model", "grok-2-latest")

    res = await auth_client.get("/api/v1/ai/info")
    assert res.status_code == 200
    data = res.json()
    assert data["provider"] == "grok"
    assert data["model"] == "grok-2-latest"
    assert data["is_mock"] is False


@pytest.mark.asyncio
async def test_decompose_goal_with_grok_provider(
    auth_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    import json

    from backend.app.llm.provider import GrokProvider

    mock_goal_response = {
        "tasks": [
            {
                "id": "T1",
                "title": "Setup repository and CI/CD",
                "description": "Initialize repo and GitHub workflows",
                "estimated_hours": 8.0,
            },
            {
                "id": "T2",
                "title": "Build Core Engine",
                "description": "Implement core algorithm",
                "estimated_hours": 16.0,
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

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(mock_goal_response),
                        }
                    }
                ]
            },
        )

    mock_client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://api.x.ai/v1",
    )
    mock_provider = GrokProvider(api_key="mock-xai-key", http_client=mock_client)
    monkeypatch.setattr("backend.app.api.v1.ai.get_llm_provider", lambda: mock_provider)

    res = await auth_client.post(
        "/api/v1/ai/decompose-goal",
        json={"goal": "Build NextGen Delivery System", "context": "Needs real-time GPS tracking"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["tasks"]) == 2
    assert len(data["dependencies"]) == 1
    assert data["estimated_total_hours"] == 24.0
    assert data["is_valid_dag"] is True


@pytest.mark.asyncio
async def test_explain_replan_with_grok_provider(
    auth_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    from backend.app.llm.provider import GrokProvider

    p_res = await auth_client.post("/api/v1/projects", json={"name": "Grok Replan Project"})
    assert p_res.status_code == 201
    project_id = p_res.json()["id"]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Grok Replan Explanation: Schedule stabilized via critical path realignment.",
                        }
                    }
                ]
            },
        )

    mock_client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://api.x.ai/v1",
    )
    mock_provider = GrokProvider(api_key="mock-xai-key", http_client=mock_client)
    monkeypatch.setattr("backend.app.api.v1.ai.get_llm_provider", lambda: mock_provider)

    replan_payload = {
        "baseline_version": 1,
        "proposed_version": 2,
        "baseline_finish_date": "2026-10-15",
        "proposed_finish_date": "2026-10-22",
        "finish_date_delta_days": 5,
        "mitigation_notes": ["Added backend buffer"],
    }
    res = await auth_client.post(
        f"/api/v1/projects/{project_id}/replan/explain",
        json=replan_payload,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["project_id"] == project_id
    assert "Schedule stabilized" in data["explanation"]
