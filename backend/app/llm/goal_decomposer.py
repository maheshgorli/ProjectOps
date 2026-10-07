"""Goal decomposition engine with strict schema validation and DAG verification.

Rule 2: LLMs only do goal decomposition, task descriptions, strategy ideas, explanations.
LLM output never writes to the DB directly. It must pass schema validation (Pydantic)
and domain validators first.
"""

from backend.app.domain.graph import CycleDetectedError, TaskGraph, TaskNotFoundError
from backend.app.domain.models import Dependency
from backend.app.llm.prompts import GOAL_DECOMPOSITION_SYSTEM_PROMPT
from backend.app.llm.provider import LLMProvider
from backend.app.llm.sanitizer import sanitize_untrusted_text
from backend.app.schemas.ai import (
    DecomposedGoalSchema,
    GoalDecompositionResponse,
)


class GoalDecomposer:
    """Decomposes goals into tasks with strict Pydantic and DAG validation."""

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    async def decompose_goal(
        self,
        goal: str,
        context: str = "",
    ) -> GoalDecompositionResponse:
        """
        Decompose an untrusted goal description into structured tasks.

        Guarantees:
        1. Input is sanitized to prevent prompt injection.
        2. Output is parsed into DecomposedGoalSchema (Pydantic v2).
        3. Precedence dependencies are verified via TaskGraph (no cycles).
        """
        sanitized_goal = sanitize_untrusted_text(goal, data_type="project_goal")
        sanitized_context = (
            sanitize_untrusted_text(context, data_type="project_context") if context else ""
        )

        user_prompt = (
            f"Please decompose the following engineering goal into tasks and dependencies:\n\n"
            f"{sanitized_goal}\n\n"
            f"{sanitized_context}"
        )

        # 1. Structured generation
        decomposed: DecomposedGoalSchema = await self.provider.generate_structured(
            prompt=user_prompt,
            schema=DecomposedGoalSchema,
            system_prompt=GOAL_DECOMPOSITION_SYSTEM_PROMPT,
        )

        # 2. Domain Graph Validation
        task_ids = [t.id for t in decomposed.tasks]
        domain_deps = [
            Dependency(
                predecessor_id=d.predecessor_id,
                successor_id=d.successor_id,
                dep_type=d.dep_type,
                lag_days=d.lag_days,
            )
            for d in decomposed.dependencies
        ]

        try:
            graph = TaskGraph(tasks=task_ids, dependencies=domain_deps)
            graph.validate_dag()
            # Test topological sorting to confirm complete connectivity
            graph.topological_sort()
        except (CycleDetectedError, TaskNotFoundError) as exc:
            raise ValueError(f"LLM produced invalid dependency graph: {exc}") from exc

        total_hours = sum(t.estimated_hours for t in decomposed.tasks)

        return GoalDecompositionResponse(
            goal=goal,
            tasks=decomposed.tasks,
            dependencies=decomposed.dependencies,
            estimated_total_hours=total_hours,
            is_valid_dag=True,
        )
