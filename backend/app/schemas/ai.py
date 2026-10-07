"""Pydantic v2 schemas for AI goal decomposition and replan explanations."""

from pydantic import BaseModel, Field

from backend.app.schemas.plan import DependencySchema


class DecomposedTaskSchema(BaseModel):
    """An individual engineering task produced by goal decomposition."""

    id: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    estimated_hours: float = Field(default=8.0, gt=0, le=200)


class DecomposedGoalSchema(BaseModel):
    """Structured output expected from the LLM during goal decomposition."""

    tasks: list[DecomposedTaskSchema] = Field(default_factory=list)
    dependencies: list[DependencySchema] = Field(default_factory=list)


class GoalDecompositionRequest(BaseModel):
    """User request to decompose a high-level project goal."""

    goal: str = Field(..., min_length=5, max_length=2000)
    context: str = Field(default="", max_length=4000)


class GoalDecompositionResponse(BaseModel):
    """Validated response from goal decomposition."""

    goal: str
    tasks: list[DecomposedTaskSchema]
    dependencies: list[DependencySchema]
    estimated_total_hours: float
    is_valid_dag: bool


class ReplanExplanationRequest(BaseModel):
    """Request to generate an executive explanation for a simulated replan."""

    baseline_version: int
    proposed_version: int
    baseline_finish_date: str
    proposed_finish_date: str
    finish_date_delta_days: int
    mitigation_notes: list[str] = Field(default_factory=list)


class ReplanExplanationResponse(BaseModel):
    """Executive explanation generated from deterministic replan metrics."""

    project_id: str
    explanation: str
