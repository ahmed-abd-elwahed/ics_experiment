"""OpenRouter chat-completions client (direct HTTP, no SDK)."""

from __future__ import annotations

import difflib
import logging
import time
from collections.abc import Iterable, Sequence
from typing import Any

import httpx

from medsim.config import Settings
from medsim.errors import ConfigError, LLMError, redact
from medsim.http_utils import Sleep, backoff_delay, request_with_retries
from medsim.llm.batch import BatchQueue, is_batch_model
from medsim.models import ChatMessage, LLMResponse, TokenUsage

logger = logging.getLogger("medsim.llm")


def _no_endpoint_for_parameters(response: httpx.Response) -> bool:
    """OpenRouter's 404 when provider routing (require_parameters) leaves no endpoint."""
    return response.status_code == 404 and "can handle the requested parameters" in response.text


class _EmptyReplyError(Exception):
    """An empty reply not caused by max_tokens; retried by ``complete``."""


class OpenRouterClient:
    """Implements :class:`medsim.llm.base.LLMClient` against ``/chat/completions``, and against
    the Batch API for ``:batch`` models (see :mod:`medsim.llm.batch`)."""

    def __init__(
        self,
        settings: Settings,
        *,
        http_client: httpx.Client | None = None,
        sleep: Sleep = time.sleep,
    ) -> None:
        self._key = settings.openrouter_api_key.get_secret_value().strip()
        if not self._key:
            raise ConfigError(
                "OPENROUTER_API_KEY is empty. Add your key to .env (see .env.example)."
            )
        self._settings = settings
        self._base_url = settings.openrouter_base_url.rstrip("/")
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(timeout=settings.llm_timeout_s)
        self._sleep = sleep
        self._capabilities: dict[str, frozenset[str]] = {}
        # Models whose reachable endpoints rejected ``temperature`` (see _complete_once).
        self._no_temperature: set[str] = set()
        self._batches = BatchQueue(
            settings, http_client=self._client, headers=self._headers, sleep=sleep
        )
        self.default_model = settings.default_model

    # -- lifecycle ------------------------------------------------------------------------------

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> OpenRouterClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # -- helpers --------------------------------------------------------------------------------

    def _redact(self, text: str) -> str:
        return redact(text, [self._key])

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
            "X-OpenRouter-Title": self._settings.openrouter_app_title,
            "X-Title": self._settings.openrouter_app_title,
        }
        if self._settings.openrouter_http_referer:
            headers["HTTP-Referer"] = self._settings.openrouter_http_referer
        return headers

    def _supports(self, model: str, parameter: str) -> bool:
        caps = self._capabilities.get(model)
        return True if caps is None else parameter in caps

    def _adapt_response_format(
        self, model: str, response_format: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        if response_format is None:
            return None
        mode = self._settings.json_mode
        if mode == "json_schema" and not self._supports(model, "structured_outputs"):
            mode = "json_object"
        if mode != "none" and not self._supports(model, "response_format"):
            mode = "none"
        if mode == "none":
            return None
        if mode == "json_object":
            return {"type": "json_object"}
        return response_format

    # -- public API -----------------------------------------------------------------------------

    def verify_models(self, models: Iterable[str] | None = None) -> None:
        """Fail fast if any model slug does not resolve on OpenRouter's models endpoint."""
        wanted = list(dict.fromkeys(models or self._settings.stage_models()))
        url = f"{self._base_url}/models"
        try:
            response = request_with_retries(
                self._client,
                "GET",
                url,
                headers=self._headers(),
                timeout=self._settings.llm_timeout_s,
                max_retries=self._settings.llm_max_retries,
                backoff_base_s=self._settings.llm_backoff_base_s,
                sleep=self._sleep,
            )
            response.raise_for_status()
            data = response.json()["data"]
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise ConfigError(
                self._redact(f"Could not list OpenRouter models from {url}: {exc}")
            ) from None

        available: dict[str, frozenset[str]] = {
            str(m["id"]): frozenset(m.get("supported_parameters") or []) for m in data
        }
        for model in wanted:
            if model not in available:
                close = difflib.get_close_matches(model, list(available), n=5, cutoff=0.6)
                vendor = model.split("/", 1)[0]
                if not close:
                    close = sorted(i for i in available if i.lstrip("~").startswith(vendor + "/"))[
                        :8
                    ]
                hint = f" Close matches: {', '.join(close)}." if close else ""
                raise ConfigError(
                    f"Model '{model}' was not found on OpenRouter ({url}).{hint} "
                    "Set MEDSIM_DEFAULT_MODEL (or a per-stage MEDSIM_*_MODEL) to a valid slug."
                )
            self._capabilities[model] = available[model]
            logger.debug("verified model %s", model)

    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        response_format: dict[str, Any] | None,
        temperature: float,
        max_tokens: int,
        model: str | None = None,
    ) -> LLMResponse:
        """One chat completion. An empty reply that was not cut off by ``max_tokens`` is a
        transient provider fault: it is retried up to ``llm_max_retries`` times with backoff."""
        retries = self._settings.llm_max_retries
        for attempt in range(retries + 1):
            try:
                return self._complete_once(
                    messages, response_format=response_format, temperature=temperature,
                    max_tokens=max_tokens, model=model,
                )  # fmt: skip
            except _EmptyReplyError:
                if attempt >= retries:
                    raise LLMError(
                        f"OpenRouter returned empty message content ({retries + 1} attempts)."
                    ) from None
                delay = backoff_delay(attempt, self._settings.llm_backoff_base_s)
                logger.warning("OpenRouter returned an empty reply; retrying in %.1fs", delay)
                self._sleep(delay)
        raise AssertionError("unreachable")

    def _post(self, body: dict[str, Any]) -> httpx.Response:
        try:
            return request_with_retries(
                self._client,
                "POST",
                f"{self._base_url}/chat/completions",
                json=body,
                headers=self._headers(),
                timeout=self._settings.llm_timeout_s,
                max_retries=self._settings.llm_max_retries,
                backoff_base_s=self._settings.llm_backoff_base_s,
                sleep=self._sleep,
            )
        except httpx.HTTPError as exc:
            raise LLMError(
                self._redact(f"OpenRouter request failed: {type(exc).__name__}: {exc}")
            ) from None

    def _post_sync(self, model: str, body: dict[str, Any]) -> dict[str, Any]:
        response = self._post(body)
        if "temperature" in body and _no_endpoint_for_parameters(response):
            # The model lists temperature, but no endpoint this account can reach accepts it
            # (e.g. after tier or data-retention filtering): retry once without it, and skip it
            # for this model from now on.
            logger.warning(
                "OpenRouter has no endpoint for %s that accepts temperature; retrying without it",
                model,
            )
            self._no_temperature.add(model)
            body.pop("temperature")
            response = self._post(body)
        if response.status_code >= 400:
            raise LLMError(f"OpenRouter HTTP {response.status_code}: {response.text[:500]}")
        try:
            data: dict[str, Any] = response.json()
        except ValueError:
            raise LLMError(f"OpenRouter returned non-JSON body: {response.text[:200]}") from None
        return data

    def _complete_once(
        self,
        messages: Sequence[ChatMessage],
        *,
        response_format: dict[str, Any] | None,
        temperature: float,
        max_tokens: int,
        model: str | None = None,
    ) -> LLMResponse:
        model = model or self.default_model
        body: dict[str, Any] = {
            "model": model,
            "messages": [m.model_dump() for m in messages],
            "max_tokens": max_tokens,
        }
        # Reasoning models often do not accept ``temperature``; with require_parameters set,
        # sending it anyway leaves OpenRouter no endpoint, so it is sent only where supported.
        if self._supports(model, "temperature") and model not in self._no_temperature:
            body["temperature"] = temperature
        if self._settings.seed is not None and self._supports(model, "seed"):
            body["seed"] = self._settings.seed
        adapted = self._adapt_response_format(model, response_format)
        if adapted is not None:
            body["response_format"] = adapted
            body["provider"] = {"require_parameters": True}
        body.update(self._settings.llm_extra_body)

        started = time.perf_counter()
        try:
            data = (
                self._batches.submit(model, body) if is_batch_model(model)
                else self._post_sync(model, body)
            )  # fmt: skip
        except LLMError as exc:
            raise LLMError(self._redact(str(exc))) from None
        latency_ms = (time.perf_counter() - started) * 1000
        if data.get("error"):
            raise LLMError(self._redact(f"OpenRouter error: {data['error']}"))
        try:
            choice = data["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise LLMError(
                self._redact(f"OpenRouter response missing choices: {data}"[:500])
            ) from None
        finish_reason = choice.get("finish_reason")
        if not isinstance(content, str):
            content = ""
        # A reply cut off by max_tokens (e.g. a reasoning model that used the whole budget) is
        # returned so the caller can retry with a larger budget; other empty replies are errors.
        if not content.strip() and finish_reason != "length":
            raise _EmptyReplyError

        usage = data.get("usage") or {}
        return LLMResponse(
            content=content,
            model=str(data.get("model") or model),
            usage=TokenUsage(
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
                total_tokens=usage.get("total_tokens"),
                cost=float(cost) if isinstance(cost := usage.get("cost"), int | float) else None,
            ),
            latency_ms=latency_ms,
            finish_reason=str(finish_reason) if finish_reason is not None else None,
            raw=data,
        )
