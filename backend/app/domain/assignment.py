"""Deterministic candidate scoring for task assignment.

Scores members per task using skill match, availability, workload, and priority.
Returns ranked candidates with an explainable per-factor score breakdown.
Weights are fully configurable.
Pure Python, zero I/O.
"""

from collections.abc import Iterable
from typing import Final

from backend.app.domain.models import AssignmentCandidate, Member, MemberWorkload, Task

DEFAULT_ASSIGNMENT_WEIGHTS: Final[dict[str, float]] = {
    "skill_match": 0.40,
    "availability": 0.30,
    "workload": 0.20,
    "priority": 0.10,
}


def score_member_assignments(
    task: Task,
    members: Iterable[Member],
    current_workloads: dict[str, MemberWorkload] | None = None,
    weights: dict[str, float] | None = None,
) -> list[AssignmentCandidate]:
    """Score and rank candidate members for assigning a task.

    Args:
        task: The task to be assigned.
        members: Eligible team members.
        current_workloads: Optional dictionary of current member workloads.
        weights: Optional dictionary of factor weights summing to 1.0.

    Returns:
        List of AssignmentCandidate sorted in descending order of total_score.
        Ties are broken deterministically by member ID.
    """
    w = weights or DEFAULT_ASSIGNMENT_WEIGHTS
    candidates: list[AssignmentCandidate] = []

    req_skills = set(task.required_skills)

    for member in members:
        # 1. Skill Match Score [0.0 - 1.0]
        if not req_skills:
            skill_score = 1.0
        else:
            member_skills = set(member.skills)
            overlap = req_skills.intersection(member_skills)
            skill_score = len(overlap) / len(req_skills)

        # 2. Availability Score & 3. Workload Score
        utilization = 0.0
        if current_workloads and member.id in current_workloads:
            utilization = current_workloads[member.id].utilization_rate

        availability_score = max(0.0, 1.0 - min(1.0, utilization))
        workload_score = max(0.0, 1.0 - utilization) if utilization <= 1.0 else 0.0

        # 4. Priority / Role Compatibility Score
        priority_score = 1.0

        breakdown = {
            "skill_match": round(skill_score, 4),
            "availability": round(availability_score, 4),
            "workload": round(workload_score, 4),
            "priority": round(priority_score, 4),
        }

        total_score = (
            w.get("skill_match", 0.40) * skill_score
            + w.get("availability", 0.30) * availability_score
            + w.get("workload", 0.20) * workload_score
            + w.get("priority", 0.10) * priority_score
        )

        candidates.append(
            AssignmentCandidate(
                member_id=member.id,
                total_score=round(total_score, 4),
                breakdown=breakdown,
            )
        )

    # Sort descending by total score, with deterministic tie-breaking on member_id
    candidates.sort(key=lambda c: (-c.total_score, c.member_id))
    return candidates
