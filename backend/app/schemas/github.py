"""Pydantic schemas for GitHub integration."""

from pydantic import BaseModel, ConfigDict


class GitHubWebhookResponse(BaseModel):
    """Response returned upon processing a GitHub webhook event."""

    model_config = ConfigDict(frozen=True)

    received: bool
    event_type: str
    summary: str
    evidence_recorded_count: int
