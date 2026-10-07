"""Deterministic Risk Engine coordinating rules and health scoring."""

from backend.app.domain.clock import Clock
from backend.app.domain.graph import TaskGraph
from backend.app.domain.models import ProjectPlan
from backend.app.domain.risk.models import (
    DetectedRisk,
    RiskEvaluationResult,
    RiskSeverity,
)
from backend.app.domain.risk.rules import (
    evaluate_blocked_cascades,
    evaluate_capacity_overloads,
    evaluate_critical_path_delays,
    evaluate_deadline_breach,
)
from backend.app.domain.scheduler import DeterministicScheduler, ScheduleResult

SEVERITY_PENALTIES = {
    RiskSeverity.CRITICAL: 25,
    RiskSeverity.HIGH: 15,
    RiskSeverity.MEDIUM: 8,
    RiskSeverity.LOW: 3,
}


class DeterministicRiskEngine:
    """Evaluates deterministic risk rules and computes project health."""

    def __init__(self, clock: Clock) -> None:
        self.clock = clock

    def analyze_risks(
        self,
        plan: ProjectPlan,
        schedule: ScheduleResult | None = None,
    ) -> RiskEvaluationResult:
        """Run all deterministic risk rules against the plan and schedule."""
        # 1. Compute schedule if not passed
        sched = schedule
        if sched is None:
            scheduler = DeterministicScheduler(self.clock)
            sched = scheduler.schedule(plan)

        # 2. Build graph for topological and cascade traversals
        graph = TaskGraph(tasks=plan.tasks.values(), dependencies=plan.dependencies)

        # 3. Evaluate rules
        risks: list[DetectedRisk] = []
        risks.extend(evaluate_critical_path_delays(plan, sched, self.clock))
        risks.extend(evaluate_capacity_overloads(sched))
        risks.extend(evaluate_blocked_cascades(plan, graph))
        risks.extend(evaluate_deadline_breach(plan, sched))

        # 4. Compute Health Score (bounded 0 - 100)
        penalty = sum(SEVERITY_PENALTIES.get(r.severity, 5) for r in risks)
        health_score = max(0, min(100, 100 - penalty))

        is_at_risk = len(risks) > 0
        if not is_at_risk:
            summary = "Project is on track. No schedule or capacity risks detected."
        else:
            severities = [r.severity.value for r in risks]
            highest = (
                "CRITICAL"
                if "CRITICAL" in severities
                else ("HIGH" if "HIGH" in severities else "MEDIUM")
            )
            summary = (
                f"Project has {len(risks)} detected risk(s) (Highest severity: {highest}). "
                f"Health score: {health_score}/100."
            )

        return RiskEvaluationResult(
            health_score=health_score,
            risks=risks,
            is_at_risk=is_at_risk,
            summary=summary,
        )
