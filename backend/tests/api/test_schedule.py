"""Integration tests for CPM Schedule and What-If Simulation API endpoints."""

import httpx
import pytest


@pytest.mark.asyncio
async def test_get_schedule_and_simulation(client: httpx.AsyncClient):
    # 1. Create project and member
    p_res = await client.post("/api/v1/projects", json={"name": "Scheduling Project"})
    project_id = p_res.json()["id"]

    m_res = await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"name": "Dev Alice", "role": "engineer", "daily_capacity_hours": 8.0},
    )
    member_id = m_res.json()["id"]

    # 2. Create baseline plan (2 tasks: T1=8h, T2=8h)
    plan_payload = {
        "version": 1,
        "name": "Baseline Plan",
        "tasks": [
            {
                "id": "T1",
                "title": "Foundation",
                "estimated_hours": 8.0,
                "assigned_to_id": member_id,
            },
            {
                "id": "T2",
                "title": "UI Integration",
                "estimated_hours": 8.0,
                "assigned_to_id": member_id,
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
    await client.post(f"/api/v1/projects/{project_id}/plans", json=plan_payload)

    # 3. Request Schedule on Active Plan
    sched_res = await client.get(
        f"/api/v1/projects/{project_id}/schedule",
        params={"start_date": "2026-10-05"},
    )
    assert sched_res.status_code == 200
    sched_data = sched_res.json()
    assert sched_data["project_start_date"] == "2026-10-05"
    assert sched_data["critical_path"] == ["T1", "T2"]
    assert sched_data["is_feasible"] is True

    # 4. Simulate What-If scenario: Increase T2 estimate from 8h (1 day) to 32h (4 days)
    sim_payload = {
        "candidate_tasks": [
            {
                "id": "T1",
                "title": "Foundation",
                "estimated_hours": 8.0,
                "assigned_to_id": member_id,
            },
            {
                "id": "T2",
                "title": "UI Integration",
                "estimated_hours": 32.0,
                "assigned_to_id": member_id,
            },
        ],
        "candidate_dependencies": [
            {
                "predecessor_id": "T1",
                "successor_id": "T2",
                "dep_type": "FINISH_TO_START",
                "lag_days": 0,
            }
        ],
        "start_date": "2026-10-05",
    }
    sim_res = await client.post(
        f"/api/v1/projects/{project_id}/schedule/simulate",
        json=sim_payload,
    )
    assert sim_res.status_code == 200
    sim_data = sim_res.json()

    # Baseline was 2 days finish (Tuesday 2026-10-06).
    # Simulated is 1 + 4 = 5 working days (Friday 2026-10-09).
    # Delta should be +3 working days!
    assert sim_data["finish_date_delta_working_days"] == 3
    assert sim_data["simulated_finish_date"] > sim_data["baseline_finish_date"]

    # 5. Confirm DB was NOT changed by simulation
    verify_res = await client.get(
        f"/api/v1/projects/{project_id}/schedule",
        params={"start_date": "2026-10-05"},
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["project_finish_date"] == sched_data["project_finish_date"]
