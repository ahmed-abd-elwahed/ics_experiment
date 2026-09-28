"""OpenRouter web search retriever (the ``openrouter:web_search`` server tool).

A small model is asked to run exactly one search with the query; OpenRouter executes it with
the configured engine and returns every result as a ``url_citation`` annotation (url, title,
excerpt). Verified by live request on 2026-09-21 (see NOTES.md). The response's
``usage.cost`` includes the search fee, and is reported as ``cost_usd`` in ``parameters()``.

The ``native`` engine (the model provider's own search, e.g. Google Search for Gemini, OpenAI's
web search for GPT models) returns citations only for sources the model cites in its reply, and
without excerpts. For it, the model is asked to list and cite the sources it found; each
document's text is the reply text its citation points to (the model's quotation or summary of the
source, not the page itself), and Google's grounding redirect links are resolved to the real
URL so the source article can be recognised. Verified by live request on 2026-09-29.
"""

from __future__ import annotations

import re
import time
from typing import Any

import httpx
from pydantic import ValidationError

from medsim.config import OpenRouterSearchSettings, Settings
from medsim.errors import RetrieverError, redact
from medsim.http_utils import Sleep, request_with_retries
from medsim.models import RetrievedDocument
from medsim.retrieval.cache import ResponseCache

SEARCH_PROMPT = (
    "You are the query step of a biomedical literature retriever. Call the web search tool "
    "exactly once, passing the user's message verbatim as the query. After the search, reply "
    "with the single word DONE. Do not answer the question yourself."
)

NATIVE_SEARCH_PROMPT = (
    "You are a literature search tool. Search the web for the user's query, restricted to "
    "biomedical literature and clinical references. Then list up to {n} relevant sources you "
    "found, one per line: the title, then a verbatim excerpt of the passage most relevant to the "
    "query (quote any numbers exactly). Cite every source with its link. Do not answer the "
    "query yourself."
)
_GOOGLE_REDIRECT = re.compile(
    r"^https://vertexaisearch\.cloud\.google\.com/grounding-api-redirect/"
)

_DOMAIN = re.compile(r"[\w-]+(\.[\w-]+)+")
_PMCID = re.compile(r"\b(PMC\d+)\b", re.I)
_PUBMED = re.compile(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", re.I)
_EUROPEPMC_MED = re.compile(r"europepmc\.org/(?:article|abstract)/MED/(\d+)", re.I)
_EXCERPT_BREAK = re.compile(r"\s*\n?\[\.\.\.\]\n?\s*")


def identifiers_from_url(url: str) -> tuple[str | None, str | None]:
    """(pmid, pmcid) recognisable from a PubMed, PMC, or Europe PMC URL."""
    pmid_match = _PUBMED.search(url) or _EUROPEPMC_MED.search(url)
    pmcid_match = _PMCID.search(url)
    return (
        pmid_match.group(1) if pmid_match else None,
        pmcid_match.group(1).upper() if pmcid_match else None,
    )


def _cited_text(reply: str, start: Any, end: Any) -> str:
    """The reply lines that contain the cited span, without the markdown link itself."""
    if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start <= end:
        return ""
    first = reply.rfind("\n", 0, start) + 1
    last = reply.find("\n", end)
    text = reply[first : last if last != -1 else len(reply)]
    text = re.sub(r"\(?\[[^\]]*\]\(https?://[^)]*\)\)?", "", text)  # ([site](url)) links
    return re.sub(r"^[\s*•-]+", "", text).replace("**", "").strip()


def doc_id_for(url: str) -> str:
    pmid, pmcid = identifiers_from_url(url)
    if pmid:
        return f"PMID:{pmid}"
    if pmcid:
        return f"PMCID:{pmcid}"
    return "URL:" + re.sub(r"^https?://(www\.)?", "", url).rstrip("/")


class OpenRouterSearchRetriever:
    name = "openrouter_search"

    def __init__(
        self,
        settings: OpenRouterSearchSettings,
        *,
        api_key: str,
        default_model: str,
        base_url: str = "https://openrouter.ai/api/v1",
        app_title: str = "medsim",
        http_referer: str | None = None,
        http_client: httpx.Client | None = None,
        cache: ResponseCache | None = None,
        sleep: Sleep = time.sleep,
    ) -> None:
        if not api_key.strip():
            raise RetrieverError(self.name, "OPENROUTER_API_KEY is empty")
        self.settings = settings
        self._key = api_key.strip()
        self._default_model = default_model
        self._base_url = base_url.rstrip("/")
        self._app_title = app_title
        self._http_referer = http_referer
        self._client = http_client or httpx.Client()
        self._cache = cache
        self._sleep = sleep
        self._last: dict[str, Any] | None = None

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        cache: ResponseCache | None = None,
        http_client: httpx.Client | None = None,
    ) -> OpenRouterSearchRetriever:
        return cls(
            settings.openrouter_search,
            api_key=settings.openrouter_api_key.get_secret_value(),
            default_model=settings.default_model,
            base_url=settings.openrouter_base_url,
            app_title=settings.openrouter_app_title,
            http_referer=settings.openrouter_http_referer,
            http_client=http_client,
            cache=cache,
        )

    def _effective(self, overrides: dict[str, Any]) -> OpenRouterSearchSettings:
        try:
            return OpenRouterSearchSettings.model_validate(
                {**self.settings.model_dump(), **overrides}
            )
        except ValidationError as exc:
            raise RetrieverError(self.name, f"invalid search parameters: {exc}") from None

    def build_request(self, query: str, cfg: OpenRouterSearchSettings) -> dict[str, Any]:
        tool: dict[str, Any] = {"engine": cfg.engine, "max_results": cfg.max_results, "max_uses": 1}
        if cfg.mode:
            tool["mode"] = cfg.mode
        if cfg.max_characters:
            tool["max_characters"] = cfg.max_characters
        if cfg.allowed_domains:
            tool["allowed_domains"] = list(cfg.allowed_domains)
        if cfg.excluded_domains:
            tool["excluded_domains"] = list(cfg.excluded_domains)
        prompt = (
            NATIVE_SEARCH_PROMPT.format(n=cfg.max_results) if cfg.engine == "native"
            else SEARCH_PROMPT
        )  # fmt: skip
        return {
            "model": cfg.model or self._default_model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": query},
            ],
            "tools": [{"type": "openrouter:web_search", "parameters": tool}],
            "temperature": 0,
            "max_tokens": cfg.max_tokens,
        }

    def _describe(
        self, cfg: OpenRouterSearchSettings, body: dict[str, Any] | None
    ) -> dict[str, Any]:
        return {
            "endpoint": f"{self._base_url}/chat/completions",
            "tool": "openrouter:web_search",
            "tool_parameters": body["tools"][0]["parameters"] if body else None,
            "model": cfg.model or self._default_model,
            "engine": cfg.engine,
            "max_results": cfg.max_results,
            "timeout_s": cfg.timeout_s,
            "max_retries": cfg.max_retries,
            "cache_enabled": self._cache is not None,
        }

    def parameters(self) -> dict[str, Any]:
        if self._last is not None:
            return dict(self._last)
        return self._describe(self.settings, None)

    def search(self, query: str, **params: Any) -> list[RetrievedDocument]:
        cfg = self._effective(params)
        body = self.build_request(query, cfg)
        self._last = self._describe(cfg, body) | {"cache_hit": False}

        payload: Any = None
        if self._cache is not None:
            payload = self._cache.get(self.name, query, body)
            self._last["cache_hit"] = payload is not None
        if payload is None:
            payload = self._fetch(body, cfg)
            if self._cache is not None:
                self._cache.set(self.name, query, body, payload)

        usage = (payload.get("usage") or {}) if isinstance(payload, dict) else {}
        cost = usage.get("cost")
        details = usage.get("server_tool_use_details") or usage.get("server_tool_use") or {}
        # cost_usd is what producing this result cost, even when it was replayed from cache.
        self._last |= {
            "cost_usd": float(cost) if isinstance(cost, int | float) else None,
            "web_search_requests": details.get("web_search_requests"),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
        }
        documents = self.parse(payload)
        return [self._resolve_redirect(doc) for doc in documents]

    def _resolve_redirect(self, doc: RetrievedDocument) -> RetrievedDocument:
        """Replace a Google grounding redirect link with the page it points to."""
        if not doc.url or not _GOOGLE_REDIRECT.match(doc.url):
            return doc
        try:
            response = self._client.head(doc.url, follow_redirects=False, timeout=20)
        except httpx.HTTPError:
            return doc
        target = response.headers.get("location")
        if not target or not target.startswith("http"):
            return doc
        pmid, pmcid = identifiers_from_url(target)
        raw = doc.raw | {"url": target, "redirect_url": doc.url, "pmid": pmid, "pmcid": pmcid}
        # Google gives the site's domain as the title ("nih.gov"); that is not a title.
        title = None if doc.title and _DOMAIN.fullmatch(doc.title) else doc.title
        return doc.model_copy(update={
            "doc_id": doc_id_for(target), "url": target, "title": title, "raw": raw,
        })  # fmt: skip

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
            "X-OpenRouter-Title": self._app_title,
            "X-Title": self._app_title,
        }
        if self._http_referer:
            headers["HTTP-Referer"] = self._http_referer
        return headers

    def _fetch(self, body: dict[str, Any], cfg: OpenRouterSearchSettings) -> Any:
        try:
            response = request_with_retries(
                self._client,
                "POST",
                f"{self._base_url}/chat/completions",
                json=body,
                headers=self._headers(),
                timeout=cfg.timeout_s,
                max_retries=cfg.max_retries,
                backoff_base_s=cfg.backoff_base_s,
                sleep=self._sleep,
            )
        except httpx.HTTPError as exc:
            raise RetrieverError(
                self.name, redact(f"request failed: {type(exc).__name__}: {exc}", [self._key])
            ) from None
        if response.status_code >= 400:
            detail = f"HTTP {response.status_code}: {response.text[:300]}"
            raise RetrieverError(self.name, redact(detail, [self._key]))
        try:
            data = response.json()
        except ValueError:
            raise RetrieverError(self.name, "response was not JSON") from None
        if not isinstance(data, dict) or data.get("error"):
            error = data.get("error") if isinstance(data, dict) else data
            raise RetrieverError(self.name, redact(f"OpenRouter error: {error}"[:300], [self._key]))
        return data

    @classmethod
    def parse(cls, payload: Any) -> list[RetrievedDocument]:
        try:
            message = payload["choices"][0]["message"]
        except (KeyError, IndexError, TypeError):
            raise RetrieverError(cls.name, "unexpected response shape (no choices)") from None
        documents: list[RetrievedDocument] = []
        seen: dict[str, int] = {}
        reply = str(message.get("content") or "")
        for annotation in message.get("annotations") or []:
            citation = annotation.get("url_citation") if isinstance(annotation, dict) else None
            if not isinstance(citation, dict) or not citation.get("url"):
                continue
            url = str(citation["url"])
            title = str(citation.get("title") or "").strip() or None
            text = _EXCERPT_BREAK.sub(" […] ", str(citation.get("content") or "")).strip()
            if not text:  # native search: the reply text the citation points to
                text = _cited_text(reply, citation.get("start_index"), citation.get("end_index"))
            if url in seen:  # native search cites a source once per supported passage
                doc = documents[seen[url]]
                if text and text not in doc.text:
                    documents[seen[url]] = doc.model_copy(update={"text": f"{doc.text} […] {text}"})
                continue
            seen[url] = len(documents)
            pmid, pmcid = identifiers_from_url(url)
            documents.append(
                RetrievedDocument(
                    source="openrouter_search",
                    doc_id=doc_id_for(url),
                    title=title,
                    text=text or title or url,
                    url=url,
                    score=None,
                    raw={"url": url, "title": title, "content": citation.get("content"),
                         "pmid": pmid, "pmcid": pmcid, "rank": len(documents) + 1},
                )
            )  # fmt: skip
        return documents
