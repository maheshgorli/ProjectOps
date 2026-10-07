"""Pure domain models for risk rules, evaluations, and replan candidates."""

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

from backend.app.domain.models import ProjectPlan


class RiskSeverity(StrEnum):
    """Risk severity classifications."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskType(StrEnum):
    """Categorized risk event types."""

    CRITICAL_PATH_DELAY = "CRITICAL_PATH_DELAY"
    CAPACITY_OVERLOAD = "CAPACITY_OVERLOAD"
    BLOCKED_CASCADE = "BLOCKED_CASCADE"
    DEADLINE_BREACH = "DEADLINE_BREACH"


@dataclass(frozen=True)
class DetectedRisk:
    """An individual risk identified by deterministic rule evaluation."""

    risk_type: RiskType
    severity: RiskSeverity
    description: str
    affected_task_ids: list[str] = field(default_factory=list)
    metrics: dict[str, str | int | float] = field(default_factory=dict)


@dataclass(frozen=True)
class RiskEvaluationResult:
    """Complete risk evaluation result including health score."""

    health_score: int  # 0 to 100
    risks: list[DetectedRisk] = field(default_factory=list)
    is_at_risk: bool = False
    summary: str = ""


@dataclass(frozen=True)
class ReplanCandidate:
    """A deterministically computed candidate replan mitigation proposition."""

    candidate_plan: ProjectPlan
    baseline_finish_date: date
    candidate_finish_date: date
    finish_date_delta_days: int
    resolved_risks_count: int
    mitigation_notes: list[str] = field(default_factory=list)
