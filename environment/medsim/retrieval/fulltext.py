"""Open-access full text from Europe PMC, as plain-text blocks for excerpting.

GET {base}/{PMCID}/fullTextXML returns JATS XML for articles in the open-access subset and an
error status otherwise (verified by live request on 2026-09-22, see NOTES.md).
"""

from __future__ import annotations

import logging
import time
import xml.etree.ElementTree as ET
from typing import Any

import httpx

from medsim.config import Settings
from medsim.http_utils import Sleep, request_with_retries
from medsim.retrieval.cache import ResponseCache

logger = logging.getLogger("medsim.retrieval")

_SKIP = frozenset({"fig", "ref-list", "fn-group", "ack", "app-group", "supplementary-material"})


def _local(tag: object) -> str:
    return str(tag).rsplit("}", 1)[-1]


def _text(elem: ET.Element) -> str:
    return " ".join("".join(elem.itertext()).split())


def _table_blocks(table: ET.Element) -> list[str]:
    """One block per data row, prefixed with the caption and header so the row reads alone."""
    caption = " ".join(_text(e) for e in table if _local(e.tag) in ("label", "caption"))[:160]
    rows = [
        " | ".join(_text(cell) for cell in tr if _local(cell.tag) in ("td", "th"))
        for tr in table.iter()
        if _local(tr.tag) == "tr"
    ]
    rows = [r for r in rows if r.strip(" |")]
    if not rows:
        return []
    header, body = rows[0], rows[1:] or rows[:1]
    prefix = f"{caption} [{header}]" if caption else f"[{header}]"
    return [f"{prefix}: {row}." for row in body]


def parse_blocks(xml: bytes | str) -> list[str]:
    """Paragraphs, section titles, and table rows of the article body, in order."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []
    body = next((e for e in root.iter() if _local(e.tag) == "body"), None)
    if body is None:
        return []
    blocks: list[str] = []

    def walk(elem: ET.Element) -> None:
        tag = _local(elem.tag)
        if tag in _SKIP:
            return
        if tag == "table-wrap":
            blocks.extend(_table_blocks(elem))
            return
        if tag in ("p", "title"):
            text = _text(elem)
            if text:
                blocks.append(text if tag == "p" else f"{text}.")
            return
        for child in elem:
            walk(child)

    walk(body)
    return blocks


class FullTextFetcher:
    name = "europe_pmc_fulltext"

    def __init__(
        self,
        *,
        base_url: str,
        user_agent: str,
        http_client: httpx.Client | None = None,
        cache: ResponseCache | None = None,
        timeout_s: float = 20.0,
        max_retries: int = 1,
        sleep: Sleep = time.sleep,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._user_agent = user_agent
        self._client = http_client or httpx.Client()
        self._cache = cache
        self._timeout_s = timeout_s
        self._max_retries = max_retries
        self._sleep = sleep

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        http_client: httpx.Client | None = None,
        cache: ResponseCache | None = None,
    ) -> FullTextFetcher:
        if cache is None and settings.cache_enabled:
            cache = ResponseCache(settings.cache_dir)
        return cls(
            base_url=settings.europe_pmc.base_url,
            user_agent=settings.user_agent(),
            http_client=http_client,
            cache=cache,
            timeout_s=settings.europe_pmc.timeout_s,
        )

    def blocks(self, pmcid: str) -> list[str] | None:
        """Body text blocks, or None if the article has no open-access full text."""
        if self._cache is not None:
            cached: Any = self._cache.get(self.name, pmcid, {})
            if isinstance(cached, dict):
                blocks: list[str] | None = cached.get("blocks")
                return blocks
        blocks = self._fetch(pmcid)
        if self._cache is not None:
            self._cache.set(self.name, pmcid, {}, {"blocks": blocks})
        return blocks

    def _fetch(self, pmcid: str) -> list[str] | None:
        url = f"{self._base_url}/{pmcid}/fullTextXML"
        try:
            response = request_with_retries(
                self._client, "GET", url,
                headers={"User-Agent": self._user_agent, "Accept": "application/xml"},
                timeout=self._timeout_s, max_retries=self._max_retries, backoff_base_s=1.0,
                sleep=self._sleep,
            )  # fmt: skip
        except httpx.HTTPError as exc:
            logger.info("full text for %s unavailable: %s", pmcid, type(exc).__name__)
            return None
        if response.status_code != 200:
            return None
        return parse_blocks(response.content) or None
