"""Strict-JSON LLM calls: schema enforcement, Pydantic validation, bounded recovery retries."""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Sequence
from typing import Any, Literal, TypeVar

from pydantic import BaseModel

from medsim.errors import LLMError, LLMResponseError, LLMTruncatedError
from medsim.llm.base import LLMClient
from medsim.models import CallPurpose, ChatMessage, LLMCallRecord, StageName

T = TypeVar("T", bound=BaseModel)

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.I)

REPAIR_PROMPT = (
    "Your previous reply could not be used: {error}\n"
    "Reply again with ONLY a single JSON object that matches the required schema. "
    "No prose, no markdown fences."
)


def strict_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Pydantic schema adapted for strict structured outputs (all keys required, no extras)."""
    schema = copy.deepcopy(model.model_json_schema())

    def fix(node: Any) -> None:
        if isinstance(node, dict):
            node.pop("title", None)
            node.pop("default", None)
            props = node.get("properties")
            if isinstance(props, dict):
                node["required"] = list(props)
                node["additionalProperties"] = False
            for value in node.values():
                fix(value)
        elif isinstance(node, list):
            for item in node:
                fix(item)

    fix(schema)
    return schema


def response_format_for(model: type[BaseModel], name: str) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {"name": name, "strict": True, "schema": strict_json_schema(model)},
    }


def extract_json(text: str) -> Any:
    """Parse a JSON object, tolerating markdown fences or leading/trailing prose."""
    cleaned = _FENCE.sub("", text.strip())
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise
        return json.loads(cleaned[start : end + 1])


def _validate(output_model: type[T], content: str) -> T:
    return output_model.model_validate(extract_json(content))


def call_structured(
    llm: LLMClient,
    *,
    stage: StageName,
    messages: Sequence[ChatMessage],
    output_model: type[T],
    temperature: float,
    max_tokens: int,
    model: str | None,
    records: list[LLMCallRecord],
    purpose: Literal["initial", "consistency_retry"] = "initial",
) -> T:
    """Call the LLM and validate its JSON, with bounded recovery.

    - If the reply was cut off by ``max_tokens`` (reasoning models can spend the whole budget
      before answering), retry once with double the budget; raise ``LLMTruncatedError`` if that
      is cut off too.
    - If the JSON is invalid, send one repair request; raise ``LLMResponseError`` if it fails.

    At most three calls are made. Every call, successful or not, is appended to ``records``.
    """
    response_format = response_format_for(output_model, f"{stage}_output")
    requested_model = model or llm.default_model
    conversation = list(messages)
    budget = max_tokens
    next_purpose: CallPurpose = purpose
    length_retried = False
    repaired = False
    attempt = 0

    while True:
        attempt += 1
        this_purpose = next_purpose
        try:
            response = llm.complete(
                conversation,
                response_format=response_format,
                temperature=temperature,
                max_tokens=budget,
                model=model,
            )
        except LLMError as exc:
            records.append(
                LLMCallRecord(
                    stage=stage, model=requested_model, prompt_tokens=None, completion_tokens=None,
                    latency_ms=0.0, attempt=attempt, purpose=this_purpose, success=False,
                    error=str(exc)[:500], max_tokens=budget,
                )
            )  # fmt: skip
            raise

        record = LLMCallRecord(
            stage=stage,
            model=response.model,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            latency_ms=response.latency_ms,
            attempt=attempt,
            purpose=this_purpose,
            finish_reason=response.finish_reason,
            max_tokens=budget,
            cost_usd=response.usage.cost,
        )

        if response.finish_reason == "length":
            try:
                parsed = _validate(output_model, response.content)
            except ValueError:
                error = f"reply cut off at max_tokens={budget} before a complete answer"
                records.append(record.model_copy(update={"success": False, "error": error}))
                if length_retried:
                    raise LLMTruncatedError(
                        f"{stage}: {error}, even after retrying with a doubled budget. "
                        f"Raise MEDSIM_{stage.upper()}_MAX_TOKENS.",
                        max_tokens=budget,
                        model=response.model,
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        latency_ms=response.latency_ms,
                    ) from None
                length_retried = True
                budget *= 2
                next_purpose = "length_retry"
                continue
            records.append(record)
            return parsed

        try:
            parsed = _validate(output_model, response.content)
        except ValueError as exc:  # JSONDecodeError and ValidationError are ValueErrors
            error = f"{type(exc).__name__}: {exc}"[:600]
            records.append(record.model_copy(update={"success": False, "error": error}))
            if repaired:
                raise LLMResponseError(
                    f"{stage}: model output was not valid JSON for {output_model.__name__} "
                    f"after one repair attempt: {error}"
                ) from None
            repaired = True
            conversation = [
                *messages,
                ChatMessage(role="assistant", content=response.content[:4000]),
                ChatMessage(role="user", content=REPAIR_PROMPT.format(error=error)),
            ]
            next_purpose = "json_repair"
            continue
        records.append(record)
        return parsed
