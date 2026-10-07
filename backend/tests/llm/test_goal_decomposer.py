"""Unit tests for GoalDecomposer, Pydantic validation, and DAG verification."""

import pytest

from backend.app.domain.models import DependencyType
from backend.app.llm.goal_decomposer import GoalDecomposer
from backend.app.llm.provider import MockLLMProvider
from backend.app.schemas.ai import (
    DecomposedGoalSchema,
    DecomposedTaskSchema,
    DependencySchema,
)


@pytest.mark.asyncio
async def test_goal_decomposer_success():
    provider = MockLLMProvider()
    decomposer = GoalDecomposer(provider)

    result = await decomposer.decompose_goal("Implement OAuth2 authentication flow")
    assert result.goal == "Implement OAuth2 authentication flow"
    assert len(result.tasks) == 3
    assert len(result.dependencies) == 2
    assert result.estimated_total_hours == 56.0
    assert result.is_valid_dag is True


class BadCycleProvider(MockLLMProvider):
    """Mock provider that simulates an LLM hallucinating a circular dependency."""

    async def generate_structured(self, prompt, schema, system_prompt=None):
        return DecomposedGoalSchema(
            tasks=[
                DecomposedTaskSchema(id="A", title="Task A", estimated_hours=8.0),
                DecomposedTaskSchema(id="B", title="Task B", estimated_hours=8.0),
            ],
            dependencies=[
                DependencySchema(
                    predecessor_id="A",
                    successor_id="B",
                    dep_type=DependencyType.FINISH_TO_START,
                ),
                DependencySchema(
                    predecessor_id="B",
                    successor_id="A",  # Cycle!
                    dep_type=DependencyType.FINISH_TO_START,
                ),
            ],
        )


@pytest.mark.asyncio
async def test_goal_decomposer_catches_cycle_hallucination():
    bad_provider = BadCycleProvider()
    decomposer = GoalDecomposer(bad_provider)

    # Must raise ValueError and protect domain integrity
    with pytest.raises(ValueError, match="Circular dependency detected"):
        await decomposer.decompose_goal("Bad circular goal")
