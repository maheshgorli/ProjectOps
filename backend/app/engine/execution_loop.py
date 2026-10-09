"""Autonomous Multi-Agent Execution Loop Engine.

Implements the core loop:
PLAN -> EXECUTE -> OBSERVE -> REASON -> REPLAN -> APPROVE -> EXECUTE

Enforces:
- Rule 1: Deterministic code owns truth (dates, graphs, CPM, risks, replans).
- Rule 3: Replans are simulated by the deterministic scheduler.
- Rule 4: Replanning requires human approval. Never silently change a plan.
- Rule 5: Append-only audit history for all agent runs and decisions.
"""

import json
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.schemas.mappers import domain_plan_to_response
from backend.app.domain.clock import Clock, SystemClock
from backend.app.domain.graph import TaskGraph
from backend.app.domain.models import ProjectPlan, TaskStatus
from backend.app.domain.risk.engine import DeterministicRiskEngine, RiskEvaluationResult
from backend.app.domain.risk.replan_generator import (
    ReplanCandidate,
    ReplanCandidateGenerator,
)
from backend.app.domain.scheduler import DeterministicScheduler
from backend.app.repositories.history_repository import HistoryRepository
from backend.app.repositories.plan_repository import PlanRepository
from backend.app.schemas.risk import ReplanCandidateResponse


@dataclass(frozen=True)
class LoopStepResult:
    """Internal result of an execution loop cycle."""

    project_id: str
    stage: str
    status: str
    health_score: float
    is_at_risk: bool
    summary: str
    detected_risks_count: int
    actionable_tasks: list[str]
    replan_candidate: ReplanCandidateResponse | None = None
    requires_human_approval: bool = False


class ExecutionLoopEngine:
    """
    Orchestrates the autonomous multi-agent execution loop.

    Flow:
    1. PLAN: Validate DAG and compute current schedule.
    2. EXECUTE: Determine tasks unblocked and ready for work.
    3. OBSERVE: Check recent progress events, deadlines, and overdue tasks.
    4. REASON: Run deterministic risk engine to score project health and identify anomalies.
    5. REPLAN: If risks require intervention, simulate deterministic mitigation candidate
       and pause at AWAITING_APPROVAL.
    """

    def __init__(self, clock: Clock | None = None) -> None:
        self.clock = clock or SystemClock()

    def get_actionable_tasks(self, plan: ProjectPlan) -> list[str]:
        """
        Identify tasks ready to be executed.

        A task is actionable if its status is TODO and all its predecessor
        dependencies are COMPLETED.
        """
        predecessors_map: dict[str, list[str]] = {tid: [] for tid in plan.tasks}
        for dep in plan.dependencies:
            if dep.successor_id in predecessors_map:
                predecessors_map[dep.successor_id].append(dep.predecessor_id)

        actionable: list[str] = []
        for task_id, task in plan.tasks.items():
            if task.status != TaskStatus.TODO:
                continue
            preds = predecessors_map.get(task_id, [])
            all_preds_completed = all(
                plan.tasks[pred_id].status == TaskStatus.COMPLETED
                for pred_id in preds
                if pred_id in plan.tasks
            )
            if all_preds_completed:
                actionable.append(task_id)

        return actionable

    async def run_step(
        self,
        project_id: str,
        session: AsyncSession,
        triggered_by: str = "manual",
    ) -> LoopStepResult:
        """Run an autonomous multi-agent loop cycle for a project."""
        plan_repo = PlanRepository(session)
        history_repo = HistoryRepository(session)

        # 1. PLAN STAGE: Verify active plan and DAG
        active_plan = await plan_repo.get_active_plan(project_id)
        if not active_plan:
            await history_repo.record_agent_run(
                project_id=project_id,
                loop_stage="PLAN",
                status="FAILED",
                summary="No active plan found for project.",
                triggered_by=triggered_by,
            )
            return LoopStepResult(
                project_id=project_id,
                stage="PLAN",
                status="FAILED",
                health_score=0.0,
                is_at_risk=True,
                summary="No active plan found. Please create or approve a project plan.",
                detected_risks_count=0,
                actionable_tasks=[],
                requires_human_approval=False,
            )

        graph = TaskGraph(active_plan.tasks.values(), active_plan.dependencies)
        graph.validate_dag()
        scheduler = DeterministicScheduler(self.clock)
        scheduler.schedule(active_plan)

        await history_repo.record_agent_run(
            project_id=project_id,
            loop_stage="PLAN",
            status="SUCCESS",
            summary=f"Plan v{active_plan.version} validated with {len(active_plan.tasks)} tasks.",
            triggered_by=triggered_by,
        )

        # 2. EXECUTE STAGE: Identify actionable tasks
        actionable_tasks = self.get_actionable_tasks(active_plan)
        await history_repo.record_agent_run(
            project_id=project_id,
            loop_stage="EXECUTE",
            status="SUCCESS",
            summary=f"{len(actionable_tasks)} task(s) unblocked and ready for execution.",
            details_json=json.dumps({"actionable_tasks": actionable_tasks}),
            triggered_by=triggered_by,
        )

        # 3. OBSERVE STAGE: Observe clock time and task overdue flags
        overdue_tasks = [t.id for t in active_plan.tasks.values() if t.is_overdue(self.clock)]
        await history_repo.record_agent_run(
            project_id=project_id,
            loop_stage="OBSERVE",
            status="SUCCESS",
            summary=f"Observed project state. Overdue tasks: {len(overdue_tasks)}.",
            details_json=json.dumps({"overdue_tasks": overdue_tasks}),
            triggered_by=triggered_by,
        )

        # 4. REASON STAGE: Deterministic risk engine
        risk_engine = DeterministicRiskEngine(self.clock)
        risk_eval: RiskEvaluationResult = risk_engine.analyze_risks(active_plan)

        # Record risks to append-only risk log
        for risk in risk_eval.risks:
            await history_repo.record_risk_event(
                project_id=project_id,
                risk_type=risk.risk_type.value,
                severity=risk.severity.value,
                description=risk.description,
                payload_json=json.dumps(risk.metrics),
            )

        await history_repo.record_agent_run(
            project_id=project_id,
            loop_stage="REASON",
            status="SUCCESS",
            summary=(
                f"Health score: {risk_eval.health_score}/100. "
                f"Detected {len(risk_eval.risks)} risk(s)."
            ),
            details_json=json.dumps(
                {
                    "health_score": risk_eval.health_score,
                    "risks_count": len(risk_eval.risks),
                }
            ),
            triggered_by=triggered_by,
        )

        # 5. REPLAN STAGE: If project is at risk, generate candidate and halt for approval
        if risk_eval.is_at_risk:
            generator = ReplanCandidateGenerator(self.clock)
            candidate: ReplanCandidate = generator.generate_mitigation_candidate(active_plan)

            candidate_response = ReplanCandidateResponse(
                project_id=project_id,
                baseline_version=active_plan.version,
                proposed_version=candidate.candidate_plan.version,
                baseline_finish_date=candidate.baseline_finish_date,
                proposed_finish_date=candidate.candidate_finish_date,
                finish_date_delta_days=candidate.finish_date_delta_days,
                resolved_risks_count=candidate.resolved_risks_count,
                mitigation_notes=candidate.mitigation_notes,
                proposed_plan=domain_plan_to_response(candidate.candidate_plan),
            )

            # Rule 4: Replanning requires human approval. Never silently change a plan.
            await history_repo.record_agent_run(
                project_id=project_id,
                loop_stage="REPLAN",
                status="AWAITING_APPROVAL",
                summary=(
                    f"Candidate replan v{candidate.candidate_plan.version} generated "
                    f"(mitigates {candidate.resolved_risks_count} risks). "
                    "Awaiting human approval."
                ),
                details_json=json.dumps(
                    {
                        "proposed_version": candidate.candidate_plan.version,
                        "finish_date_delta_days": candidate.finish_date_delta_days,
                        "resolved_risks_count": candidate.resolved_risks_count,
                    }
                ),
                triggered_by=triggered_by,
            )

            return LoopStepResult(
                project_id=project_id,
                stage="REPLAN",
                status="AWAITING_APPROVAL",
                health_score=risk_eval.health_score,
                is_at_risk=True,
                summary=(
                    f"Risk detected. Candidate replan generated to mitigate "
                    f"{candidate.resolved_risks_count} risk(s). Requires human approval."
                ),
                detected_risks_count=len(risk_eval.risks),
                actionable_tasks=actionable_tasks,
                replan_candidate=candidate_response,
                requires_human_approval=True,
            )

        # Project is healthy: cycle completes cleanly
        await history_repo.record_agent_run(
            project_id=project_id,
            loop_stage="APPROVE",
            status="HEALTHY",
            summary="All tasks on track. No replan needed.",
            triggered_by=triggered_by,
        )

        return LoopStepResult(
            project_id=project_id,
            stage="EXECUTE",
            status="HEALTHY",
            health_score=risk_eval.health_score,
            is_at_risk=False,
            summary="Project execution on track. No replanning required.",
            detected_risks_count=0,
            actionable_tasks=actionable_tasks,
            replan_candidate=None,
            requires_human_approval=False,
        )
