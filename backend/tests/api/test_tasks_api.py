"""Integration tests for Task Execution State API and lifecycle transitions."""

import httpx
import pytest


@pytest.mark.asyncio
async def test_list_tasks_empty(client: httpx.AsyncClient):
    # Create project without a plan
    p_res = await client.post("/api/v1/projects", json={"name": "No Plan Project"})
    assert p_res.status_code == 201
    project_id = p_res.json()["id"]

    # List tasks should return empty list
    res = await client.get(f"/api/v1/projects/{project_id}/tasks")
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.asyncio
async def test_get_and_list_tasks_merged(client: httpx.AsyncClient):
    # 1. Create project & member
    p_res = await client.post("/api/v1/projects", json={"name": "Task Execution Project"})
    assert p_res.status_code == 201
    project_id = p_res.json()["id"]

    m_res = await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"name": "Alice Bob", "role": "engineer", "daily_capacity_hours": 8.0},
    )
    assert m_res.status_code == 201
    member_id = m_res.json()["id"]

    # 2. Create baseline plan with past due date on T1 and future due date on T2
    plan_payload = {
        "version": 1,
        "name": "Sprint 1 Baseline",
        "tasks": [
            {
                "id": "T1",
                "title": "Database Schema",
                "description": "Create Postgres tables",
                "estimated_hours": 8.0,
                "status": "TODO",
                "assigned_to_id": member_id,
                "start_date": "2026-01-05",
                "due_date": "2026-01-06",
            },
            {
                "id": "T2",
                "title": "API Routes",
                "description": "Implement FastAPI routes",
                "estimated_hours": 16.0,
                "status": "TODO",
                "assigned_to_id": member_id,
                "start_date": "2026-10-10",
                "due_date": "2026-10-15",
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
    create_plan_res = await client.post(f"/api/v1/projects/{project_id}/plans", json=plan_payload)
    assert create_plan_res.status_code == 201

    # 3. List tasks - verify merge
    tasks_res = await client.get(f"/api/v1/projects/{project_id}/tasks")
    assert tasks_res.status_code == 200
    tasks = tasks_res.json()
    assert len(tasks) == 2

    t1 = next(t for t in tasks if t["id"] == "T1")
    assert t1["title"] == "Database Schema"
    assert t1["status"] == "TODO"
    assert t1["is_overdue"] is True  # Due date 2026-01-06 is in past
    assert t1["dependencies"] == []

    t2 = next(t for t in tasks if t["id"] == "T2")
    assert t2["title"] == "API Routes"
    assert t2["status"] == "TODO"
    assert t2["dependencies"] == ["T1"]

    # 4. Get single task
    single_res = await client.get(f"/api/v1/projects/{project_id}/tasks/T1")
    assert single_res.status_code == 200
    assert single_res.json()["id"] == "T1"

    # 5. Non-existent task returns 404
    missing_res = await client.get(f"/api/v1/projects/{project_id}/tasks/T999")
    assert missing_res.status_code == 404


@pytest.mark.asyncio
async def test_task_status_transitions_and_audit_log(client: httpx.AsyncClient):
    # 1. Setup project and plan
    p_res = await client.post("/api/v1/projects", json={"name": "Lifecycle Project"})
    project_id = p_res.json()["id"]

    plan_payload = {
        "version": 1,
        "name": "Lifecycle Plan",
        "tasks": [
            {
                "id": "T-10",
                "title": "Task Lifecycle Demo",
                "estimated_hours": 8.0,
                "status": "TODO",
                "start_date": "2026-01-01",
                "due_date": "2026-01-02",
            }
        ],
        "dependencies": [],
    }
    await client.post(f"/api/v1/projects/{project_id}/plans", json=plan_payload)

    # 2. Invalid status value -> 422
    bad_val_res = await client.patch(
        f"/api/v1/projects/{project_id}/tasks/T-10/status",
        json={"status": "INVALID_STATUS"},
    )
    assert bad_val_res.status_code == 422
    assert "Invalid task status" in bad_val_res.json()["detail"]

    # 3. Disallowed transition: TODO -> COMPLETED directly -> 422
    jump_res = await client.patch(
        f"/api/v1/projects/{project_id}/tasks/T-10/status",
        json={"status": "COMPLETED"},
    )
    assert jump_res.status_code == 422
    assert "Illegal task status transition" in jump_res.json()["detail"]

    # 4. Valid transition: TODO -> IN_PROGRESS
    start_res = await client.patch(
        f"/api/v1/projects/{project_id}/tasks/T-10/status",
        json={
            "status": "IN_PROGRESS",
            "actual_start": "2026-10-09",
            "actual_hours": 4.0,
            "percent_complete": 50,
            "evidence_notes": "Started feature branch implementation",
            "updated_by": "alice",
        },
    )
    assert start_res.status_code == 200
    t_start = start_res.json()
    assert t_start["status"] == "IN_PROGRESS"
    assert t_start["actual_start"] == "2026-10-09"
    assert t_start["actual_hours"] == 4.0
    assert t_start["percent_complete"] == 50
    assert t_start["updated_by"] == "alice"
    assert t_start["is_overdue"] is True  # Still due 2026-01-02 and not completed

    # 5. Valid transition: IN_PROGRESS -> BLOCKED
    block_res = await client.patch(
        f"/api/v1/projects/{project_id}/tasks/T-10/status",
        json={
            "status": "BLOCKED",
            "blocked_reason": "Waiting on upstream database credentials",
            "evidence_notes": "Blocked on ops ticket #123",
            "updated_by": "alice",
        },
    )
    assert block_res.status_code == 200
    t_block = block_res.json()
    assert t_block["status"] == "BLOCKED"
    assert t_block["blocked_reason"] == "Waiting on upstream database credentials"

    # 6. Valid transition: BLOCKED -> IN_PROGRESS
    unblock_res = await client.patch(
        f"/api/v1/projects/{project_id}/tasks/T-10/status",
        json={
            "status": "IN_PROGRESS",
            "evidence_notes": "Credentials received, resumed development",
            "updated_by": "alice",
        },
    )
    assert unblock_res.status_code == 200
    assert unblock_res.json()["status"] == "IN_PROGRESS"

    # 7. Valid transition: IN_PROGRESS -> COMPLETED
    complete_res = await client.patch(
        f"/api/v1/projects/{project_id}/tasks/T-10/status",
        json={
            "status": "COMPLETED",
            "actual_finish": "2026-10-09",
            "actual_hours": 8.0,
            "percent_complete": 100,
            "evidence_notes": "PR #99 merged to main",
            "updated_by": "alice",
        },
    )
    assert complete_res.status_code == 200
    t_comp = complete_res.json()
    assert t_comp["status"] == "COMPLETED"
    assert t_comp["actual_finish"] == "2026-10-09"
    assert t_comp["percent_complete"] == 100
    # Rule: Once COMPLETED, is_overdue is FALSE regardless of due date!
    assert t_comp["is_overdue"] is False

    # 8. Valid reopen: COMPLETED -> IN_PROGRESS (rework)
    reopen_res = await client.patch(
        f"/api/v1/projects/{project_id}/tasks/T-10/status",
        json={
            "status": "IN_PROGRESS",
            "evidence_notes": "QA found edge-case regression, reopening",
            "updated_by": "lead",
        },
    )
    assert reopen_res.status_code == 200
    assert reopen_res.json()["status"] == "IN_PROGRESS"

    # 9. Verify that each status update recorded an audit trail event in ProgressHistory (Rule 5)
    hist_res = await client.get(
        f"/api/v1/projects/{project_id}/history/progress",
        params={"task_id": "T-10"},
    )
    assert hist_res.status_code == 200
    events = hist_res.json()
    # Transitions logged:
    # 1. TODO -> IN_PROGRESS
    # 2. IN_PROGRESS -> BLOCKED
    # 3. BLOCKED -> IN_PROGRESS
    # 4. IN_PROGRESS -> COMPLETED
    # 5. COMPLETED -> IN_PROGRESS
    assert len(events) == 5
    transitions = [(e["previous_status"], e["new_status"]) for e in events]
    assert transitions == [
        ("TODO", "IN_PROGRESS"),
        ("IN_PROGRESS", "BLOCKED"),
        ("BLOCKED", "IN_PROGRESS"),
        ("IN_PROGRESS", "COMPLETED"),
        ("COMPLETED", "IN_PROGRESS"),
    ]


@pytest.mark.asyncio
async def test_execution_state_propagates_to_schedule_and_risks(client: httpx.AsyncClient):
    # 1. Create project, member, and plan
    p_res = await client.post("/api/v1/projects", json={"name": "Integration Propagation"})
    project_id = p_res.json()["id"]

    m_res = await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"name": "Dev Charlie", "role": "engineer", "daily_capacity_hours": 8.0},
    )
    member_id = m_res.json()["id"]

    plan_payload = {
        "version": 1,
        "name": "Propagation Plan",
        "tasks": [
            {
                "id": "T1",
                "title": "Backend API",
                "estimated_hours": 8.0,
                "status": "TODO",
                "assigned_to_id": member_id,
                "start_date": "2026-10-05",
                "due_date": "2026-10-05",
            },
            {
                "id": "T2",
                "title": "Frontend Client",
                "estimated_hours": 8.0,
                "status": "TODO",
                "assigned_to_id": member_id,
                "start_date": "2026-10-06",
                "due_date": "2026-10-06",
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

    # 2. Baseline plan is unblocked; verify schedule
    sched_res = await client.get(
        f"/api/v1/projects/{project_id}/schedule",
        params={"start_date": "2026-10-05"},
    )
    assert sched_res.status_code == 200
    sched_data = sched_res.json()
    assert sched_data["is_feasible"] is True

    # 3. Mark T1 as IN_PROGRESS then BLOCKED
    await client.patch(
        f"/api/v1/projects/{project_id}/tasks/T1/status",
        json={"status": "IN_PROGRESS", "evidence_notes": "Started"},
    )
    await client.patch(
        f"/api/v1/projects/{project_id}/tasks/T1/status",
        json={
            "status": "BLOCKED",
            "blocked_reason": "Blocked by 3rd-party outage",
            "evidence_notes": "Reported issue to vendor",
        },
    )

    # 4. Analyze risks: BLOCKED task with dependent successor triggers BLOCKED_CASCADE
    risks_res = await client.get(f"/api/v1/projects/{project_id}/risks/analyze")
    assert risks_res.status_code == 200
    risk_data = risks_res.json()
    risk_types = [r["risk_type"] for r in risk_data["risks"]]
    assert "BLOCKED_CASCADE" in risk_types
    cascade_risk = next(r for r in risk_data["risks"] if r["risk_type"] == "BLOCKED_CASCADE")
    assert "T1" in cascade_risk["affected_task_ids"]
    assert "T2" in cascade_risk["affected_task_ids"]

    # 5. Check schedule with runtime state
    sched_res_after = await client.get(
        f"/api/v1/projects/{project_id}/schedule",
        params={"start_date": "2026-10-05"},
    )
    assert sched_res_after.status_code == 200
    assert sched_res_after.json()["project_start_date"] == "2026-10-05"
