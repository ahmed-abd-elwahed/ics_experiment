from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

import pytest

from medsim.errors import LLMError, LLMResponseError, LLMTruncatedError
from medsim.llm.structured import call_structured, strict_json_schema
from medsim.models import (
    ChatMessage,
    LLMCallRecord,
    LLMResponse,
    QueryBuilderOutput,
    SynthesizerOutput,
    TokenUsage,
)
from tests.conftest import ScriptedLLM

VALID = {
    "literature_query": "body temperature common cold adults",
    "clinical_variable": "body temperature",
    "expected_answer_type": "numeric",
    "decline_reason": None,
}
MESSAGES = [ChatMessage(role="user", content="q")]


def _call(llm: ScriptedLLM, records: list[LLMCallRecord]) -> QueryBuilderOutput:
    return call_structured(
        llm,
        stage="query_builder",
        messages=MESSAGES,
        output_model=QueryBuilderOutput,
        temperature=0.0,
        max_tokens=100,
        model=None,
        records=records,
    )


def test_valid_json_first_try(llm: ScriptedLLM) -> None:
    llm.push(VALID)
    records: list[LLMCallRecord] = []
    output = _call(llm, records)
    assert output.literature_query == VALID["literature_query"]
    assert [(r.attempt, r.purpose, r.success) for r in records] == [(1, "initial", True)]
    assert llm.calls[0]["response_format"]["type"] == "json_schema"


def test_fenced_json_is_accepted(llm: ScriptedLLM) -> None:
    llm.push('```json\n{"literature_query": null, "clinical_variable": null, '
             '"expected_answer_type": "descriptive", "decline_reason": "name"}\n```')  # fmt: skip
    output = _call(llm, [])
    assert output.literature_query is None


def test_malformed_json_is_repaired_once(llm: ScriptedLLM) -> None:
    llm.push('{"literature_query": "fever", oops', VALID)
    records: list[LLMCallRecord] = []
    output = _call(llm, records)
    assert output.clinical_variable == "body temperature"
    assert [(r.purpose, r.success) for r in records] == [
        ("initial", False),
        ("json_repair", True),
    ]
    repair_messages: list[ChatMessage] = llm.calls[1]["messages"]
    assert repair_messages[-2].role == "assistant"
    assert repair_messages[-2].content.startswith('{"literature_query": "fever", oops')
    assert "could not be used" in repair_messages[-1].content


def test_invalid_twice_raises_typed_error(llm: ScriptedLLM) -> None:
    llm.push({"unexpected": 1}, "still not json")
    records: list[LLMCallRecord] = []
    with pytest.raises(LLMResponseError, match="after one repair attempt"):
        _call(llm, records)
    assert [r.success for r in records] == [False, False]
    assert len(llm.calls) == 2


def test_transport_error_is_recorded_then_raised(llm: ScriptedLLM) -> None:
    llm.push(LLMError("boom"))
    records: list[LLMCallRecord] = []
    with pytest.raises(LLMError, match="boom"):
        _call(llm, records)
    assert records[0].success is False and records[0].error == "boom"


def test_strict_schema_requires_every_key() -> None:
    schema = strict_json_schema(SynthesizerOutput)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            assert "default" not in node
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(schema)


class BudgetLLM:
    """Replies are cut off (finish_reason="length") until max_tokens reaches ``needed``."""

    def __init__(self, needed: int, content: str, truncated_content: str = " ") -> None:
        self.default_model = "test/model"
        self.needed = needed
        self.content = content
        self.truncated_content = truncated_content
        self.budgets: list[int] = []

    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        response_format: dict[str, Any] | None,
        temperature: float,
        max_tokens: int,
        model: str | None = None,
    ) -> LLMResponse:
        self.budgets.append(max_tokens)
        cut_off = max_tokens < self.needed
        return LLMResponse(
            content=self.truncated_content if cut_off else self.content,
            model=self.default_model,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=min(max_tokens, self.needed)),
            latency_ms=1.0,
            finish_reason="length" if cut_off else "stop",
        )


def _budget_call(llm: BudgetLLM, records: list[LLMCallRecord], max_tokens: int = 100) -> Any:
    return call_structured(
        llm, stage="query_builder", messages=MESSAGES, output_model=QueryBuilderOutput,
        temperature=0.0, max_tokens=max_tokens, model=None, records=records,
    )  # fmt: skip


def test_cut_off_reply_is_retried_with_double_budget() -> None:
    llm = BudgetLLM(needed=200, content=json.dumps(VALID))
    records: list[LLMCallRecord] = []
    output = _budget_call(llm, records)
    assert output.literature_query == VALID["literature_query"]
    assert llm.budgets == [100, 200]
    assert [(r.purpose, r.success, r.finish_reason, r.max_tokens) for r in records] == [
        ("initial", False, "length", 100),
        ("length_retry", True, "stop", 200),
    ]
    assert "cut off at max_tokens=100" in (records[0].error or "")


def test_cut_off_twice_raises_truncated_error() -> None:
    llm = BudgetLLM(needed=10_000, content=json.dumps(VALID))
    records: list[LLMCallRecord] = []
    with pytest.raises(LLMTruncatedError, match="MEDSIM_QUERY_BUILDER_MAX_TOKENS") as excinfo:
        _budget_call(llm, records)
    assert llm.budgets == [100, 200]
    assert excinfo.value.max_tokens == 200
    assert [r.purpose for r in records] == ["initial", "length_retry"]


def test_cut_off_partial_json_retries_budget_not_repair() -> None:
    llm = BudgetLLM(
        needed=200, content=json.dumps(VALID), truncated_content='{"literature_query": "bo'
    )
    records: list[LLMCallRecord] = []
    _budget_call(llm, records)
    assert [r.purpose for r in records] == ["initial", "length_retry"]


def test_complete_json_is_accepted_even_at_the_limit() -> None:
    llm = BudgetLLM(needed=500, content="", truncated_content=json.dumps(VALID))
    records: list[LLMCallRecord] = []
    output = _budget_call(llm, records)
    assert output.clinical_variable == "body temperature"
    assert llm.budgets == [100]
    assert records[0].success and records[0].finish_reason == "length"
