"""Provider-agnostic LLM interface with Claude and Mock implementations.

Domain Decision 4: LLM access goes through a provider-agnostic interface
in backend/app/llm (default provider: Claude).
"""

import json
import os
import re
from typing import Protocol, TypeVar

from pydantic import BaseModel

from backend.app.core.config import settings

T = TypeVar("T", bound=BaseModel)


class LLMProvider(Protocol):
    """Protocol defining the provider-agnostic LLM interface."""

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        """Generate free-form text response."""
        ...

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        system_prompt: str | None = None,
    ) -> T:
        """Generate structured response strictly validated against Pydantic schema."""
        ...


class ClaudeProvider:
    """Claude LLM implementation using Anthropic API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or settings.anthropic_api_key or ""
        self.model = model or settings.anthropic_model
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError("ANTHROPIC_API_KEY is not configured.")
            import anthropic

            self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
        return self._client

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        client = self._get_client()
        messages = [{"role": "user", "content": prompt}]
        response = await client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=system_prompt or "",
            messages=messages,
        )
        # Extract text block
        text_blocks = [b.text for b in response.content if hasattr(b, "text")]
        return "".join(text_blocks)

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        system_prompt: str | None = None,
    ) -> T:
        client = self._get_client()
        json_schema = json.dumps(schema.model_json_schema(), indent=2)
        full_system = (
            system_prompt or ""
        ) + f"\nYou must reply ONLY with a valid JSON object matching this schema:\n{json_schema}"
        messages = [{"role": "user", "content": prompt}]
        response = await client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=full_system,
            messages=messages,
        )
        text_blocks = [b.text for b in response.content if hasattr(b, "text")]
        raw_text = "".join(text_blocks).strip()

        # Extract JSON from potential markdown code fences
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text)
        json_str = match.group(1) if match else raw_text
        parsed_dict = json.loads(json_str)
        return schema.model_validate(parsed_dict)


class MockLLMProvider:
    """Deterministic, offline mock provider for automated tests and fallback."""

    def __init__(self, canned_text: str | None = None) -> None:
        self.canned_text = canned_text

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        if self.canned_text:
            return self.canned_text
        return (
            "Executive Replan Summary: The deterministic scheduler rebalanced assignments "
            "to resolve member over-allocation and maintained critical path feasibility."
        )

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        system_prompt: str | None = None,
    ) -> T:
        # Default mock structured goal decomposition payload
        schema_name = schema.__name__
        if "DecomposedGoal" in schema_name or "Goal" in schema_name:
            mock_data = {
                "tasks": [
                    {
                        "id": "TASK-1",
                        "title": "Architectural Design and Schema Spec",
                        "description": "Establish data models and interface boundaries.",
                        "estimated_hours": 16.0,
                    },
                    {
                        "id": "TASK-2",
                        "title": "Core Implementation",
                        "description": "Implement business logic and domain engine.",
                        "estimated_hours": 24.0,
                    },
                    {
                        "id": "TASK-3",
                        "title": "Integration Testing and Verification",
                        "description": "Write and run comprehensive test suite.",
                        "estimated_hours": 16.0,
                    },
                ],
                "dependencies": [
                    {
                        "predecessor_id": "TASK-1",
                        "successor_id": "TASK-2",
                        "dep_type": "FINISH_TO_START",
                        "lag_days": 0,
                    },
                    {
                        "predecessor_id": "TASK-2",
                        "successor_id": "TASK-3",
                        "dep_type": "FINISH_TO_START",
                        "lag_days": 0,
                    },
                ],
            }
            return schema.model_validate(mock_data)

        # Fallback empty construction
        return schema.model_validate({})


def get_llm_provider() -> LLMProvider:
    """
    Provider factory returning the configured LLMProvider.

    Enforces:
    - If LLM_PROVIDER is 'claude', ANTHROPIC_API_KEY is required; raises ValueError if missing.
    - 'mock' is allowed only when explicitly set via LLM_PROVIDER=mock.
    - Unknown providers raise ValueError.
    """
    provider_type = (settings.llm_provider or "").lower().strip()
    if provider_type == "mock":
        return MockLLMProvider()
    if provider_type == "claude":
        api_key = settings.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is not configured. "
                "Set ANTHROPIC_API_KEY or explicitly set LLM_PROVIDER=mock for development."
            )
        return ClaudeProvider(api_key=api_key, model=settings.anthropic_model)
    raise ValueError(f"Unsupported LLM_PROVIDER '{provider_type}'. Must be 'claude' or 'mock'.")
