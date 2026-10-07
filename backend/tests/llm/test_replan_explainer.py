"""Unit tests for ReplanExplainer."""

import pytest

from backend.app.llm.provider import MockLLMProvider
from backend.app.llm.replan_explainer import ReplanExplainer


class CapturingMockProvider(MockLLMProvider):
    """Mock provider that records the exact prompt it was called with."""

    def __init__(self):
        super().__init__()
        self.recorded_prompt = ""

    async def generate_text(self, prompt, system_prompt=None):
        self.recorded_prompt = prompt
        return "Explanation based on exact metrics."


@pytest.mark.asyncio
async def test_replan_explainer_passes_exact_metrics():
    provider = CapturingMockProvider()
    explainer = ReplanExplainer(provider)

    result = await explainer.explain_replan(
        baseline_version=1,
        proposed_version=2,
        baseline_finish_date="2026-10-15",
        proposed_finish_date="2026-10-18",
        finish_date_delta_days=3,
        mitigation_notes=["Reassigned task T2 from Alice to Bob"],
    )

    assert result == "Explanation based on exact metrics."
    assert "Version 1" in provider.recorded_prompt
    assert "Version 2" in provider.recorded_prompt
    assert "2026-10-15" in provider.recorded_prompt
    assert "2026-10-18" in provider.recorded_prompt
    assert "+3 working days" in provider.recorded_prompt
    assert "Reassigned task T2 from Alice to Bob" in provider.recorded_prompt
