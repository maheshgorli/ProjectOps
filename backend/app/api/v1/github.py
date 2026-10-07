"""GitHub webhook API endpoints."""

import json
import os

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_async_session
from backend.app.integrations.github.service import (
    GitHubWebhookService,
    verify_github_signature,
)
from backend.app.repositories.project_repository import ProjectRepository
from backend.app.schemas.github import GitHubWebhookResponse

router = APIRouter(prefix="/projects/{project_id}/github", tags=["github"])


@router.post("/webhook", response_model=GitHubWebhookResponse)
async def receive_github_webhook(
    project_id: str,
    request: Request,
    x_github_event: str = Header("push", alias="X-GitHub-Event"),
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
    session: AsyncSession = Depends(get_async_session),
) -> GitHubWebhookResponse:
    """
    Ingest GitHub webhook event as audit evidence.

    Verifies HMAC-SHA256 signature using X-Hub-Signature-256.
    Rule 6: Logs commit and PR activity to progress_history as evidence without
    automatically mutating task completion status.
    Rule 7: Never exposes tokens or secrets.
    """
    project_repo = ProjectRepository(session)
    project = await project_repo.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )

    payload_bytes = await request.body()
    webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET", "projectops_dev_secret")

    # Enforce HMAC signature check
    require_signature = os.getenv("GITHUB_REQUIRE_SIGNATURE", "true").lower() == "true"
    if require_signature and (
        not x_hub_signature_256
        or not verify_github_signature(payload_bytes, x_hub_signature_256, webhook_secret)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Hub-Signature-256 signature.",
        )

    try:
        payload = json.loads(payload_bytes.decode("utf-8")) if payload_bytes else {}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed JSON payload: {exc}",
        ) from exc

    service = GitHubWebhookService(webhook_secret=webhook_secret)
    result = await service.process_webhook(
        project_id=project_id,
        event_type=x_github_event,
        payload=payload,
        session=session,
    )

    await session.commit()

    return GitHubWebhookResponse(
        received=result["received"],
        event_type=result["event_type"],
        summary=result["summary"],
        evidence_recorded_count=result["evidence_recorded_count"],
    )
