"""Retriever protocol and shared helpers."""

from __future__ import annotations

import html
import re
from typing import Any, Protocol, runtime_checkable

from medsim.models import RetrievedDocument

__all__ = ["RetrievedDocument", "Retriever", "strip_html"]

_TAG = re.compile(r"</?[A-Za-z][^<>]*>")  # real tags only; keeps "(< 35 °C)" intact


@runtime_checkable
class Retriever(Protocol):
    name: str

    def search(self, query: str, **params: Any) -> list[RetrievedDocument]: ...

    def parameters(self) -> dict[str, Any]:
        """Parameters actually used by the most recent ``search`` (or configured defaults)."""
        ...


def strip_html(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", html.unescape(_TAG.sub(" ", text))).strip()


def pubmed_url(pmid: str | None, pmcid: str | None, doi: str | None) -> str | None:
    if pmid:
        return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    if pmcid:
        return f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"
    if doi:
        return f"https://doi.org/{doi}"
    return None
