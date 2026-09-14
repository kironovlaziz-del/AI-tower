"""
Provider adapters: outbound calls to OpenAI/Azure/Anthropic/custom
endpoints. Every test swaps in an httpx.MockTransport via a monkeypatched
_get_client() - no real network call ever leaves the test process.
"""

import httpx
import pytest

from app.services import provider_adapters
from app.services.provider_adapters import ProviderCallError, call_provider


pytestmark = pytest.mark.asyncio


def _mock_client(handler):
    """Build an AsyncClient wired to a MockTransport and patch _get_client
    to return it, so call_provider() never touches the real network."""
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture(autouse=True)
def _reset_singleton_client(monkeypatch):
    # Each test installs its own client via monkeypatch; make sure none of
    # them can accidentally see a leftover singleton from a previous test.
    monkeypatch.setattr(provider_adapters, "_http_client", None)
    yield
    monkeypatch.setattr(provider_adapters, "_http_client", None)


async def test_missing_api_key_is_rejected_before_any_network_call(monkeypatch):
    def handler(request):
        raise AssertionError("should never be called - no api_key")

    monkeypatch.setattr(provider_adapters, "_get_client", lambda: _mock_client(handler))

    with pytest.raises(ProviderCallError, match="No API key"):
        await call_provider("openai", None, None, None, "hi")


async def test_openai_uses_bearer_header_and_default_url(monkeypatch):
    captured = {}

    def handler(request):
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"choices": [{"message": {"content": "hello back"}}]})

    monkeypatch.setattr(provider_adapters, "_get_client", lambda: _mock_client(handler))

    text, raw = await call_provider("openai", "sk-test", None, None, "hi")
    assert text == "hello back"
    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["auth"] == "Bearer sk-test"


async def test_azure_requires_base_url(monkeypatch):
    with pytest.raises(ProviderCallError, match="require a base_url"):
        await call_provider("azure_openai", "sk-test", None, None, "hi")


async def test_azure_uses_api_key_header_not_bearer(monkeypatch):
    captured = {}

    def handler(request):
        captured["api_key_header"] = request.headers.get("api-key")
        captured["auth_header"] = request.headers.get("authorization")
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr(provider_adapters, "_get_client", lambda: _mock_client(handler))

    await call_provider(
        "azure_openai", "az-key", "https://my-resource.openai.azure.com", None, "hi"
    )
    assert captured["api_key_header"] == "az-key"
    assert captured["auth_header"] is None


async def test_anthropic_joins_content_blocks_and_sets_headers(monkeypatch):
    captured = {}

    def handler(request):
        captured["url"] = str(request.url)
        captured["x_api_key"] = request.headers.get("x-api-key")
        captured["version"] = request.headers.get("anthropic-version")
        return httpx.Response(
            200,
            json={"content": [{"text": "Hello, "}, {"text": "world."}]},
        )

    monkeypatch.setattr(provider_adapters, "_get_client", lambda: _mock_client(handler))

    text, raw = await call_provider("anthropic", "sk-ant-test", None, None, "hi")
    assert text == "Hello, world."
    assert captured["url"] == "https://api.anthropic.com/v1/messages"
    assert captured["x_api_key"] == "sk-ant-test"
    assert captured["version"] == "2023-06-01"


async def test_custom_requires_base_url(monkeypatch):
    with pytest.raises(ProviderCallError, match="Custom connections require"):
        await call_provider("custom", "some-key", None, None, "hi")


@pytest.mark.parametrize(
    "response_body,expected_text",
    [
        ({"response": "from response key"}, "from response key"),
        ({"text": "from text key"}, "from text key"),
        ({"response": 0}, 0),  # falsy-but-present value must not be skipped
        ({"text": ""}, ""),  # same for an empty string
        ({"unrelated": "field"}, "{'unrelated': 'field'}"),
    ],
)
async def test_custom_response_shape_handling(monkeypatch, response_body, expected_text):
    def handler(request):
        return httpx.Response(200, json=response_body)

    monkeypatch.setattr(provider_adapters, "_get_client", lambda: _mock_client(handler))

    text, raw = await call_provider(
        "custom", "some-key", "https://my-model.example.com/generate", None, "hi"
    )
    assert text == expected_text


async def test_error_status_code_raises_provider_call_error(monkeypatch):
    def handler(request):
        return httpx.Response(401, text="invalid api key")

    monkeypatch.setattr(provider_adapters, "_get_client", lambda: _mock_client(handler))

    with pytest.raises(ProviderCallError, match="401"):
        await call_provider("openai", "sk-bad", None, None, "hi")


async def test_network_error_is_wrapped_as_provider_call_error(monkeypatch):
    def handler(request):
        raise httpx.ConnectError("simulated network failure")

    monkeypatch.setattr(provider_adapters, "_get_client", lambda: _mock_client(handler))

    with pytest.raises(ProviderCallError, match="Network error"):
        await call_provider("openai", "sk-test", None, None, "hi")


async def test_unexpected_openai_response_shape_raises_provider_call_error(monkeypatch):
    def handler(request):
        return httpx.Response(200, json={"unexpected": "shape"})

    monkeypatch.setattr(provider_adapters, "_get_client", lambda: _mock_client(handler))

    with pytest.raises(ProviderCallError, match="Unexpected response shape"):
        await call_provider("openai", "sk-test", None, None, "hi")


async def test_custom_provider_type_falls_back_to_custom_call(monkeypatch):
    """Any type not explicitly matched (openai/azure_openai/anthropic) is
    treated as a custom endpoint, provided base_url is given."""
    captured = {}

    def handler(request):
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"response": "custom-vendor reply"})

    monkeypatch.setattr(provider_adapters, "_get_client", lambda: _mock_client(handler))

    text, raw = await call_provider(
        "some_other_vendor", "key-123", "https://vendor.example.com/api", None, "hi"
    )
    assert text == "custom-vendor reply"
    assert captured["auth"] == "Bearer key-123"
