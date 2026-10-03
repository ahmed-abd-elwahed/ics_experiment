from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httpx
import pytest
import respx

from medsim.config import DEFAULT_MODEL, OpenRouterSearchSettings
from medsim.errors import REDACTED, LLMError
from medsim.llm.batch import is_batch_model, sync_model
from medsim.llm.openrouter import OpenRouterClient
from medsim.models import ChatMessage
from medsim.retrieval.openrouter_search import OpenRouterSearchRetriever
from tests.conftest import TEST_KEY, completion_body, load_fixture, make_settings

BASE = "https://openrouter.ai/api/v1"
BATCH_ID = "batch-1"
SCHEMA_FORMAT = {"type": "json_schema", "json_schema": {"name": "x", "strict": True, "schema": {}}}


def _client(**overrides: Any) -> OpenRouterClient:
    values = {"default_model": DEFAULT_MODEL, "batch_window_s": 0.2, **overrides}
    return OpenRouterClient(make_settings(**values), sleep=lambda _: None)


def _batch(status: str, **fields: Any) -> dict[str, Any]:
    return {"id": BATCH_ID, "object": "batch", "status": status, "results": None, "error": None,
            **fields}  # fmt: skip


def _result(custom_id: str, content: str, **usage: Any) -> dict[str, Any]:
    body = completion_body(content, model="deepseek/deepseek-v4.1-flash-20260910")
    body["usage"].update(usage)
    return {"id": f"r-{custom_id}", "custom_id": custom_id, "error": None,
            "response": {"status_code": 200, "request_id": "x", "body": body}}  # fmt: skip


def _echo(submit: respx.Route) -> list[dict[str, Any]]:
    """A result per submitted request, answering with that request's user message."""
    requests = json.loads(submit.calls.last.request.content)["requests"]
    return [_result(r["custom_id"], r["body"]["messages"][0]["content"]) for r in requests]


def _complete(client: OpenRouterClient, text: str = "hello", **kwargs: Any) -> Any:
    values = {"response_format": None, "temperature": 0.2, "max_tokens": 50, **kwargs}
    return client.complete([ChatMessage(role="user", content=text)], **values)


def test_default_model_is_the_batch_endpoint() -> None:
    assert DEFAULT_MODEL == "deepseek/deepseek-v4.1-flash:batch"
    assert is_batch_model(DEFAULT_MODEL) and not is_batch_model(sync_model(DEFAULT_MODEL))
    assert sync_model(DEFAULT_MODEL) == "deepseek/deepseek-v4.1-flash"


def test_verify_models_accepts_the_default(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(f"{BASE}/models").mock(
        return_value=httpx.Response(
            200, json=load_fixture("openrouter_models_deepseek_subset.json")
        )
    )
    _client().verify_models()


def test_batch_model_is_submitted_and_polled(respx_mock: respx.MockRouter) -> None:
    submit = respx_mock.post(f"{BASE}/batches").mock(
        return_value=httpx.Response(202, json=_batch("validating"))
    )
    done = _batch("completed", results=[_result("req-000000", '{"ok": true}')])
    poll = respx_mock.get(f"{BASE}/batches/{BATCH_ID}").mock(
        side_effect=[
            httpx.Response(200, json=_batch("in_progress")),
            httpx.Response(200, json=done),
        ]
    )
    response = _complete(_client(), response_format=SCHEMA_FORMAT)

    request = submit.calls.last.request
    assert request.headers["Authorization"] == f"Bearer {TEST_KEY}"
    sent = json.loads(request.content)
    assert list(sent) == ["endpoint", "model", "requests"]  # ``requests`` must come last
    assert (sent["endpoint"], sent["model"]) == ("/v1/chat/completions", DEFAULT_MODEL)
    [item] = sent["requests"]
    assert item["custom_id"] == "req-000000"
    assert item["body"]["messages"] == [{"role": "user", "content": "hello"}]
    assert item["body"]["response_format"] == SCHEMA_FORMAT
    assert (item["body"]["temperature"], item["body"]["seed"]) == (0.2, 7)
    assert "model" not in item["body"] and "provider" not in item["body"]
    assert poll.call_count == 2
    assert response.content == '{"ok": true}'
    assert response.model == "deepseek/deepseek-v4.1-flash-20260910"
    assert response.usage.prompt_tokens == 100


def test_concurrent_calls_share_one_batch(respx_mock: respx.MockRouter) -> None:
    submit = respx_mock.post(f"{BASE}/batches").mock(
        return_value=httpx.Response(202, json=_batch("validating"))
    )
    respx_mock.get(f"{BASE}/batches/{BATCH_ID}").mock(
        side_effect=lambda _: httpx.Response(
            200,
            json=_batch("completed", results=_echo(submit), usage={"cost": 0.24}),
        )
    )
    client = _client(batch_window_s=0.5)
    texts = [f"question {i}" for i in range(6)]
    with ThreadPoolExecutor(max_workers=6) as pool:
        responses = list(pool.map(lambda t: _complete(client, t), texts))

    assert submit.call_count == 1
    assert len(json.loads(submit.calls.last.request.content)["requests"]) == 6
    assert [r.content for r in responses] == texts  # each caller gets its own result
    # no per-request cost in the results: the batch's cost is shared by tokens
    assert [r.usage.cost for r in responses] == [pytest.approx(0.04)] * 6


def test_response_formats_go_in_separate_batches(respx_mock: respx.MockRouter) -> None:
    submit = respx_mock.post(f"{BASE}/batches").mock(
        return_value=httpx.Response(202, json=_batch("validating"))
    )
    respx_mock.get(f"{BASE}/batches/{BATCH_ID}").mock(
        return_value=httpx.Response(
            200, json=_batch("completed", results=[_result("req-000000", "{}")])
        )
    )
    client = _client(batch_window_s=0.5)
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda f: _complete(client, response_format=f), [None, SCHEMA_FORMAT]))
    assert submit.call_count == 2


def test_failed_request_raises_for_that_caller_only(respx_mock: respx.MockRouter) -> None:
    submit = respx_mock.post(f"{BASE}/batches").mock(
        return_value=httpx.Response(202, json=_batch("validating"))
    )

    def results(_: httpx.Request) -> httpx.Response:
        good, bad = _echo(submit)
        bad.update(response=None, error={"type": "invalid", "message": "bad req", "param": None})
        return httpx.Response(200, json=_batch("completed", results=[good, bad]))

    respx_mock.get(f"{BASE}/batches/{BATCH_ID}").mock(side_effect=results)
    client = _client(batch_window_s=0.5)

    def call(text: str) -> str:
        try:
            return str(_complete(client, text).content)
        except LLMError as exc:
            return f"error: {exc}"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = sorted(pool.map(call, ["a", "b"]))
    assert outcomes[0] in {"a", "b"}
    assert outcomes[1].startswith("error:") and "bad req" in outcomes[1]


def test_failed_batch_raises(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{BASE}/batches").mock(
        return_value=httpx.Response(202, json=_batch("validating"))
    )
    respx_mock.get(f"{BASE}/batches/{BATCH_ID}").mock(
        return_value=httpx.Response(
            200, json=_batch("failed", error={"message": "stream is not supported"})
        )
    )
    with pytest.raises(LLMError, match="batch-1 failed: stream is not supported"):
        _complete(_client())


def test_submit_error_is_redacted(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{BASE}/batches").mock(
        return_value=httpx.Response(402, json={"error": {"message": f"no credit {TEST_KEY}"}})
    )
    with pytest.raises(LLMError) as excinfo:
        _complete(_client())
    assert "HTTP 402" in str(excinfo.value)
    assert TEST_KEY not in str(excinfo.value) and REDACTED in str(excinfo.value)


def test_unfinished_batch_times_out(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{BASE}/batches").mock(
        return_value=httpx.Response(202, json=_batch("validating"))
    )
    respx_mock.get(f"{BASE}/batches/{BATCH_ID}").mock(
        return_value=httpx.Response(200, json=_batch("in_progress"))
    )
    with pytest.raises(LLMError, match="did not finish"):
        _complete(_client(batch_timeout_s=0.05))


def test_web_search_uses_the_synchronous_endpoint() -> None:
    retriever = OpenRouterSearchRetriever(
        OpenRouterSearchSettings(), api_key=TEST_KEY, default_model=DEFAULT_MODEL
    )
    body = retriever.build_request("serum albumin biloma", retriever.settings)
    assert body["model"] == "deepseek/deepseek-v4.1-flash"
    pinned = OpenRouterSearchSettings(model="openai/gpt-6-luna:batch")
    assert retriever.build_request("q", pinned)["model"] == "openai/gpt-6-luna"
