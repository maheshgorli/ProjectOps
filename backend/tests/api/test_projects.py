"""Integration tests for Projects and Members API endpoints."""

import httpx
import pytest


@pytest.mark.asyncio
async def test_create_and_get_project(auth_client: httpx.AsyncClient):
    # 1. Create Project
    res = await auth_client.post(
        "/api/v1/projects",
        json={"name": "Project Artemis", "description": "Space exploration portal"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Project Artemis"
    project_id = data["id"]

    # 2. Add Member
    member_res = await auth_client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"name": "Commander Shepard", "role": "lead", "daily_capacity_hours": 8.0},
    )
    assert member_res.status_code == 201
    member_data = member_res.json()
    assert member_data["name"] == "Commander Shepard"
    assert member_data["project_id"] == project_id

    # 3. Get Project details
    get_res = await auth_client.get(f"/api/v1/projects/{project_id}")
    assert get_res.status_code == 200
    proj_details = get_res.json()
    assert len(proj_details["members"]) == 1
    assert proj_details["members"][0]["name"] == "Commander Shepard"

    # 4. List Projects
    list_res = await auth_client.get("/api/v1/projects")
    assert list_res.status_code == 200
    assert any(p["id"] == project_id for p in list_res.json())


@pytest.mark.asyncio
async def test_project_not_found(auth_client: httpx.AsyncClient):
    res = await auth_client.get("/api/v1/projects/non-existent-id")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_user_scoped_project_isolation(
    auth_client: httpx.AsyncClient,
    other_client: httpx.AsyncClient,
):
    # 1. User A creates a project
    res = await auth_client.post(
        "/api/v1/projects",
        json={"name": "Confidential Alpha", "description": "Owner only access"},
    )
    assert res.status_code == 201
    project_id = res.json()["id"]

    # 2. User A sees it in their projects list
    user_a_list = await auth_client.get("/api/v1/projects")
    assert user_a_list.status_code == 200
    assert any(p["id"] == project_id for p in user_a_list.json())

    # 3. User B (stranger) does NOT see it in their projects list
    user_b_list = await other_client.get("/api/v1/projects")
    assert user_b_list.status_code == 200
    assert not any(p["id"] == project_id for p in user_b_list.json())

    # 4. User B cannot access the project directly (returns 404 to avoid leaking existence)
    b_access = await other_client.get(f"/api/v1/projects/{project_id}")
    assert b_access.status_code == 404


@pytest.mark.asyncio
async def test_project_active_plan_metadata(auth_client: httpx.AsyncClient):
    # 1. Create project with no plan initially
    p_res = await auth_client.post(
        "/api/v1/projects",
        json={"name": "Metadata Project", "description": "Testing plan metadata"},
    )
    assert p_res.status_code == 201
    p_data = p_res.json()
    assert p_data["task_count"] == 0
    assert p_data["active_plan_version"] is None
    project_id = p_data["id"]

    # 2. Post a plan snapshot with 2 tasks
    plan_payload = {
        "name": "Phase 1 Baseline",
        "target_completion_date": "2026-11-01",
        "tasks": [
            {"id": "T1", "title": "Database schema", "estimated_hours": 6.0},
            {"id": "T2", "title": "API implementation", "estimated_hours": 12.0},
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
    plan_res = await auth_client.post(
        f"/api/v1/projects/{project_id}/plans",
        json=plan_payload,
    )
    assert plan_res.status_code == 201

    # 3. Activate plan version 1
    act_res = await auth_client.post(
        f"/api/v1/projects/{project_id}/plans/1/activate",
        json={"rationale": "Initial plan sign-off"},
    )
    assert act_res.status_code == 200

    # 4. List projects & get project both show updated plan metadata
    list_res = await auth_client.get("/api/v1/projects")
    assert list_res.status_code == 200
    matched = next((p for p in list_res.json() if p["id"] == project_id), None)
    assert matched is not None
    assert matched["task_count"] == 2
    assert matched["active_plan_version"] == 1
    assert matched["target_completion_date"] == "2026-11-01"

    get_res = await auth_client.get(f"/api/v1/projects/{project_id}")
    assert get_res.status_code == 200
    assert get_res.json()["task_count"] == 2
    assert get_res.json()["active_plan_version"] == 1

