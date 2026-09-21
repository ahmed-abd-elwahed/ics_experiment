"""Recognise documents about animals rather than people, from each source's own metadata."""

from __future__ import annotations

import re

from medsim.models import RetrievedDocument

HUMAN_TAXON = "9606"
# NCBI taxonomy ids of animals common in biomedical studies (PubTator species annotations).
ANIMAL_TAXA = frozenset(
    {"10090", "10116", "9615", "9685", "9823", "9913", "9796", "9940", "9986", "9031", "7955",
     "9544", "9541", "9925", "10141", "10036", "10029", "8355", "9598", "9483"}
)  # fmt: skip
_ANIMAL_TITLE = re.compile(
    r"\b(?:dogs?|canine|cats?|feline|rats?|mice|mouse|murine|rabbits?|pigs?|porcine|swine|"
    r"piglets?|sheep|ovine|goats?|caprine|horses?|equine|foals?|cattle|bovine|cows?|calves|"
    r"primates?|macaques?|monkeys?|zebrafish|chickens?|avian|veterinary)\b",
    re.I,
)


def _litsense_taxa(raw: dict[str, object]) -> set[str]:
    """Species ids from LitSense annotations ("offset|length|species|9606")."""
    taxa: set[str] = set()
    for annotation in raw.get("annotations") or []:  # type: ignore[attr-defined]
        parts = str(annotation).split("|")
        if len(parts) >= 4 and parts[2] == "species":
            taxa.add(parts[3])
    return taxa


def _mesh(raw: dict[str, object]) -> set[str]:
    headings = (raw.get("meshHeadingList") or {}).get("meshHeading") or []  # type: ignore[attr-defined]
    return {str(h.get("descriptorName")) for h in headings if isinstance(h, dict)}


def non_human(doc: RetrievedDocument) -> bool:
    """True for animal studies: Europe PMC MeSH "Animals" without "Humans", LitSense passages
    tagged only with animal species, or an animal word in the title."""
    if doc.source == "europe_pmc":
        mesh = _mesh(doc.raw)
        if "Animals" in mesh and "Humans" not in mesh:
            return True
    elif doc.source == "litsense":
        taxa = _litsense_taxa(doc.raw)
        if taxa & ANIMAL_TAXA and HUMAN_TAXON not in taxa:
            return True
    return bool(doc.title and _ANIMAL_TITLE.search(doc.title))
