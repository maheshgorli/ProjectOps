"""Repository for append-only audit trail: progress history, decisions, and risk events."""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.history import (
    DecisionRecordORM,
    ProgressHistoryORM,
    RiskEventORM,
)


class HistoryRepository:
    """Provides append-only persistence and queries for history, decisions, and risk events."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record_progress(
        self,
        project_id: str,
        task_id: str,
        new_status: str,
        previous_status: str | None = None,
        evidence_notes: str = "",
        recorded_by: str = "system",
        recorded_at: datetime | None = None,
    ) -> ProgressHistoryORM:
        """Append a progress event to the immutable audit trail."""
        event = ProgressHistoryORM(
            id=str(uuid4()),
            project_id=project_id,
            task_id=task_id,
            previous_status=previous_status,
            new_status=new_status,
            evidence_notes=evidence_notes,
            recorded_by=recorded_by,
            recorded_at=recorded_at or datetime.now(UTC),
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def get_progress_history(
        self,
        project_id: str,
        task_id: str | None = None,
    ) -> Sequence[ProgressHistoryORM]:
        """Query progress history in chronological order."""
        stmt = (
            select(ProgressHistoryORM)
            .where(ProgressHistoryORM.project_id == project_id)
            .order_by(ProgressHistoryORM.recorded_at.asc())
        )
        if task_id:
            stmt = stmt.where(ProgressHistoryORM.task_id == task_id)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def record_decision(
        self,
        project_id: str,
        decision_type: str,
        summary: str,
        decided_by: str,
        rationale: str = "",
        plan_id: str | None = None,
        recorded_at: datetime | None = None,
    ) -> DecisionRecordORM:
        """Append an immutable decision record (replan approvals, rejections, adjustments)."""
        record = DecisionRecordORM(
            id=str(uuid4()),
            project_id=project_id,
            plan_id=plan_id,
            decision_type=decision_type,
            summary=summary,
            rationale=rationale,
            decided_by=decided_by,
            recorded_at=recorded_at or datetime.now(UTC),
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def get_decisions(self, project_id: str) -> Sequence[DecisionRecordORM]:
        """Query all decision records for a project chronologically."""
        stmt = (
            select(DecisionRecordORM)
            .where(DecisionRecordORM.project_id == project_id)
            .order_by(DecisionRecordORM.recorded_at.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def record_risk_event(
        self,
        project_id: str,
        risk_type: str,
        severity: str,
        description: str,
        payload_json: str | None = None,
        detected_at: datetime | None = None,
    ) -> RiskEventORM:
        """Append a detected risk anomaly to the risk log."""
        event = RiskEventORM(
            id=str(uuid4()),
            project_id=project_id,
            risk_type=risk_type,
            severity=severity,
            description=description,
            payload_json=payload_json,
            detected_at=detected_at or datetime.now(UTC),
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def get_risk_events(
        self,
        project_id: str,
        min_severity: str | None = None,
    ) -> Sequence[RiskEventORM]:
        """Query all risk events for a project chronologically."""
        stmt = (
            select(RiskEventORM)
            .where(RiskEventORM.project_id == project_id)
            .order_by(RiskEventORM.detected_at.asc())
        )
        if min_severity:
            stmt = stmt.where(RiskEventORM.severity == min_severity)

        result = await self.session.execute(stmt)
        return result.scalars().all()
