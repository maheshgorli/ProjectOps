"""Integration tests for History, Decisions, and Risk Events API endpoints."""

import httpx
import pytest


@pytest.mark.asyncio
async def test_history_decisions_and_risks_api(client: httpx.AsyncClient):
    # 1. Create Project
    p_res = await client.post("/api/v1/projects", json={"name": "History API Project"})
    assert p_res.status_code == 201
    project_id = p_res.json()["id"]

    # 2. Record Progress Event
    prog_res = await client.post(
        f"/api/v1/projects/{project_id}/history/progress",
        json={
            "task_id": "TASK-101",
            "new_status": "IN_PROGRESS",
            "previous_status": "TODO",
            "evidence_notes": "PR #42 opened on GitHub",
            "recorded_by": "github-webhook-worker",
        },
    )
    assert prog_res.status_code == 201
    prog_data = prog_res.json()
    assert prog_data["task_id"] == "TASK-101"
    assert prog_data["new_status"] == "IN_PROGRESS"

    # Query Progress Events
    list_prog_res = await client.get(
        f"/api/v1/projects/{project_id}/history/progress",
        params={"task_id": "TASK-101"},
    )
    assert list_prog_res.status_code == 200
    assert len(list_prog_res.json()) == 1

    # 3. Record Governance Decision
    dec_res = await client.post(
        f"/api/v1/projects/{project_id}/decisions",
        json={
            "decision_type": "REPLAN_APPROVAL",
            "summary": "Approved shifting milestone 1 week forward",
            "rationale": "Key dependency delayed by upstream provider",
            "decided_by": "engineering_manager_bob",
        },
    )
    assert dec_res.status_code == 201
    dec_data = dec_res.json()
    assert dec_data["decision_type"] == "REPLAN_APPROVAL"

    list_dec_res = await client.get(f"/api/v1/projects/{project_id}/decisions")
    assert list_dec_res.status_code == 200
    assert len(list_dec_res.json()) == 1

    # 4. Record Risk Event
    risk_res = await client.post(
        f"/api/v1/projects/{project_id}/risks",
        json={
            "risk_type": "CAPACITY_BOTTLENECK",
            "severity": "CRITICAL",
            "description": "Lead engineer workload exceeds 12h/day on Thursday",
            "payload_json": '{"member_id": "M1", "peak_hours": 12.0}',
        },
    )
    assert risk_res.status_code == 201
    risk_data = risk_res.json()
    assert risk_data["severity"] == "CRITICAL"

    list_risks_res = await client.get(
        f"/api/v1/projects/{project_id}/risks",
        params={"min_severity": "CRITICAL"},
    )
    assert list_risks_res.status_code == 200
    assert len(list_risks_res.json()) == 1
