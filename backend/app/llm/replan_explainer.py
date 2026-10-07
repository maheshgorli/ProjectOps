"""Deterministic Replan Explainer translating computed numbers into executive narratives.

Rule 3: Replans are simulated by the deterministic scheduler.
The LLM explains computed numbers; it never invents them.
"""

from backend.app.llm.prompts import REPLAN_EXPLANATION_SYSTEM_PROMPT
from backend.app.llm.provider import LLMProvider


class ReplanExplainer:
    """Explains deterministic replan adjustments and impact metrics."""

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    async def explain_replan(
        self,
        baseline_version: int,
        proposed_version: int,
        baseline_finish_date: str,
        proposed_finish_date: str,
        finish_date_delta_days: int,
        mitigation_notes: list[str],
    ) -> str:
        """Generate an executive explanation grounded exclusively in computed scheduler facts."""
        notes_bullets = (
            "\n".join(f"- {note}" for note in mitigation_notes)
            if mitigation_notes
            else "- No adjustments made."
        )

        user_prompt = (
            "Please explain this project replan for stakeholders based on computed metrics:\n\n"
            f"- Baseline: Version {baseline_version} (Finish: {baseline_finish_date})\n"
            f"- Proposed: Version {proposed_version} (Finish: {proposed_finish_date})\n"
            f"- Variance: {finish_date_delta_days:+d} working days\n\n"
            f"Computed Mitigation Actions:\n"
            f"{notes_bullets}\n\n"
            "Provide a 2-3 paragraph executive summary explaining the rationale and trade-offs."
        )

        return await self.provider.generate_text(
            prompt=user_prompt,
            system_prompt=REPLAN_EXPLANATION_SYSTEM_PROMPT,
        )
