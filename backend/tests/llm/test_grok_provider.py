"""Unit tests for GrokProvider (xAI integration) using mocked HTTP transport."""

import json

import httpx
import pytest
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.llm.provider import GrokProvider, get_llm_provider


class SampleSchema(BaseModel):
    summary: str
    points: list[str] = Field(default_factory=list)
    confidence: float = 1.0


@pytest.mark.asyncio
async def test_grok_provider_init_defaults():
    provider = GrokProvider(api_key="xai-test-key")
    assert provider.api_key == "xai-test-key"
    assert provider.model == "grok-2-latest"
    assert provider.base_url == "https://api.x.ai/v1"
    assert provider.timeout == 60.0


@pytest.mark.asyncio
async def test_grok_provider_missing_key_raises():
    provider = GrokProvider(api_key="")
    with pytest.raises(ValueError, match="XAI_API_KEY is not configured"):
        provider._get_headers()


@pytest.mark.asyncio
async def test_grok_generate_text_success():
    captured_request = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        assert request.headers["Authorization"] == "Bearer xai-secret-token"
        body = json.loads(request.read())
        assert body["model"] == "grok-2-latest"
        assert body["messages"] == [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Summarize status."},
        ]
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "All systems operating normally.",
                        }
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://api.x.ai/v1")
    provider = GrokProvider(api_key="xai-secret-token", http_client=client)

    result = await provider.generate_text(
        prompt="Summarize status.",
        system_prompt="You are a helpful assistant.",
    )
    assert result == "All systems operating normally."
    assert captured_request is not None


@pytest.mark.asyncio
async def test_grok_generate_structured_success():
    expected_obj = {
        "summary": "Sprint 1 completed with zero critical defects",
        "points": ["CI/CD passed", "Load tests green"],
        "confidence": 0.98,
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
    client = httpx.AsyncClient(transport=transport, base_url="https://api.x.ai/v1")
    provider = GrokProvider(api_key="xai-secret-token", http_client=client)

    parsed = await provider.generate_structured(
        prompt="Generate sprint summary.",
        schema=SampleSchema,
    )
    assert isinstance(parsed, SampleSchema)
    assert parsed.summary == expected_obj["summary"]
    assert parsed.points == expected_obj["points"]
    assert parsed.confidence == 0.98


@pytest.mark.asyncio
async def test_grok_generate_structured_unwraps_markdown_fences():
    def handler(request: httpx.Request) -> httpx.Response:
        content = """```json
{
    "summary": "Unwrapped from markdown code fence",
    "points": ["Fence handled"],
    "confidence": 1.0
}
```"""
        return httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": content}}]},
        )

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://api.x.ai/v1")
    provider = GrokProvider(api_key="xai-secret-token", http_client=client)

    parsed = await provider.generate_structured(
        prompt="Generate summary.",
        schema=SampleSchema,
    )
    assert parsed.summary == "Unwrapped from markdown code fence"
    assert parsed.points == ["Fence handled"]


@pytest.mark.asyncio
async def test_grok_auth_failure_401():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "Incorrect API key provided"}})

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://api.x.ai/v1")
    provider = GrokProvider(api_key="invalid-key", http_client=client)

    with pytest.raises(ValueError, match="authentication failed \\(401 Unauthorized\\)"):
        await provider.generate_text("Test prompt")


@pytest.mark.asyncio
async def test_grok_rate_limit_429():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "Rate limit reached"}})

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://api.x.ai/v1")
    provider = GrokProvider(api_key="xai-token", http_client=client)

    with pytest.raises(RuntimeError, match="rate limit exceeded \\(429 Too Many Requests\\)"):
        await provider.generate_text("Test prompt")


@pytest.mark.asyncio
async def test_grok_server_error_500():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://api.x.ai/v1")
    provider = GrokProvider(api_key="xai-token", http_client=client)

    with pytest.raises(RuntimeError, match="xAI API request failed with status 500"):
        await provider.generate_text("Test prompt")


@pytest.mark.asyncio
async def test_grok_timeout():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Timeout waiting for server")

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://api.x.ai/v1")
    provider = GrokProvider(api_key="xai-token", http_client=client, timeout=5.0)

    with pytest.raises(TimeoutError, match="xAI API request timed out after 5.0s"):
        await provider.generate_text("Test prompt")


@pytest.mark.asyncio
async def test_grok_malformed_envelope():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "payload"})

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://api.x.ai/v1")
    provider = GrokProvider(api_key="xai-token", http_client=client)

    with pytest.raises(ValueError, match="Malformed response payload from xAI API"):
        await provider.generate_text("Test prompt")


@pytest.mark.asyncio
async def test_grok_structured_invalid_json():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": "not-valid-json"}}]},
        )

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://api.x.ai/v1")
    provider = GrokProvider(api_key="xai-token", http_client=client)

    with pytest.raises(ValueError, match="Invalid JSON returned by xAI API"):
        await provider.generate_structured("Prompt", SampleSchema)


@pytest.mark.asyncio
async def test_grok_structured_schema_mismatch():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": json.dumps({"wrong_field": 123}),
                        }
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://api.x.ai/v1")
    provider = GrokProvider(api_key="xai-token", http_client=client)

    with pytest.raises(ValueError, match="xAI output failed schema validation for SampleSchema"):
        await provider.generate_structured("Prompt", SampleSchema)


@pytest.mark.asyncio
async def test_grok_secret_not_leaked_in_exceptions():
    secret_key = "super-secret-xai-key-do-not-leak"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"})

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://api.x.ai/v1")
    provider = GrokProvider(api_key=secret_key, http_client=client)

    try:
        await provider.generate_text("Test prompt")
    except ValueError as exc:
        assert secret_key not in str(exc)


@pytest.mark.asyncio
async def test_factory_grok_selection_and_validation(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "llm_provider", "grok")
    monkeypatch.setattr(settings, "xai_api_key", None)
    monkeypatch.delenv("XAI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="XAI_API_KEY is not configured"):
        get_llm_provider()

    # When key is configured, factory successfully returns GrokProvider
    monkeypatch.setattr(settings, "xai_api_key", "valid-xai-key")
    provider = get_llm_provider()
    assert isinstance(provider, GrokProvider)
    assert provider.api_key == "valid-xai-key"

    # Also test 'xai' alias
    monkeypatch.setattr(settings, "llm_provider", "xai")
    provider_alias = get_llm_provider()
    assert isinstance(provider_alias, GrokProvider)
