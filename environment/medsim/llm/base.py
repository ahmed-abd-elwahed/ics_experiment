"""LLM client protocol."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable

from medsim.models import ChatMessage, LLMResponse


@runtime_checkable
class LLMClient(Protocol):
    default_model: str

    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        response_format: dict[str, Any] | None,
        temperature: float,
        max_tokens: int,
        model: str | None = None,
    ) -> LLMResponse: ...
