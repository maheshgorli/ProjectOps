"""Unit tests for deterministic member scoring and assignment."""

from datetime import date

from backend.app.domain.assignment import score_member_assignments
from backend.app.domain.models import Member, MemberWorkload, Task


def test_assignment_ranking_by_skills_and_workload():
    members = [
        Member(id="m-alice", name="Alice", skills=["React", "TypeScript"]),
        Member(id="m-bob", name="Bob", skills=["Python", "FastAPI"]),
    ]

    task_react = Task(id="T_React", title="Frontend", required_skills=["React", "TypeScript"])

    candidates = score_member_assignments(task_react, members)
    assert len(candidates) == 2
    # Alice has 100% skill match, Bob has 0%
    assert candidates[0].member_id == "m-alice"
    assert candidates[0].breakdown["skill_match"] == 1.0
    assert candidates[1].member_id == "m-bob"
    assert candidates[1].breakdown["skill_match"] == 0.0


def test_assignment_penalizes_overloaded_member():
    members = [
        Member(id="m-1", name="Dev 1", skills=["Python"]),
        Member(id="m-2", name="Dev 2", skills=["Python"]),
    ]
    task = Task(id="T1", title="Task", required_skills=["Python"])

    # Dev 1 has 90% utilization, Dev 2 has 10%
    workloads = {
        "m-1": MemberWorkload("m-1", date(2026, 11, 2), date(2026, 11, 6), 36.0, 40.0, 0.9, False),
        "m-2": MemberWorkload("m-2", date(2026, 11, 2), date(2026, 11, 6), 4.0, 40.0, 0.1, False),
    }

    candidates = score_member_assignments(task, members, current_workloads=workloads)
    assert candidates[0].member_id == "m-2"
    assert candidates[0].total_score > candidates[1].total_score
