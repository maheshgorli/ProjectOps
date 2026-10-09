"""Repository for server-side Replan Proposals (Core Principle 4 & P0-1 fix)."""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.proposal import ReplanProposalORM


class ProposalRepository:
    """Manages the lifecycle of server-stored replan proposal snapshots."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_proposal(
        self,
        project_id: str,
        baseline_version: int,
        candidate_plan: dict[str, Any],
        risks_addressed: list[str] | None = None,
        explanation: str = "",
        created_by: str = "engine",
    ) -> ReplanProposalORM:
        """Persist a newly simulated candidate replan proposal in PENDING status."""
        proposal = ReplanProposalORM(
            id=str(uuid4()),
            project_id=project_id,
            baseline_version=baseline_version,
            candidate_plan=candidate_plan,
            risks_addressed=risks_addressed or [],
            explanation=explanation,
            status="PENDING",
            created_by=created_by,
            created_at=datetime.now(UTC),
        )
        self.session.add(proposal)
        await self.session.flush()
        return proposal

    async def get_proposal(self, project_id: str, proposal_id: str) -> ReplanProposalORM | None:
        """Fetch a specific proposal by project and proposal ID."""
        stmt = select(ReplanProposalORM).where(
            ReplanProposalORM.project_id == project_id,
            ReplanProposalORM.id == proposal_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_proposals(
        self, project_id: str, status: str | None = None
    ) -> Sequence[ReplanProposalORM]:
        """List proposals for a project, optionally filtered by status, ordered newest first."""
        stmt = select(ReplanProposalORM).where(ReplanProposalORM.project_id == project_id)
        if status:
            stmt = stmt.where(ReplanProposalORM.status == status.upper().strip())
        stmt = stmt.order_by(ReplanProposalORM.created_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def supersede_pending_proposals(self, project_id: str) -> int:
        """Mark all existing PENDING proposals for this project as SUPERSEDED."""
        stmt = (
            update(ReplanProposalORM)
            .where(
                ReplanProposalORM.project_id == project_id,
                ReplanProposalORM.status == "PENDING",
            )
            .values(status="SUPERSEDED")
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def mark_approved(
        self,
        proposal: ReplanProposalORM,
        decided_by: str,
        rationale: str,
        decided_at: datetime | None = None,
    ) -> None:
        """Mark a proposal as officially APPROVED."""
        proposal.status = "APPROVED"
        proposal.decided_by = decided_by
        proposal.rationale = rationale
        proposal.decided_at = decided_at or datetime.now(UTC)
        await self.session.flush()

    async def mark_rejected(
        self,
        proposal: ReplanProposalORM,
        decided_by: str,
        rationale: str,
        decided_at: datetime | None = None,
    ) -> None:
        """Mark a proposal as formally REJECTED."""
        proposal.status = "REJECTED"
        proposal.decided_by = decided_by
        proposal.rationale = rationale
        proposal.decided_at = decided_at or datetime.now(UTC)
        await self.session.flush()
