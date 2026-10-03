"""OpenRouter Batch API: chat completions sent together, asynchronously, at batch prices.

A ``:batch`` model (e.g. ``deepseek/deepseek-v4.1-flash:batch``) is not served by
``/chat/completions``; its requests go to ``POST /batches`` and the results are polled from
``GET /batches/{id}``. :class:`BatchQueue` hides that behind a blocking call: requests made by
concurrent workers within a short window are submitted as one batch, and each caller gets its
own result back. More parallel workers therefore mean larger batches, not more requests.

Batches are asynchronous (OpenRouter's completion window is 24 hours), so a call can take
minutes or longer. OpenRouter-orchestrated web search is not available in batch; requests
that need it go to the model's synchronous endpoint (see :func:`sync_model`).
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections.abc import Callable
from typing import Any

import httpx

from medsim.config import Settings
from medsim.errors import LLMError
from medsim.http_utils import Clock, Sleep, request_with_retries

logger = logging.getLogger("medsim.llm")

BATCH_SUFFIX = ":batch"
ENDPOINT = "/v1/chat/completions"
TERMINAL_STATUSES = frozenset({"completed", "failed", "expired", "cancelled"})
# The Batch API takes one batch-level model and accepts no per-request provider preferences.
_DROPPED_KEYS = ("model", "provider")
_IDLE_EXIT_S = 5.0


def is_batch_model(model: str) -> bool:
    return model.endswith(BATCH_SUFFIX)


def sync_model(model: str) -> str:
    """The synchronous endpoint of a ``:batch`` model, for requests that cannot be batched."""
    return model.removesuffix(BATCH_SUFFIX)


class _Job:
    def __init__(self, model: str, body: dict[str, Any]) -> None:
        self.model = model
        self.body = body
        self.done = threading.Event()
        self.result: dict[str, Any] | None = None
        self.error: str | None = None

    @property
    def group(self) -> tuple[str, str]:
        # One batch per model and response format: Google's batch service derives a single
        # output schema for the whole batch.
        return self.model, json.dumps(self.body.get("response_format"), sort_keys=True)

    def finish(self, result: dict[str, Any] | None, error: str | None = None) -> None:
        self.result, self.error = result, error
        self.done.set()


class BatchQueue:
    """Collects concurrent requests into batches; ``submit`` blocks until its result is in."""

    def __init__(
        self,
        settings: Settings,
        *,
        http_client: httpx.Client,
        headers: Callable[[], dict[str, str]],
        sleep: Sleep = time.sleep,
        clock: Clock = time.monotonic,
    ) -> None:
        self._settings = settings
        self._base_url = settings.openrouter_base_url.rstrip("/")
        self._client = http_client
        self._headers = headers
        self._sleep = sleep
        self._clock = clock
        self._cond = threading.Condition()
        self._pending: list[_Job] = []
        self._dispatcher: threading.Thread | None = None

    def submit(self, model: str, body: dict[str, Any]) -> dict[str, Any]:
        """Run one chat completion in a batch and return its response body."""
        job = _Job(model, {k: v for k, v in body.items() if k not in _DROPPED_KEYS})
        with self._cond:
            self._pending.append(job)
            if self._dispatcher is None:
                self._dispatcher = threading.Thread(
                    target=self._dispatch, name="batch-dispatch", daemon=True
                )
                self._dispatcher.start()
            self._cond.notify_all()
        job.done.wait()
        if job.result is None:
            raise LLMError(job.error or "OpenRouter batch returned no result")
        return job.result

    # -- collecting -----------------------------------------------------------------------------

    def _dispatch(self) -> None:
        while True:
            with self._cond:
                idle = not self._pending and not self._cond.wait(timeout=_IDLE_EXIT_S)
                if idle and not self._pending:
                    self._dispatcher = None
                    return
                jobs = self._collect()
            groups: dict[tuple[str, str], list[_Job]] = {}
            for job in jobs:
                groups.setdefault(job.group, []).append(job)
            for (model, _), group in groups.items():
                threading.Thread(
                    target=self._run, args=(model, group), name="batch-run", daemon=True
                ).start()

    def _collect(self) -> list[_Job]:
        """Wait (lock held) until no request has arrived for ``batch_window_s``, the first one
        has waited ``batch_max_wait_s``, or ``batch_max_requests`` are queued."""
        limit = self._settings.batch_max_requests
        deadline = time.monotonic() + self._settings.batch_max_wait_s
        while len(self._pending) < limit:
            queued = len(self._pending)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            self._cond.wait(timeout=min(self._settings.batch_window_s, remaining))
            if len(self._pending) == queued:
                break
        jobs, self._pending = self._pending[:limit], self._pending[limit:]
        return jobs

    # -- running --------------------------------------------------------------------------------

    def _run(self, model: str, jobs: list[_Job]) -> None:
        try:
            results = self._execute(model, jobs)
        except Exception as exc:  # every waiting caller must be released
            if not isinstance(exc, LLMError):
                logger.exception("OpenRouter batch failed")
            message = str(exc) if isinstance(exc, LLMError) else f"{type(exc).__name__}: {exc}"
            for job in jobs:
                job.finish(None, message)
            return
        for index, job in enumerate(jobs):
            job.finish(*_outcome(results.get(_custom_id(index))))

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = request_with_retries(
                self._client,
                method,
                f"{self._base_url}{path}",
                headers=self._headers(),
                timeout=self._settings.llm_timeout_s,
                max_retries=self._settings.llm_max_retries,
                backoff_base_s=self._settings.llm_backoff_base_s,
                sleep=self._sleep,
                **kwargs,
            )
        except httpx.HTTPError as exc:
            raise LLMError(
                f"OpenRouter batch request failed: {type(exc).__name__}: {exc}"
            ) from None
        if response.status_code >= 400:
            raise LLMError(f"OpenRouter batch HTTP {response.status_code}: {response.text[:500]}")
        try:
            data = response.json()
        except ValueError:
            raise LLMError(f"OpenRouter batch returned non-JSON: {response.text[:200]}") from None
        if not isinstance(data, dict):
            raise LLMError(f"OpenRouter batch returned an unexpected body: {str(data)[:200]}")
        return data

    def _execute(self, model: str, jobs: list[_Job]) -> dict[str, dict[str, Any]]:
        """Submit one batch and poll it to the end; results by ``custom_id``."""
        # ``requests`` must be serialized last: the API stream-parses the body.
        batch = self._request(
            "POST",
            "/batches",
            json={
                "endpoint": ENDPOINT,
                "model": model,
                "requests": [
                    {"custom_id": _custom_id(i), "body": job.body} for i, job in enumerate(jobs)
                ],
            },
        )
        batch_id = batch.get("id")
        if not isinstance(batch_id, str):
            raise LLMError(f"OpenRouter batch submit returned no id: {str(batch)[:300]}")
        logger.info("submitted batch %s: %d request(s) to %s", batch_id, len(jobs), model)

        started = self._clock()
        interval = self._settings.batch_poll_interval_s
        while batch.get("status") not in TERMINAL_STATUSES:
            if self._clock() - started > self._settings.batch_timeout_s:
                raise LLMError(
                    f"OpenRouter batch {batch_id} did not finish within "
                    f"{self._settings.batch_timeout_s:g} s (status {batch.get('status')}). "
                    "Its results stay available from GET /batches/{id} for 30 days."
                )
            self._sleep(interval)
            interval = min(interval * 1.5, self._settings.batch_poll_max_interval_s)
            batch = self._request("GET", f"/batches/{batch_id}")

        if batch["status"] != "completed" or not isinstance(batch.get("results"), list):
            detail = (batch.get("error") or {}).get("message") or "no results"
            raise LLMError(f"OpenRouter batch {batch_id} {batch['status']}: {detail}")
        results = {str(r.get("custom_id")): r for r in batch["results"] if isinstance(r, dict)}
        _share_cost(batch.get("usage"), results)
        return results


def _custom_id(index: int) -> str:
    return f"req-{index:06d}"


def _outcome(result: dict[str, Any] | None) -> tuple[dict[str, Any] | None, str | None]:
    """One batch result as (chat completion body, None) or (None, error message)."""
    if result is None:
        return None, "OpenRouter batch returned no result for this request"
    response = result.get("response") or {}
    body = response.get("body")
    status = response.get("status_code", 200)
    if result.get("error") or not isinstance(body, dict) or status >= 400:
        detail = (result.get("error") or {}).get("message") or str(body)[:300]
        return None, f"OpenRouter batch request failed (HTTP {status}): {detail}"
    return body, None


def _share_cost(usage: Any, results: dict[str, dict[str, Any]]) -> None:
    """Batch results may carry token counts without a cost; the batch's total cost is then
    divided over its requests in proportion to their tokens, so that per-call costs add up."""
    total = usage.get("cost") if isinstance(usage, dict) else None
    if not isinstance(total, int | float):
        return
    usages = []
    for result in results.values():
        body = (result.get("response") or {}).get("body")
        if isinstance(body, dict) and isinstance(body.get("usage"), dict):
            if isinstance(body["usage"].get("cost"), int | float):
                return  # the provider reported per-request costs
            usages.append(body["usage"])
    tokens = sum(u.get("total_tokens") or 0 for u in usages)
    for u in usages:
        u["cost"] = total * (u.get("total_tokens") or 0) / tokens if tokens else total / len(usages)
