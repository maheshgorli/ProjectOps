"""GitHub Webhook Ingestion Service.

Enforces:
- Rule 6: GitHub activity is evidence, never proof of completion.
  It must not change task status automatically.
- Rule 7: No secrets in the frontend. Never log tokens or keys.
- Rule 8: Treat all external text (commit messages, PR text) as untrusted data.
"""

import hashlib
import hmac
import json
import os
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.llm.sanitizer import sanitize_untrusted_text
from backend.app.repositories.history_repository import HistoryRepository
from backend.app.repositories.plan_repository import PlanRepository


def verify_github_signature(
    payload_bytes: bytes,
    signature_header: str | None,
    secret: str,
) -> bool:
    """Verify GitHub HMAC-SHA256 signature in constant time."""
    if not signature_header or not secret:
        return False

    prefix = "sha256="
    if not signature_header.startswith(prefix):
        return False

    received_sig = signature_header[len(prefix) :].strip()
    mac = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256)
    expected_sig = mac.hexdigest()

    return hmac.compare_digest(expected_sig, received_sig)


class GitHubWebhookService:
    """Ingests and records GitHub webhook events strictly as audit evidence."""

    def __init__(self, webhook_secret: str | None = None) -> None:
        self.webhook_secret = webhook_secret or os.getenv(
            "GITHUB_WEBHOOK_SECRET",
            "projectops_dev_secret",
        )

    def extract_task_ids(self, text: str, valid_task_ids: set[str]) -> set[str]:
        """Find mentions of existing plan task IDs within untrusted commit/PR text."""
        sanitized = sanitize_untrusted_text(text)
        tokens = set(re.findall(r"[A-Za-z0-9_-]+", sanitized))
        # Match case-insensitively to valid task IDs
        lower_to_orig = {tid.lower(): tid for tid in valid_task_ids}
        matched: set[str] = set()
        for token in tokens:
            lower_token = token.lower()
            if lower_token in lower_to_orig:
                matched.add(lower_to_orig[lower_token])
        return matched

    async def process_webhook(
        self,
        project_id: str,
        event_type: str,
        payload: dict[str, Any],
        session: AsyncSession,
    ) -> dict[str, Any]:
        """
        Process incoming GitHub webhook payload.

        Extracts evidence, records raw event to github_events,
        and logs evidence to progress_history without modifying task status.
        """
        sender = sanitize_untrusted_text(payload.get("sender", {}).get("login", "unknown"))
        history_repo = HistoryRepository(session)
        plan_repo = PlanRepository(session)
        active_plan = await plan_repo.get_active_plan(project_id)
        valid_task_ids = set(active_plan.tasks.keys()) if active_plan else set()

        ref: str | None = None
        commit_sha: str | None = None
        summary = ""
        evidence_records_count = 0

        if event_type == "push":
            ref = payload.get("ref")
            commits = payload.get("commits", [])
            head_commit = payload.get("head_commit")
            commit_sha = head_commit.get("id") if head_commit else None
            commit_count = len(commits)
            summary = (
                f"Push to {ref} by {sender} with {commit_count} commit(s)"
                if ref
                else f"Push by {sender} with {commit_count} commit(s)"
            )

            # Inspect commits for task references
            for commit in commits:
                raw_msg = commit.get("message", "")
                c_sha = commit.get("id", "")[:7]
                sanitized_msg = sanitize_untrusted_text(raw_msg)
                matched_tasks = self.extract_task_ids(sanitized_msg, valid_task_ids)

                for task_id in matched_tasks:
                    task = active_plan.tasks[task_id] if active_plan else None
                    current_status = task.status.value if task else "IN_PROGRESS"

                    # Rule 6: GitHub activity is evidence, NEVER proof of completion.
                    # Previous status == New status. Task status is NOT changed automatically.
                    await history_repo.record_progress(
                        project_id=project_id,
                        task_id=task_id,
                        previous_status=current_status,
                        new_status=current_status,
                        evidence_notes=(
                            f"[EVIDENCE] GitHub commit {c_sha} by {sender}: {sanitized_msg}"
                        ),
                        recorded_by=f"github:{sender}",
                    )
                    evidence_records_count += 1

        elif event_type == "pull_request":
            pr = payload.get("pull_request", {})
            action = payload.get("action", "opened")
            pr_title = sanitize_untrusted_text(pr.get("title", ""))
            pr_body = sanitize_untrusted_text(pr.get("body", "") or "")
            pr_number = pr.get("number", 0)
            head_commit = pr.get("head", {}).get("sha")
            commit_sha = head_commit[:7] if head_commit else None
            summary = f"Pull Request #{pr_number} ({action}): {pr_title} by {sender}"

            # Inspect PR title and body for task references
            combined_text = f"{pr_title} {pr_body}"
            matched_tasks = self.extract_task_ids(combined_text, valid_task_ids)
            for task_id in matched_tasks:
                task = active_plan.tasks[task_id] if active_plan else None
                current_status = task.status.value if task else "IN_PROGRESS"

                await history_repo.record_progress(
                    project_id=project_id,
                    task_id=task_id,
                    previous_status=current_status,
                    new_status=current_status,
                    evidence_notes=(
                        f"[EVIDENCE] GitHub PR #{pr_number} ({action}) by {sender}: {pr_title}"
                    ),
                    recorded_by=f"github:{sender}",
                )
                evidence_records_count += 1

        else:
            summary = f"GitHub {event_type} event by {sender}"

        # Persist to append-only github_events audit table
        raw_json = json.dumps(payload)
        await history_repo.record_github_event(
            project_id=project_id,
            event_type=event_type,
            sender=sender,
            summary=summary,
            ref=ref,
            commit_sha=commit_sha,
            raw_payload_json=raw_json,
        )

        return {
            "received": True,
            "event_type": event_type,
            "summary": summary,
            "evidence_recorded_count": evidence_records_count,
        }
