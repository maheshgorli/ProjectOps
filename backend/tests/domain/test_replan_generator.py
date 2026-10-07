"""Unit tests for ReplanCandidateGenerator."""

from datetime import UTC, date, datetime

from backend.app.domain.clock import FrozenClock
from backend.app.domain.models import (
    Member,
    ProjectPlan,
    Task,
)
from backend.app.domain.risk.replan_generator import ReplanCandidateGenerator


def test_replan_generator_mitigates_capacity_overload():
    clock = FrozenClock(date(2026, 10, 5))
    generator = ReplanCandidateGenerator(clock)

    # Alice is assigned 2 parallel tasks on day 1 (total 16h, capacity 8h)
    alice = Member(id="ALICE", name="Alice", daily_capacity_hours=8.0)
    # Bob is available with 0 assigned tasks
    bob = Member(id="BOB", name="Bob", daily_capacity_hours=8.0)

    tasks = {
        "T1": Task(id="T1", title="Backend Task", estimated_hours=8.0, assigned_to_id="ALICE"),
        "T2": Task(id="T2", title="Frontend Task", estimated_hours=8.0, assigned_to_id="ALICE"),
    }

    plan = ProjectPlan(
        id="PLAN-INIT",
        project_id="PROJ-REPLAN",
        version=1,
        name="Overloaded Plan",
        created_at=datetime.now(UTC),
        tasks=tasks,
        dependencies=[],
        members={"ALICE": alice, "BOB": bob},
    )

    candidate = generator.generate_mitigation_candidate(plan)

    # 1. Version incremented
    assert candidate.candidate_plan.version == 2
    assert candidate.candidate_plan.id != plan.id

    # 2. Check reassignment
    cand_t1 = candidate.candidate_plan.tasks["T1"]
    cand_t2 = candidate.candidate_plan.tasks["T2"]

    # Either T1 or T2 should have been reassigned to Bob
    assignees = {cand_t1.assigned_to_id, cand_t2.assigned_to_id}
    assert assignees == {"ALICE", "BOB"}

    # 3. Verify resolved risks
    assert candidate.resolved_risks_count >= 1
    assert any("Reassigned" in note for note in candidate.mitigation_notes)

    # 4. Verify original plan was NOT mutated
    assert plan.tasks["T1"].assigned_to_id == "ALICE"
    assert plan.tasks["T2"].assigned_to_id == "ALICE"
    assert plan.version == 1
