"""Unit tests for GroqProvider (GroqCloud integration) using mocked HTTP transport."""

import json

import httpx
import pytest
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.llm.provider import GroqProvider, get_llm_provider


class SamplePlanSchema(BaseModel):
    summary: str
    deliverables: list[str] = Field(default_factory=list)
    total_hours: float = 0.0


@pytest.mark.asyncio
async def test_groq_provider_init_defaults():
    provider = GroqProvider(api_key="gsk-test-key")
    assert provider.api_key == "gsk-test-key"
    assert provider.model == "openai/gpt-oss-120b"
    assert provider.base_url == "https://api.groq.com/openai/v1"
    assert provider.timeout == 60.0


@pytest.mark.asyncio
async def test_groq_provider_missing_key_raises():
    provider = GroqProvider(api_key="")
    with pytest.raises(ValueError, match="GROQ_API_KEY is not configured"):
        provider._get_headers()


@pytest.mark.asyncio
async def test_groq_generate_text_success():
    captured_request = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        assert request.headers["Authorization"] == "Bearer gsk-secret-token"
        body = json.loads(request.read())
        assert body["model"] == "openai/gpt-oss-120b"
        assert body["messages"] == [
            {"role": "system", "content": "You are a software architect."},
            {"role": "user", "content": "Explain project scope."},
        ]
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-groq-test",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Project architecture is decomposed and ready.",
                        }
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://api.groq.com/openai/v1")
    provider = GroqProvider(api_key="gsk-secret-token", http_client=client)

    result = await provider.generate_text(
        prompt="Explain project scope.",
        system_prompt="You are a software architect.",
    )
    assert result == "Project architecture is decomposed and ready."
    assert captured_request is not None


@pytest.mark.asyncio
async def test_groq_generate_structured_success():
    expected_obj = {
        "summary": "Full-stack cloud delivery plan",
        "deliverables": ["API Gateway", "Auth Service", "Worker Engine"],
        "total_hours": 120.0,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.read())
        assert body["response_format"] == {"type": "json_object"}
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(expected_obj),
                        }
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://api.groq.com/openai/v1")
    provider = GroqProvider(api_key="gsk-secret-token", http_client=client)

    parsed = await provider.generate_structured(
        prompt="Generate full plan.",
        schema=SamplePlanSchema,
    )
    assert isinstance(parsed, SamplePlanSchema)
    assert parsed.summary == expected_obj["summary"]
    assert len(parsed.deliverables) == 3
    assert parsed.total_hours == 120.0


@pytest.mark.asyncio
async def test_groq_generate_structured_unwraps_markdown_fences():
    def handler(request: httpx.Request) -> httpx.Response:
        content = """```json
{
    "summary": "Unwrapped from Groq markdown block",
    "deliverables": ["CI/CD Pipeline"],
    "total_hours": 40.0
}
```"""
        return httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": content}}]},
        )

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://api.groq.com/openai/v1")
    provider = GroqProvider(api_key="gsk-secret-token", http_client=client)

    parsed = await provider.generate_structured(
        prompt="Generate plan.",
        schema=SamplePlanSchema,
    )
    assert parsed.summary == "Unwrapped from Groq markdown block"
    assert parsed.deliverables == ["CI/CD Pipeline"]
    assert parsed.total_hours == 40.0


@pytest.mark.asyncio
async def test_groq_auth_failure_401():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "Invalid API Key"}})

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://api.groq.com/openai/v1")
    provider = GroqProvider(api_key="invalid-groq-key", http_client=client)

    with pytest.raises(ValueError, match="Groq API authentication failed \\(401 Unauthorized\\)"):
        await provider.generate_text("Test prompt")


@pytest.mark.asyncio
async def test_groq_rate_limit_429():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "Rate limit exceeded"}})

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://api.groq.com/openai/v1")
    provider = GroqProvider(api_key="gsk-token", http_client=client)

    with pytest.raises(
        RuntimeError, match="Groq API rate limit exceeded \\(429 Too Many Requests\\)"
    ):
        await provider.generate_text("Test prompt")


@pytest.mark.asyncio
async def test_groq_server_error_500():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Groq Server Error")

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://api.groq.com/openai/v1")
    provider = GroqProvider(api_key="gsk-token", http_client=client)

    with pytest.raises(RuntimeError, match="Groq API request failed with status 500"):
        await provider.generate_text("Test prompt")


@pytest.mark.asyncio
async def test_groq_timeout():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Timeout waiting for Groq LPU response")

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://api.groq.com/openai/v1")
    provider = GroqProvider(api_key="gsk-token", http_client=client, timeout=3.0)

    with pytest.raises(TimeoutError, match="Groq API request timed out after 3.0s"):
        await provider.generate_text("Test prompt")


@pytest.mark.asyncio
async def test_groq_malformed_envelope():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": []})

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://api.groq.com/openai/v1")
    provider = GroqProvider(api_key="gsk-token", http_client=client)

    with pytest.raises(ValueError, match="Malformed response payload from Groq API"):
        await provider.generate_text("Test prompt")


@pytest.mark.asyncio
async def test_groq_structured_invalid_json():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": "not-valid-json"}}]},
        )

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://api.groq.com/openai/v1")
    provider = GroqProvider(api_key="gsk-token", http_client=client)

    with pytest.raises(ValueError, match="Invalid JSON returned by Groq API"):
        await provider.generate_structured("Prompt", SamplePlanSchema)


@pytest.mark.asyncio
async def test_groq_secret_not_leaked_in_exceptions():
    secret_key = "gsk_super_secret_groq_key_do_not_leak"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"})

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://api.groq.com/openai/v1")
    provider = GroqProvider(api_key=secret_key, http_client=client)

    try:
        await provider.generate_text("Test prompt")
    except ValueError as exc:
        assert secret_key not in str(exc)


@pytest.mark.asyncio
async def test_factory_groq_selection_and_validation(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "groq_api_key", None)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(ValueError, match="GROQ_API_KEY is not configured"):
        get_llm_provider()

    # When key is configured, factory successfully returns GroqProvider
    monkeypatch.setattr(settings, "groq_api_key", "gsk-valid-key")
    provider = get_llm_provider()
    assert isinstance(provider, GroqProvider)
    assert provider.api_key == "gsk-valid-key"
    assert provider.model == "openai/gpt-oss-120b"
