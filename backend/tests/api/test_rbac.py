"""RBAC role-based authorization tests: Owner vs Member permissions."""

from uuid import uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.security import create_access_token, hash_password
from backend.app.main import app
from backend.app.models.auth import ProjectMembershipORM, UserORM


@pytest.mark.asyncio
async def test_owner_vs_member_permissions(
    auth_client: httpx.AsyncClient,
    test_session: AsyncSession,
):
    # 1. Owner creates a project
    p_res = await auth_client.post("/api/v1/projects", json={"name": "RBAC Test Project"})
    assert p_res.status_code == 201
    project_id = p_res.json()["id"]

    # 2. Create a member user and add them to project_memberships with role='member'
    member_user = UserORM(
        id=str(uuid4()),
        email="teammember@example.com",
        display_name="Team Member",
        password_hash=hash_password("Password123!"),
        is_active=True,
    )
    test_session.add(member_user)
    await test_session.commit()

    membership = ProjectMembershipORM(
        id=str(uuid4()),
        project_id=project_id,
        user_id=member_user.id,
        role="member",
    )
    test_session.add(membership)
    await test_session.commit()

    # Create an authenticated client for member_user
    member_token = create_access_token(member_user.id)
    transport = httpx.ASGITransport(app=app)
    member_client = httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {member_token}"},
    )

    # 3. Read endpoints: member can access project details, tasks, and schedule
    res_details = await member_client.get(f"/api/v1/projects/{project_id}")
    assert res_details.status_code == 200

    # 4. Plan creation: Member cannot create a plan (Owner only -> 403)
    plan_payload = {
        "name": "Draft Plan",
        "tasks": [{"id": "T1", "title": "Setup", "estimated_hours": 8.0}],
        "dependencies": [],
    }
    member_plan_res = await member_client.post(
        f"/api/v1/projects/{project_id}/plans", json=plan_payload
    )
    assert member_plan_res.status_code == 403
    assert "owner" in member_plan_res.json()["detail"].lower()

    # Owner creates the plan snapshot (version 1)
    owner_plan_res = await auth_client.post(
        f"/api/v1/projects/{project_id}/plans", json=plan_payload
    )
    assert owner_plan_res.status_code == 201
    assert owner_plan_res.json()["version"] == 1

    # 5. Plan activation: Member cannot activate the initial plan (403)
    member_act_res = await member_client.post(
        f"/api/v1/projects/{project_id}/plans/1/activate",
        json={"rationale": "Member attempting activation"},
    )
    assert member_act_res.status_code == 403
    assert "owner" in member_act_res.json()["detail"].lower()

    # Owner activates the plan -> 200
    owner_act_res = await auth_client.post(
        f"/api/v1/projects/{project_id}/plans/1/activate",
        json={"rationale": "Owner approved baseline"},
    )
    assert owner_act_res.status_code == 200

    # 6. Task status updates: Member is permitted to update task status -> 200
    member_task_update = await member_client.patch(
        f"/api/v1/projects/{project_id}/tasks/T1/status",
        json={"status": "IN_PROGRESS", "evidence_notes": "Member started work"},
    )
    assert member_task_update.status_code == 200
    assert member_task_update.json()["status"] == "IN_PROGRESS"
    assert member_task_update.json()["updated_by"] == member_user.id

    # 7. Agent-loop step: Member is permitted to trigger agent-loop step -> 200
    member_loop_res = await member_client.post(f"/api/v1/projects/{project_id}/agent-loop/step")
    assert member_loop_res.status_code == 200

    # 8. Replan proposals: Generate proposal (member can trigger proposal generation)
    prop_res = await member_client.post(f"/api/v1/projects/{project_id}/replan/propose")
    assert prop_res.status_code == 200
    proposal_id = prop_res.json()["proposal_id"]

    # Member cannot approve replan proposal -> 403
    member_approve_res = await member_client.post(
        f"/api/v1/projects/{project_id}/replan/approve",
        json={"proposal_id": proposal_id, "decision_rationale": "Member approving"},
    )
    assert member_approve_res.status_code == 403
    assert "owner" in member_approve_res.json()["detail"].lower()

    # Member cannot reject replan proposal -> 403
    member_reject_res = await member_client.post(
        f"/api/v1/projects/{project_id}/replan/reject",
        json={"proposal_id": proposal_id, "rationale": "Member rejecting"},
    )
    assert member_reject_res.status_code == 403
    assert "owner" in member_reject_res.json()["detail"].lower()

    # Owner can approve proposal -> 200
    owner_approve_res = await auth_client.post(
        f"/api/v1/projects/{project_id}/replan/approve",
        json={"proposal_id": proposal_id, "decision_rationale": "Owner approved"},
    )
    assert owner_approve_res.status_code == 200
    assert owner_approve_res.json()["status"] == "APPROVED"
