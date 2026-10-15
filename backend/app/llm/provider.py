"""Provider-agnostic LLM interface with Claude and Mock implementations.

Domain Decision 4: LLM access goes through a provider-agnostic interface
in backend/app/llm (default provider: Claude).
"""

import json
import os
import re
from typing import Protocol, TypeVar

import httpx
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


class GrokProvider:
    """Grok LLM implementation using official xAI API (OpenAI-compatible)."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 60.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key or settings.xai_api_key or os.getenv("XAI_API_KEY", "")
        self.model = model or settings.xai_model or os.getenv("XAI_MODEL", "grok-2-latest")
        self.base_url = (
            base_url or settings.xai_base_url or os.getenv("XAI_BASE_URL", "https://api.x.ai/v1")
        ).rstrip("/")
        self.timeout = timeout
        self._http_client = http_client

    def _get_headers(self) -> dict[str, str]:
        if not self.api_key:
            raise ValueError(
                "XAI_API_KEY is not configured. "
                "Set XAI_API_KEY or explicitly set LLM_PROVIDER=mock for development."
            )
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._http_client

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        headers = self._get_headers()
        client = self._get_client()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
        }
        try:
            response = await client.post("/chat/completions", json=payload, headers=headers)

        except httpx.TimeoutException as exc:
            raise TimeoutError(f"xAI API request timed out after {self.timeout}s") from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"xAI API connection error: {exc.__class__.__name__}") from exc

        if response.status_code == 401:
            raise ValueError(
                "xAI API authentication failed (401 Unauthorized). Verify XAI_API_KEY."
            )
        if response.status_code == 429:
            raise RuntimeError("xAI API rate limit exceeded (429 Too Many Requests).")
        if response.is_error:
            raise RuntimeError(
                f"xAI API request failed with status {response.status_code}: {response.text}"
            )

        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"Malformed response payload from xAI API: {exc}") from exc

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        system_prompt: str | None = None,
    ) -> T:
        client = self._get_client()
        json_schema = json.dumps(schema.model_json_schema(), indent=2)
        schema_instruction = (
            "You must reply ONLY with a valid JSON object strictly matching this JSON schema:\n"
            f"{json_schema}\n"
            "Do not include any text before or after the JSON object."
        )

        full_system = (
            f"{system_prompt}\n\n{schema_instruction}" if system_prompt else schema_instruction
        )

        headers = self._get_headers()
        messages = [
            {"role": "system", "content": full_system},
            {"role": "user", "content": prompt},
        ]
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        try:
            response = await client.post("/chat/completions", json=payload, headers=headers)

        except httpx.TimeoutException as exc:
            raise TimeoutError(f"xAI API request timed out after {self.timeout}s") from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"xAI API connection error: {exc.__class__.__name__}") from exc

        if response.status_code == 401:
            raise ValueError(
                "xAI API authentication failed (401 Unauthorized). Verify XAI_API_KEY."
            )
        if response.status_code == 429:
            raise RuntimeError("xAI API rate limit exceeded (429 Too Many Requests).")
        if response.is_error:
            raise RuntimeError(
                f"xAI API request failed with status {response.status_code}: {response.text}"
            )

        data = response.json()
        try:
            raw_text = data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"Malformed response payload from xAI API: {exc}") from exc

        # Extract JSON from potential markdown code fences
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text)
        json_str = match.group(1).strip() if match else raw_text

        try:
            parsed_dict = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON returned by xAI API: {exc}") from exc

        try:
            return schema.model_validate(parsed_dict)
        except Exception as exc:
            raise ValueError(
                f"xAI output failed schema validation for {schema.__name__}: {exc}"
            ) from exc


class GroqProvider:
    """Groq LLM implementation using official GroqCloud API (OpenAI-compatible)."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 60.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = (
            api_key
            if api_key is not None
            else (settings.groq_api_key or os.getenv("GROQ_API_KEY", ""))
        )
        self.model = model or settings.groq_model or os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        self.base_url = (
            base_url
            or settings.groq_base_url
            or os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
        ).rstrip("/")
        self.timeout = timeout
        self._http_client = http_client

    def _get_headers(self) -> dict[str, str]:
        if not self.api_key:
            raise ValueError(
                "GROQ_API_KEY is not configured. "
                "Set GROQ_API_KEY or explicitly set LLM_PROVIDER=mock for development."
            )
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._http_client

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        headers = self._get_headers()
        client = self._get_client()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
        }
        try:
            response = await client.post("/chat/completions", json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise TimeoutError(f"Groq API request timed out after {self.timeout}s") from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"Groq API connection error: {exc.__class__.__name__}") from exc

        if response.status_code == 401:
            raise ValueError(
                "Groq API authentication failed (401 Unauthorized). Verify GROQ_API_KEY."
            )
        if response.status_code == 429:
            raise RuntimeError("Groq API rate limit exceeded (429 Too Many Requests).")
        if response.is_error:
            raise RuntimeError(
                f"Groq API request failed with status {response.status_code}: {response.text}"
            )

        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"Malformed response payload from Groq API: {exc}") from exc

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        system_prompt: str | None = None,
    ) -> T:
        client = self._get_client()
        json_schema = json.dumps(schema.model_json_schema(), indent=2)
        schema_instruction = (
            "You must reply ONLY with a valid JSON object strictly matching this JSON schema:\n"
            f"{json_schema}\n"
            "Do not include any text before or after the JSON object."
        )
        full_system = (
            f"{system_prompt}\n\n{schema_instruction}" if system_prompt else schema_instruction
        )

        headers = self._get_headers()
        messages = [
            {"role": "system", "content": full_system},
            {"role": "user", "content": prompt},
        ]
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        try:
            response = await client.post("/chat/completions", json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise TimeoutError(f"Groq API request timed out after {self.timeout}s") from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"Groq API connection error: {exc.__class__.__name__}") from exc

        if response.status_code == 401:
            raise ValueError(
                "Groq API authentication failed (401 Unauthorized). Verify GROQ_API_KEY."
            )
        if response.status_code == 429:
            raise RuntimeError("Groq API rate limit exceeded (429 Too Many Requests).")
        if response.is_error:
            raise RuntimeError(
                f"Groq API request failed with status {response.status_code}: {response.text}"
            )

        data = response.json()
        try:
            raw_text = data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"Malformed response payload from Groq API: {exc}") from exc

        # Extract JSON from potential markdown code fences
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text)
        json_str = match.group(1).strip() if match else raw_text

        try:
            parsed_dict = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON returned by Groq API: {exc}") from exc

        try:
            return schema.model_validate(parsed_dict)
        except Exception as exc:
            raise ValueError(
                f"Groq output failed schema validation for {schema.__name__}: {exc}"
            ) from exc


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
    - If LLM_PROVIDER is 'groq', GROQ_API_KEY is required; raises ValueError if missing.
    - If LLM_PROVIDER is 'grok' or 'xai', XAI_API_KEY is required; raises ValueError if missing.
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
    if provider_type == "groq":
        api_key = settings.groq_api_key or os.getenv("GROQ_API_KEY", "")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY is not configured. "
                "Set GROQ_API_KEY or explicitly set LLM_PROVIDER=mock for development."
            )
        return GroqProvider(
            api_key=api_key,
            model=settings.groq_model,
            base_url=settings.groq_base_url,
        )
    if provider_type in ("grok", "xai"):
        api_key = settings.xai_api_key or os.getenv("XAI_API_KEY", "")
        if not api_key:
            raise ValueError(
                "XAI_API_KEY is not configured. "
                "Set XAI_API_KEY or explicitly set LLM_PROVIDER=mock for development."
            )
        return GrokProvider(
            api_key=api_key,
            model=settings.xai_model,
            base_url=settings.xai_base_url,
        )
    raise ValueError(
        f"Unsupported LLM_PROVIDER '{provider_type}'. Must be 'claude', 'groq', 'grok', or 'mock'."
    )
