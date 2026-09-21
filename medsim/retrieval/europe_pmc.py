"""Europe PMC REST search retriever.

Endpoint and parameters verified by live request echo (see NOTES.md):
GET {base}/search?query=&resultType=&pageSize=&format=json&synonym=&cursorMark=*[&sort=]
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from pydantic import ValidationError

from medsim.config import EuropePMCSettings
from medsim.errors import RetrieverError
from medsim.http_utils import RateLimiter, Sleep, backoff_delay, request_with_retries
from medsim.models import RetrievedDocument
from medsim.retrieval.base import pubmed_url, strip_html
from medsim.retrieval.cache import ResponseCache

logger = logging.getLogger("medsim.retrieval")


class EuropePMCRetriever:
    name = "europe_pmc"

    def __init__(
        self,
        settings: EuropePMCSettings,
        *,
        user_agent: str,
        http_client: httpx.Client | None = None,
        cache: ResponseCache | None = None,
        sleep: Sleep = time.sleep,
    ) -> None:
        self.settings = settings
        self._user_agent = user_agent
        self._client = http_client or httpx.Client()
        self._cache = cache
        self._sleep = sleep
        self._rate = RateLimiter(settings.min_interval_s, sleep=sleep)
        self._last: dict[str, Any] | None = None

    def _effective(self, overrides: dict[str, Any]) -> EuropePMCSettings:
        try:
            return EuropePMCSettings.model_validate({**self.settings.model_dump(), **overrides})
        except ValidationError as exc:
            raise RetrieverError(self.name, f"invalid search parameters: {exc}") from None

    @staticmethod
    def build_request(query: str, cfg: EuropePMCSettings) -> tuple[str, dict[str, str]]:
        q = query
        filters = []
        if cfg.open_access_only:
            filters.append("OPEN_ACCESS:y")
        if cfg.full_text_only:
            filters.append("HAS_FT:y")
        if filters:
            q = f"({query}) AND " + " AND ".join(filters)
        params = {
            "query": q,
            "resultType": cfg.result_type,
            "pageSize": str(cfg.page_size),
            "format": "json",
            "synonym": "true" if cfg.synonym else "false",
            "cursorMark": "*",
        }
        if cfg.sort:
            params["sort"] = cfg.sort
        return f"{cfg.base_url.rstrip('/')}/search", params

    def _describe(
        self, cfg: EuropePMCSettings, url: str, params: dict[str, str] | None
    ) -> dict[str, Any]:
        return {
            "endpoint": url,
            "request_params": params,
            "page_size": cfg.page_size,
            "result_type": cfg.result_type,
            "filters": {
                "open_access_only": cfg.open_access_only,
                "full_text_only": cfg.full_text_only,
            },
            "sort": cfg.sort,
            "synonym": cfg.synonym,
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
        self._last = self._describe(cfg, url, request_params) | {"cache_hit": False}

        payload: Any = None
        if self._cache is not None:
            payload = self._cache.get(self.name, query, request_params)
            if payload is not None and not self.well_formed(payload):
                payload = None  # a malformed reply cached by an older version: fetch again
            self._last["cache_hit"] = payload is not None
        if payload is None:
            payload = self._fetch(url, request_params, cfg)
            if self._cache is not None:
                self._cache.set(self.name, query, request_params, payload)
        return self.parse(payload)

    @staticmethod
    def well_formed(payload: Any) -> bool:
        result_list = payload.get("resultList") if isinstance(payload, dict) else None
        return isinstance(result_list, dict) and isinstance(result_list.get("result"), list)

    def _fetch(self, url: str, params: dict[str, str], cfg: EuropePMCSettings) -> Any:
        """Fetch a search page, retrying HTTP 200 replies without results.

        Europe PMC intermittently answers HTTP 200 with only ``{"version": "6.9"}`` (seen on 11
        of 50 benchmark questions on 2026-09-21); such a reply is retried with backoff and never
        cached.
        """
        for attempt in range(cfg.max_retries + 1):
            payload = self._fetch_once(url, params, cfg)
            if self.well_formed(payload):
                return payload
            if attempt < cfg.max_retries:
                delay = backoff_delay(attempt, cfg.backoff_base_s)
                logger.warning("Europe PMC reply had no results list; retrying in %.1fs", delay)
                self._sleep(delay)
        raise RetrieverError(
            self.name,
            f"unexpected response shape (no resultList.result) after {cfg.max_retries + 1} "
            f"attempts: {str(payload)[:80]}",
        )

    def _fetch_once(self, url: str, params: dict[str, str], cfg: EuropePMCSettings) -> Any:
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
        if response.status_code >= 400:
            raise RetrieverError(self.name, f"HTTP {response.status_code}: {response.text[:200]}")
        try:
            return response.json()
        except ValueError:
            raise RetrieverError(self.name, "response was not JSON") from None

    @classmethod
    def parse(cls, payload: Any) -> list[RetrievedDocument]:
        try:
            results = payload["resultList"]["result"]
        except (KeyError, TypeError):
            raise RetrieverError(
                cls.name, "unexpected response shape (no resultList.result)"
            ) from None
        documents: list[RetrievedDocument] = []
        for record in results:
            if not isinstance(record, dict):
                continue
            pmid = record.get("pmid")
            pmcid = record.get("pmcid")
            doi = record.get("doi")
            if pmid:
                doc_id = f"PMID:{pmid}"
            elif pmcid:
                doc_id = f"PMCID:{pmcid}"
            elif doi:
                doc_id = f"DOI:{doi}"
            else:
                doc_id = f"EPMC:{record.get('source', '?')}:{record.get('id', '?')}"
            title = strip_html(record.get("title")) or None
            text = strip_html(record.get("abstractText")) or (title or "")
            documents.append(
                RetrievedDocument(
                    source="europe_pmc",
                    doc_id=doc_id,
                    title=title,
                    text=text,
                    url=pubmed_url(pmid, pmcid, doi),
                    score=None,
                    raw=record,
                )
            )
        return documents
