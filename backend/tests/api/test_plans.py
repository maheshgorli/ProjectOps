"""Integration tests for Plan snapshots and versioning API endpoints."""

import httpx
import pytest


@pytest.mark.asyncio
async def test_create_plan_and_versioning(client: httpx.AsyncClient):
    # 1. Create Project
    p_res = await client.post("/api/v1/projects", json={"name": "Plan Test Project"})
    assert p_res.status_code == 201
    project_id = p_res.json()["id"]

    # 2. Post Plan Version 1
    plan_payload_v1 = {
        "version": 1,
        "name": "Initial Baseline",
        "tasks": [
            {"id": "T1", "title": "Setup repo", "estimated_hours": 8.0, "status": "COMPLETED"},
            {"id": "T2", "title": "Implement core", "estimated_hours": 16.0, "status": "TODO"},
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
    res_v1 = await client.post(f"/api/v1/projects/{project_id}/plans", json=plan_payload_v1)
    assert res_v1.status_code == 201
    data_v1 = res_v1.json()
    assert data_v1["version"] == 1
    assert len(data_v1["tasks"]) == 2

    # 3. Get Active Plan
    active_res = await client.get(f"/api/v1/projects/{project_id}/plans/active")
    assert active_res.status_code == 200
    assert active_res.json()["version"] == 1

    # 4. Attempt to overwrite Version 1 -> Expect HTTP 409 Conflict
    conflict_res = await client.post(f"/api/v1/projects/{project_id}/plans", json=plan_payload_v1)
    assert conflict_res.status_code == 409
    assert "already exists" in conflict_res.json()["detail"].lower()

    # 5. Post Version 2 (Valid replan snapshot)
    plan_payload_v2 = {
        "version": 2,
        "name": "Replan with testing",
        "tasks": [
            {"id": "T1", "title": "Setup repo", "estimated_hours": 8.0, "status": "COMPLETED"},
            {
                "id": "T2",
                "title": "Implement core",
                "estimated_hours": 16.0,
                "status": "IN_PROGRESS",
            },
            {"id": "T3", "title": "Automated tests", "estimated_hours": 12.0, "status": "TODO"},
        ],
        "dependencies": [
            {
                "predecessor_id": "T1",
                "successor_id": "T2",
                "dep_type": "FINISH_TO_START",
                "lag_days": 0,
            },
            {
                "predecessor_id": "T2",
                "successor_id": "T3",
                "dep_type": "FINISH_TO_START",
                "lag_days": 0,
            },
        ],
    }
    res_v2 = await client.post(f"/api/v1/projects/{project_id}/plans", json=plan_payload_v2)
    assert res_v2.status_code == 201
    assert res_v2.json()["version"] == 2

    # 6. Check version list and historical retrieval
    ver_res = await client.get(f"/api/v1/projects/{project_id}/plans/versions")
    assert ver_res.status_code == 200
    assert ver_res.json()["versions"] == [1, 2]
    assert ver_res.json()["active_version"] == 2

    hist_res = await client.get(f"/api/v1/projects/{project_id}/plans/1")
    assert hist_res.status_code == 200
    assert len(hist_res.json()["tasks"]) == 2  # Untouched historical snapshot!


@pytest.mark.asyncio
async def test_create_plan_with_cycle_fails_with_422(client: httpx.AsyncClient):
    p_res = await client.post("/api/v1/projects", json={"name": "Cycle Project"})
    project_id = p_res.json()["id"]

    cycle_payload = {
        "version": 1,
        "name": "Circular Plan",
        "tasks": [
            {"id": "A", "title": "Task A", "estimated_hours": 8.0},
            {"id": "B", "title": "Task B", "estimated_hours": 8.0},
        ],
        "dependencies": [
            {"predecessor_id": "A", "successor_id": "B"},
            {"predecessor_id": "B", "successor_id": "A"},  # Circular dependency!
        ],
    }
    res = await client.post(f"/api/v1/projects/{project_id}/plans", json=cycle_payload)
    assert res.status_code == 422
    err_body = res.json()["detail"]
    assert "cycle" in err_body
    assert err_body["cycle"] in (["A", "B", "A"], ["B", "A", "B"])
