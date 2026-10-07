"""Integration tests for Projects and Members API endpoints."""

import httpx
import pytest


@pytest.mark.asyncio
async def test_create_and_get_project(client: httpx.AsyncClient):
    # 1. Create Project
    res = await client.post(
        "/api/v1/projects",
        json={"name": "Project Artemis", "description": "Space exploration portal"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Project Artemis"
    project_id = data["id"]

    # 2. Add Member
    member_res = await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"name": "Commander Shepard", "role": "lead", "daily_capacity_hours": 8.0},
    )
    assert member_res.status_code == 201
    member_data = member_res.json()
    assert member_data["name"] == "Commander Shepard"
    assert member_data["project_id"] == project_id

    # 3. Get Project details
    get_res = await client.get(f"/api/v1/projects/{project_id}")
    assert get_res.status_code == 200
    proj_details = get_res.json()
    assert len(proj_details["members"]) == 1
    assert proj_details["members"][0]["name"] == "Commander Shepard"

    # 4. List Projects
    list_res = await client.get("/api/v1/projects")
    assert list_res.status_code == 200
    assert any(p["id"] == project_id for p in list_res.json())


@pytest.mark.asyncio
async def test_project_not_found(client: httpx.AsyncClient):
    res = await client.get("/api/v1/projects/non-existent-id")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()
