"""Authorization matrix test inspecting OpenAPI schema for all project routes.

Asserts:
- No token -> 401 Unauthorized
- Non-member token -> 404 Not Found (zero information leakage)
"""

import httpx
import pytest

from backend.app.main import app


def _resolve_path(path_template: str, project_id: str) -> str:
    return (
        path_template.replace("{project_id}", project_id)
        .replace("{proposal_id}", "prop-123")
        .replace("{version}", "1")
        .replace("{task_id}", "T1")
        .replace("{member_id}", "M1")
    )


@pytest.mark.asyncio
async def test_openapi_project_routes_authorization_matrix(
    client: httpx.AsyncClient,
    other_client: httpx.AsyncClient,
    auth_client: httpx.AsyncClient,
):
    """
    Dynamically iterate all project routes from OpenAPI schema.
    Verify:
    1. Unauthenticated requests always receive 401.
    2. Non-member authenticated requests always receive 404.
    """
    # 1. Create a real project owned by auth_user
    p_res = await auth_client.post("/api/v1/projects", json={"name": "Auth Matrix Project"})
    assert p_res.status_code == 201
    real_project_id = p_res.json()["id"]

    openapi = app.openapi()
    paths = openapi.get("paths", {})

    project_endpoints: list[tuple[str, str]] = []
    for path, methods in paths.items():
        if "{project_id}" not in path:
            continue
        # Skip GitHub webhook as it is authenticated exclusively via X-Hub-Signature-256
        if "github/webhook" in path:
            continue

        for method in methods:
            if method.lower() in ("get", "post", "patch", "put", "delete"):
                project_endpoints.append((method.upper(), path))

    assert len(project_endpoints) > 10, "Expected at least 10 project endpoints in OpenAPI"

    for method, path_template in project_endpoints:
        resolved_path = _resolve_path(path_template, real_project_id)

        # 1. Unauthenticated request -> must return 401
        res_no_auth = await client.request(
            method=method,
            url=resolved_path,
            json={},  # Empty body to avoid potential 422 if body inspected first
        )
        assert res_no_auth.status_code == 401, (
            f"Expected 401 for unauthenticated {method} {resolved_path}, "
            f"got {res_no_auth.status_code} ({res_no_auth.text})"
        )

        # 2. Non-member request -> must return 404 (never leak project existence)
        res_non_member = await other_client.request(
            method=method,
            url=resolved_path,
            json={},
        )
        assert res_non_member.status_code == 404, (
            f"Expected 404 for non-member {method} {resolved_path}, "
            f"got {res_non_member.status_code} ({res_non_member.text})"
        )
