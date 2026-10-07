"""Deterministic Candidate Replan Generator and Impact Evaluation.

Core Principle 3: Replans are simulated by the deterministic scheduler.
The LLM explains computed numbers; it never invents them.
"""

from copy import deepcopy
from datetime import UTC, datetime

from backend.app.domain.calendar import working_days_delta
from backend.app.domain.clock import Clock
from backend.app.domain.models import ProjectPlan, Task, TaskStatus
from backend.app.domain.risk.engine import DeterministicRiskEngine
from backend.app.domain.risk.models import (
    ReplanCandidate,
    RiskType,
)
from backend.app.domain.scheduler import DeterministicScheduler


class ReplanCandidateGenerator:
    """Generates candidate replan options to resolve detected risks."""

    def __init__(self, clock: Clock) -> None:
        self.clock = clock
        self.risk_engine = DeterministicRiskEngine(clock)
        self.scheduler = DeterministicScheduler(clock)

    def generate_mitigation_candidate(self, baseline_plan: ProjectPlan) -> ReplanCandidate:
        """
        Produce a deterministically adjusted candidate plan resolving overload and delays.

        Does NOT mutate the original plan or database.
        """
        baseline_sched = self.scheduler.schedule(baseline_plan)
        baseline_risks = self.risk_engine.analyze_risks(baseline_plan, baseline_sched).risks

        # Clone plan tasks and dependencies
        candidate_tasks: dict[str, Task] = {
            t_id: deepcopy(t) for t_id, t in baseline_plan.tasks.items()
        }
        candidate_deps = list(baseline_plan.dependencies)
        notes: list[str] = []

        # 1. Address Capacity Overloads by reallocating parallel tasks to available members
        overload_risks = [r for r in baseline_risks if r.risk_type == RiskType.CAPACITY_OVERLOAD]
        for orisk in overload_risks:
            overloaded_m_id = str(orisk.metrics.get("member_id", ""))
            # Find eligible alternate members in the plan
            alternate_members = [
                m_id
                for m_id in baseline_plan.members
                if m_id != overloaded_m_id
                and not baseline_sched.member_workloads.get(m_id, None)
                or not baseline_sched.member_workloads[m_id].is_overallocated
            ]

            if alternate_members:
                target_alt = sorted(alternate_members)[0]
                # Reassign one non-critical task assigned to the overloaded member
                for t_id, task in sorted(candidate_tasks.items()):
                    if (
                        task.assigned_to_id == overloaded_m_id
                        and task.status != TaskStatus.COMPLETED
                    ):
                        task.assigned_to_id = target_alt
                        notes.append(
                            f"Reassigned '{task.title}' ({t_id}) from '{overloaded_m_id}' "
                            f"to '{target_alt}' to resolve capacity overload."
                        )
                        break

        # 2. Address Overdue Critical Path Tasks: Reset start date to today
        delay_risks = [r for r in baseline_risks if r.risk_type == RiskType.CRITICAL_PATH_DELAY]
        for drisk in delay_risks:
            for t_id in drisk.affected_task_ids:
                task = candidate_tasks.get(t_id)
                if task and task.is_overdue(self.clock):
                    task.start_date = self.clock.today()
                    notes.append(
                        f"Adjusted planned start for overdue task '{task.title}' ({t_id}) "
                        f"to current date ({self.clock.today()})."
                    )

        # 3. Create Candidate ProjectPlan snapshot
        candidate_plan = ProjectPlan(
            id=f"{baseline_plan.id}-candidate-v{baseline_plan.version + 1}",
            project_id=baseline_plan.project_id,
            version=baseline_plan.version + 1,
            name=f"{baseline_plan.name} (Proposed Replan)",
            created_at=datetime.now(UTC),
            tasks=candidate_tasks,
            dependencies=candidate_deps,
            members=baseline_plan.members,
            target_completion_date=baseline_plan.target_completion_date,
            created_by="replan_generator",
        )

        candidate_sched = self.scheduler.schedule(candidate_plan)
        candidate_risks = self.risk_engine.analyze_risks(candidate_plan, candidate_sched).risks

        finish_delta = working_days_delta(
            baseline_sched.project_finish_date,
            candidate_sched.project_finish_date,
        )
        resolved_count = max(0, len(baseline_risks) - len(candidate_risks))

        if not notes:
            notes.append("No automated task adjustments required; plan is structurally optimal.")

        return ReplanCandidate(
            candidate_plan=candidate_plan,
            baseline_finish_date=baseline_sched.project_finish_date,
            candidate_finish_date=candidate_sched.project_finish_date,
            finish_date_delta_days=finish_delta,
            resolved_risks_count=resolved_count,
            mitigation_notes=notes,
        )
