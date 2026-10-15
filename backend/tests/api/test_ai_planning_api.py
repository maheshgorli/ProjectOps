"""Integration tests for AI Plan Generation with Groq and Document Parser."""

import httpx
import pytest


@pytest.mark.asyncio
async def test_generate_plan_multipart_with_documents(auth_client: httpx.AsyncClient):
    # 1. Create a project
    p_res = await auth_client.post(
        "/api/v1/projects",
        json={"name": "Cloud Logistics Platform", "description": "Microservices delivery stack"},
    )
    assert p_res.status_code == 201
    project_id = p_res.json()["id"]

    # 2. Call generate-plan with multipart form data + attached requirements document
    doc_content = b"# Architecture Specification\nNeed auth, rate limiting, and order queue."
    files = [("files", ("spec.md", doc_content, "text/markdown"))]
    data = {
        "requirements": "Build resilient logistics platform with order routing",
        "github_url": "https://github.com/org/logistics",
        "save_as_draft": "true",
    }

    res = await auth_client.post(
        f"/api/v1/projects/{project_id}/ai/generate-plan",
        data=data,
        files=files,
    )
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["project_id"] == project_id
    assert res_data["is_valid_dag"] is True
    assert len(res_data["tasks"]) >= 2
    assert "spec.md" in res_data["documents_processed"]
    assert res_data["version"] is not None
    assert res_data["plan_id"] is not None
    assert res_data["status"] == "DRAFT"

    # 3. Verify the generated plan snapshot was persisted in DB
    version = res_data["version"]
    plan_res = await auth_client.get(f"/api/v1/projects/{project_id}/plans/{version}")
    assert plan_res.status_code == 200
    plan_data = plan_res.json()
    assert plan_data["id"] == res_data["plan_id"]
    assert len(plan_data["tasks"]) == len(res_data["tasks"])


@pytest.mark.asyncio
async def test_generate_plan_json_endpoint(auth_client: httpx.AsyncClient):
    p_res = await auth_client.post(
        "/api/v1/projects",
        json={"name": "Fintech Core Gateway", "description": "High-throughput ledger"},
    )
    assert p_res.status_code == 201
    project_id = p_res.json()["id"]

    json_payload = {
        "requirements": "Ledger double-entry accounting with audit log",
        "github_url": "",
        "documents": [
            {
                "filename": "ledger_spec.txt",
                "content": "Double entry ledger requirements: ACID compliance, idempotency.",
                "file_type": "text",
            }
        ],
        "save_as_draft": True,
    }

    res = await auth_client.post(
        f"/api/v1/projects/{project_id}/ai/generate-plan-json",
        json=json_payload,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["project_id"] == project_id
    assert len(data["tasks"]) >= 1
    assert "ledger_spec.txt" in data["documents_processed"]


@pytest.mark.asyncio
async def test_generate_plan_unsupported_file_fails(auth_client: httpx.AsyncClient):
    p_res = await auth_client.post(
        "/api/v1/projects",
        json={"name": "Test Fail Project"},
    )
    assert p_res.status_code == 201
    project_id = p_res.json()["id"]

    files = [("files", ("bad.exe", b"\x4d\x5a", "application/octet-stream"))]
    res = await auth_client.post(
        f"/api/v1/projects/{project_id}/ai/generate-plan",
        data={"requirements": "Some requirements"},
        files=files,
    )
    assert res.status_code == 422
    assert "Unsupported document format" in res.json()["detail"]


@pytest.mark.asyncio
async def test_generate_plan_nonexistent_project_404(auth_client: httpx.AsyncClient):
    res = await auth_client.post(
        "/api/v1/projects/nonexistent-uuid/ai/generate-plan",
        data={"requirements": "Some requirements"},
    )
    assert res.status_code == 404
