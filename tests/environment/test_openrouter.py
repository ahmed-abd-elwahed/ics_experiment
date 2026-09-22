from __future__ import annotations

import json

import httpx
import pytest
import respx

from medsim.config import load_settings
from medsim.errors import REDACTED, ConfigError, LLMError
from medsim.llm.openrouter import OpenRouterClient
from medsim.models import ChatMessage
from tests.conftest import MODEL, TEST_KEY, completion_body, load_fixture, make_settings

BASE = "https://openrouter.ai/api/v1"
MESSAGES = [ChatMessage(role="user", content="hello")]
SCHEMA_FORMAT = {"type": "json_schema", "json_schema": {"name": "x", "strict": True, "schema": {}}}


def _client(**overrides: object) -> OpenRouterClient:
    return OpenRouterClient(make_settings(**overrides), sleep=lambda _: None)


def test_complete_sends_auth_attribution_and_parses_usage(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post(f"{BASE}/chat/completions").mock(
        return_value=httpx.Response(
            200, json=completion_body('{"ok": true}', prompt_tokens=11, completion_tokens=3)
        )
    )
    client = _client(openrouter_http_referer="https://example.org/medsim")
    response = client.complete(
        MESSAGES, response_format=SCHEMA_FORMAT, temperature=0.0, max_tokens=50
    )

    request = route.calls.last.request
    assert request.headers["Authorization"] == f"Bearer {TEST_KEY}"
    assert request.headers["HTTP-Referer"] == "https://example.org/medsim"
    assert request.headers["X-OpenRouter-Title"] == "medsim"
    assert request.headers["X-Title"] == "medsim"
    body = json.loads(request.content)
    assert body["model"] == MODEL
    assert body["temperature"] == 0.0
    assert body["seed"] == 7
    assert body["response_format"] == SCHEMA_FORMAT
    assert body["provider"] == {"require_parameters": True}
    assert response.content == '{"ok": true}'
    assert (response.usage.prompt_tokens, response.usage.completion_tokens) == (11, 3)
    assert response.latency_ms >= 0


def test_per_call_model_override(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post(f"{BASE}/chat/completions").mock(
        return_value=httpx.Response(200, json=completion_body("{}", model="other/model"))
    )
    response = _client().complete(
        MESSAGES, response_format=None, temperature=0.3, max_tokens=5, model="other/model"
    )
    body = json.loads(route.calls.last.request.content)
    assert body["model"] == "other/model"
    assert "response_format" not in body
    assert response.model == "other/model"


def test_retries_429_then_succeeds(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post(f"{BASE}/chat/completions").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "0"}),
            httpx.Response(200, json=completion_body("{}")),
        ]
    )
    _client().complete(MESSAGES, response_format=None, temperature=0, max_tokens=5)
    assert route.call_count == 2


def test_http_error_message_redacts_key(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{BASE}/chat/completions").mock(
        return_value=httpx.Response(401, json={"error": {"message": f"bad key {TEST_KEY}"}})
    )
    with pytest.raises(LLMError) as excinfo:
        _client().complete(MESSAGES, response_format=None, temperature=0, max_tokens=5)
    assert TEST_KEY not in str(excinfo.value)
    assert REDACTED in str(excinfo.value)
    assert excinfo.value.__cause__ is None


def test_transport_error_redacts_key(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{BASE}/chat/completions").mock(
        side_effect=httpx.ConnectError(f"connection to {TEST_KEY} failed")
    )
    with pytest.raises(LLMError) as excinfo:
        _client().complete(MESSAGES, response_format=None, temperature=0, max_tokens=5)
    assert TEST_KEY not in str(excinfo.value)
    assert excinfo.value.__suppress_context__  # original exception (with request) not chained


def test_error_object_in_200_body_raises(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{BASE}/chat/completions").mock(
        return_value=httpx.Response(200, json={"error": {"code": 502, "message": "upstream"}})
    )
    with pytest.raises(LLMError, match="upstream"):
        _client().complete(MESSAGES, response_format=None, temperature=0, max_tokens=5)


def test_verify_models_accepts_recorded_slug(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(f"{BASE}/models").mock(
        return_value=httpx.Response(
            200, json=load_fixture("openrouter_models_deepseek_subset.json")
        )
    )
    _client().verify_models()


def test_verify_models_unknown_slug_lists_close_matches(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(f"{BASE}/models").mock(
        return_value=httpx.Response(
            200, json=load_fixture("openrouter_models_deepseek_subset.json")
        )
    )
    with pytest.raises(ConfigError) as excinfo:
        _client(default_model="deepseek/deepseek-v4-flash-0730").verify_models()
    message = str(excinfo.value)
    assert "deepseek/deepseek-v4-flash-0730" in message
    assert MODEL in message


def test_response_format_downgrades_without_structured_outputs(
    respx_mock: respx.MockRouter,
) -> None:
    respx_mock.get(f"{BASE}/models").mock(
        return_value=httpx.Response(
            200, json={"data": [{"id": "acme/basic", "supported_parameters": ["response_format"]}]}
        )
    )
    route = respx_mock.post(f"{BASE}/chat/completions").mock(
        return_value=httpx.Response(200, json=completion_body("{}", model="acme/basic"))
    )
    client = _client(default_model="acme/basic")
    client.verify_models()
    client.complete(MESSAGES, response_format=SCHEMA_FORMAT, temperature=0, max_tokens=5)
    body = json.loads(route.calls.last.request.content)
    assert body["response_format"] == {"type": "json_object"}
    assert "seed" not in body  # not in the model's supported_parameters


def test_missing_key_fails_fast_with_actionable_message() -> None:
    with pytest.raises(ConfigError, match=r"OPENROUTER_API_KEY.*\.env"):
        load_settings(_env_file=None)
    with pytest.raises(ConfigError, match="empty"):
        OpenRouterClient(make_settings(openrouter_api_key="   "))


def test_settings_never_expose_key() -> None:
    settings = make_settings()
    assert TEST_KEY not in repr(settings)
    assert TEST_KEY not in settings.model_dump_json()


def test_reply_cut_off_by_token_limit_is_returned_for_retry(respx_mock: respx.MockRouter) -> None:
    body = completion_body(" ", completion_tokens=50)
    body["choices"][0]["finish_reason"] = "length"
    respx_mock.post(f"{BASE}/chat/completions").mock(return_value=httpx.Response(200, json=body))
    response = _client().complete(MESSAGES, response_format=None, temperature=0, max_tokens=50)
    assert response.finish_reason == "length"
    assert response.content.strip() == ""


def test_empty_reply_that_was_not_cut_off_raises(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{BASE}/chat/completions").mock(
        return_value=httpx.Response(200, json=completion_body("   "))
    )
    with pytest.raises(LLMError, match="empty message content"):
        _client().complete(MESSAGES, response_format=None, temperature=0, max_tokens=50)
