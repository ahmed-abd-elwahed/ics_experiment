"""Typed exception hierarchy and secret redaction."""

from __future__ import annotations

from collections.abc import Iterable

REDACTED = "***REDACTED***"


def redact(text: str, secrets: Iterable[str | None]) -> str:
    """Replace every occurrence of each non-empty secret in ``text``."""
    for secret in secrets:
        if secret:
            text = text.replace(secret, REDACTED)
    return text


class MedSimError(Exception):
    """Base class for all medsim errors."""


class ConfigError(MedSimError):
    """Invalid or missing configuration."""


class LLMError(MedSimError):
    """LLM transport or API failure."""


class LLMResponseError(LLMError):
    """The LLM returned output that could not be parsed or validated, even after repair."""


class LLMTruncatedError(LLMError):
    """The completion hit ``max_tokens`` before producing usable output (e.g. all reasoning)."""

    def __init__(
        self,
        message: str,
        *,
        max_tokens: int,
        model: str,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        latency_ms: float = 0.0,
    ) -> None:
        super().__init__(message)
        self.max_tokens = max_tokens
        self.model = model
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.latency_ms = latency_ms


class RetrieverError(MedSimError):
    """A literature source failed."""

    def __init__(self, source: str, message: str) -> None:
        super().__init__(f"{source}: {message}")
        self.source = source
