"""LitSense 2.0 retriever.

Endpoints (NAR 2025 paper and the LitSense 2.0 site's API tutorial, see NOTES.md):
GET {base}/sentences/?query=&rerank=true   GET {base}/passages/?query=&rerank=true
Returns a JSON list (top 100). A query with no matches returns HTTP 404 with {"detail": ...}.
Documented usage limit: one request per user per second.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

import httpx
from pydantic import ValidationError

from medsim.config import LitSenseSettings
from medsim.errors import RetrieverError
from medsim.http_utils import RateLimiter, Sleep, request_with_retries
from medsim.models import RetrievedDocument
from medsim.retrieval.base import pubmed_url
from medsim.retrieval.cache import ResponseCache


class LitSenseRetriever:
    name = "litsense"

    def __init__(
        self,
        settings: LitSenseSettings,
        *,
        user_agent: str,
        http_client: httpx.Client | None = None,
        cache: ResponseCache | None = None,
        sleep: Sleep = time.sleep,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self.settings = settings
        self._user_agent = user_agent
        self._client = http_client or httpx.Client()
        self._cache = cache
        self._sleep = sleep
        self._rate = rate_limiter or RateLimiter(settings.min_interval_s, sleep=sleep)
        self._last: dict[str, Any] | None = None

    def _effective(self, overrides: dict[str, Any]) -> LitSenseSettings:
        try:
            return LitSenseSettings.model_validate({**self.settings.model_dump(), **overrides})
        except ValidationError as exc:
            raise RetrieverError(self.name, f"invalid search parameters: {exc}") from None

    @staticmethod
    def build_request(query: str, cfg: LitSenseSettings) -> tuple[str, dict[str, str]]:
        url = f"{cfg.base_url.rstrip('/')}/{cfg.mode}/"
        return url, {"query": query, "rerank": "true" if cfg.rerank else "false"}

    def _describe(
        self, cfg: LitSenseSettings, url: str, params: dict[str, str] | None
    ) -> dict[str, Any]:
        return {
            "endpoint": url,
            "request_params": params,
            "result_type": cfg.mode,
            "rerank": cfg.rerank,
            "max_results": cfg.max_results,
            "filters": None,  # the LitSense API exposes no open-access/full-text filters
            "timeout_s": cfg.timeout_s,
            "max_retries": cfg.max_retries,
            "backoff_base_s": cfg.backoff_base_s,
            "min_interval_s": cfg.min_interval_s,
            "cache_enabled": self._cache is not None,
        }

    def parameters(self) -> dict[str, Any]:
        if self._last is not None:
            return dict(self._last)
        url, _ = self.build_request("", self.settings)
        return self._describe(self.settings, url, None)

    def search(self, query: str, **params: Any) -> list[RetrievedDocument]:
        cfg = self._effective(params)
        url, request_params = self.build_request(query, cfg)
        self._last = self._describe(cfg, url, request_params) | {
            "cache_hit": False,
            "no_match": False,
        }

        payload: Any = None
        if self._cache is not None:
            payload = self._cache.get(self.name, url + "|" + query, request_params)
            self._last["cache_hit"] = payload is not None
        if payload is None:
            payload = self._fetch(url, request_params, cfg)
            if self._cache is not None:
                self._cache.set(self.name, url + "|" + query, request_params, payload)
        if isinstance(payload, dict) and "no_match" in payload:
            self._last["no_match"] = True
            return []
        return self.parse(payload, cfg.mode)[: cfg.max_results]

    def _fetch(self, url: str, params: dict[str, str], cfg: LitSenseSettings) -> Any:
        try:
            response = request_with_retries(
                self._client,
                "GET",
                url,
                params=params,
                headers={"User-Agent": self._user_agent, "Accept": "application/json"},
                timeout=cfg.timeout_s,
                max_retries=cfg.max_retries,
                backoff_base_s=cfg.backoff_base_s,
                sleep=self._sleep,
                rate_limiter=self._rate,
            )
        except httpx.HTTPError as exc:
            raise RetrieverError(
                self.name, f"request failed: {type(exc).__name__}: {exc}"
            ) from None
        if response.status_code == 404:
            try:
                detail = response.json().get("detail")
            except (ValueError, AttributeError):
                detail = None
            if isinstance(detail, str):
                return {"no_match": detail}
        if response.status_code >= 400:
            raise RetrieverError(self.name, f"HTTP {response.status_code}: {response.text[:200]}")
        try:
            return response.json()
        except ValueError:
            raise RetrieverError(self.name, "response was not JSON") from None

    @classmethod
    def parse(cls, payload: Any, mode: str = "passages") -> list[RetrievedDocument]:
        if not isinstance(payload, list):
            raise RetrieverError(cls.name, "unexpected response shape (expected a JSON list)")
        documents: list[RetrievedDocument] = []
        for item in payload:
            if not isinstance(item, dict) or not isinstance(item.get("text"), str):
                continue
            text: str = item["text"].strip()
            pmid = str(item["pmid"]) if item.get("pmid") else None
            pmcid = str(item["pmcid"]) if item.get("pmcid") else None
            base = f"PMID:{pmid}" if pmid else f"PMCID:{pmcid}" if pmcid else "LITSENSE"
            fragment = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
            section = str(item.get("section") or mode).upper()
            score = item.get("score")
            documents.append(
                RetrievedDocument(
                    source="litsense",
                    doc_id=f"{base}#{section}-{fragment}",
                    title=None,
                    text=text,
                    url=pubmed_url(pmid, pmcid, None),
                    score=float(score) if isinstance(score, int | float) else None,
                    raw=item,
                )
            )
        return documents
