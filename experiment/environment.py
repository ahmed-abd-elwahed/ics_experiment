"""The simulated environment, built afresh for each case run."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Protocol

import httpx

from medsim.config import Settings
from medsim.environment import MedicalEnvironment, build_aggregator
from medsim.errors import ConfigError
from medsim.http_utils import RateLimiter
from medsim.llm.base import LLMClient
from medsim.models import CaseStudy, EnvironmentResponse
from medsim.retrieval.base import Retriever
from medsim.retrieval.cache import ResponseCache
from medsim.retrieval.europe_pmc import EuropePMCRetriever
from medsim.retrieval.fulltext import FullTextFetcher
from medsim.retrieval.litsense import LitSenseRetriever
from medsim.retrieval.openrouter_search import OpenRouterSearchRetriever

logger = logging.getLogger("experiment.environment")


class Environment(Protocol):
    def query(self, query: str) -> EnvironmentResponse: ...


EnvironmentFactory = Callable[[CaseStudy], Environment]


class MedsimEnvironmentFactory:
    """A new ``MedicalEnvironment`` per case run, with its own fact ledger and retrievers (they
    keep per-search state).

    Case runs in parallel threads share one LLM client, one HTTP client, the retrieval cache,
    and one LitSense rate limiter, so its documented limit of one request per second holds
    across all workers.
    """

    def __init__(self, settings: Settings, llm: LLMClient) -> None:
        self.settings = settings
        self.llm = llm
        self._http = httpx.Client()
        self._cache = ResponseCache(settings.cache_dir) if settings.cache_enabled else None
        self._litsense_rate = RateLimiter(settings.litsense.min_interval_s)
        self._user_agent = settings.user_agent()
        if not self.retrievers():
            raise ConfigError("No literature sources enabled; set enabled_sources.")
        if not settings.contact_email:
            logger.warning("MEDSIM_CONTACT_EMAIL is unset; User-Agent will carry no contact.")

    def retrievers(self) -> list[Retriever]:
        settings = self.settings
        retrievers: list[Retriever] = []
        for name in dict.fromkeys(settings.enabled_sources):
            if name == "europe_pmc" and settings.europe_pmc.enabled:
                retrievers.append(EuropePMCRetriever(
                    settings.europe_pmc, user_agent=self._user_agent, http_client=self._http,
                    cache=self._cache,
                ))  # fmt: skip
            elif name == "litsense" and settings.litsense.enabled:
                retrievers.append(LitSenseRetriever(
                    settings.litsense, user_agent=self._user_agent, http_client=self._http,
                    cache=self._cache, rate_limiter=self._litsense_rate,
                ))  # fmt: skip
            elif name == "openrouter_search" and settings.openrouter_search.enabled:
                retrievers.append(OpenRouterSearchRetriever.from_settings(
                    settings, cache=self._cache, http_client=self._http
                ))  # fmt: skip
        return retrievers

    def __call__(self, case: CaseStudy) -> MedicalEnvironment:
        settings = self.settings
        retrievers = self.retrievers()
        fulltext = None
        if settings.fulltext_excerpts and settings.fulltext_max_docs > 0:
            fulltext = FullTextFetcher.from_settings(
                settings, http_client=self._http, cache=self._cache
            )
        aggregator = build_aggregator(settings, retrievers, self.llm, fulltext=fulltext)
        return MedicalEnvironment(
            case_study=case,
            llm=self.llm,
            retrievers=retrievers,
            settings=settings,
            aggregator=aggregator,
        )

    def close(self) -> None:
        self._http.close()
