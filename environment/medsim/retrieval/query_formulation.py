"""Source-specific query formulation, relaxation ladders, and lexical relevance ranking.

Stage B describes *what* to look for as term lists; this module decides *how* each source is
queried:

- Europe PMC gets boolean synonym groups restricted to title/abstract (``TITLE_ABS``), so every
  hit mentions both the variable and the condition. Unrestricted keyword strings mostly return
  conference programmes and records without abstracts.
- LitSense gets short focused phrases: its lexical prefilter needs word overlap with the query,
  and its reranker favours focused queries over long keyword lists or questions.

Each source has a ladder of progressively broader queries that the aggregator walks until
enough documents mention the variable.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

from medsim.models import LiteratureQuery, QueryBuilderOutput, RetrievedDocument

MAX_TERMS = 5
MAX_RELATED_TERMS = 4
MAX_CONTEXT_TERMS = 3
MAX_TERM_WORDS = 6
REFERENCE_TERMS = ("reference range", "reference interval", "normal values", "healthy adults")

_UNSAFE = re.compile(r"[\"'():\[\]{}^~*?\\/!+&|<>=]+")
_BOOLEAN = re.compile(r"\b(?:AND|OR|NOT)\b")
_QUALIFIERS = frozenset(
    {"serum", "plasma", "blood", "total", "body", "arterial", "venous", "peripheral", "mean",
     "resting", "whole"}
)  # fmt: skip


@dataclass(frozen=True)
class QueryAttempt:
    level: str
    query: str


# --- term handling ------------------------------------------------------------------------------


def clean_term(term: str) -> str:
    """Strip query-syntax characters and boolean operators so terms can't break a query."""
    text = _BOOLEAN.sub(" ", _UNSAFE.sub(" ", term))
    return " ".join(text.split()[:MAX_TERM_WORDS])


def clean_terms(terms: Iterable[str], limit: int = MAX_TERMS) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for term in terms:
        value = clean_term(term)
        key = value.casefold()
        if len(value) < 2 or key in seen:
            continue
        seen.add(key)
        cleaned.append(value)
        if len(cleaned) == limit:
            break
    return cleaned


def to_literature_query(output: QueryBuilderOutput) -> LiteratureQuery:
    return LiteratureQuery(
        keywords=output.literature_query or "",
        variable_terms=output.variable_terms,
        condition_terms=output.condition_terms,
        related_condition_terms=output.related_condition_terms,
        context_terms=output.context_terms,
        expected_answer_type=output.expected_answer_type,
    )


# --- ladders ------------------------------------------------------------------------------------


def _phrase(term: str) -> str:
    return f'"{term}"' if (" " in term or "-" in term) else term


def _group(terms: Sequence[str], field: str | None = None) -> str:
    body = "(" + " OR ".join(_phrase(t) for t in terms) + ")"
    return f"{field}:{body}" if field else body


def _core_terms(lq: LiteratureQuery) -> tuple[list[str], list[str], list[str]]:
    return (
        clean_terms(lq.variable_terms),
        clean_terms(lq.condition_terms),
        clean_terms(lq.related_condition_terms, limit=MAX_RELATED_TERMS),
    )


@dataclass(frozen=True)
class LadderOptions:
    """Which ladders to build. v1 is the original method; v2 adds an article-body rung for
    Europe PMC and drops the rungs that never yielded a useful document in the benchmark
    (LitSense synonym and reference-range rungs, Europe PMC any-field and reference rungs)."""

    version: Literal["v1", "v2"] = "v1"
    litsense_query: Literal["keywords", "natural"] = "keywords"


V1 = LadderOptions()
BODY_SECTIONS = ("CASE", "RESULTS", "TABLE")  # Europe PMC full-text section fields


def natural_phrase(variable: str, condition: str, context: Sequence[str] = ()) -> str:
    who = f"{context[0]} patients" if context else "patients"
    return f"{variable} in {who} with {condition}"


def europe_pmc_ladder(lq: LiteratureQuery, options: LadderOptions = V1) -> list[QueryAttempt]:
    variable, condition, related = _core_terms(lq)
    if not variable or not condition:
        return [QueryAttempt("keywords", lq.keywords)]
    variable_ta = _group(variable, "TITLE_ABS")
    condition_ta = _group(condition, "TITLE_ABS")
    ladder = [QueryAttempt("variable_and_condition", f"{variable_ta} AND {condition_ta}")]
    if options.version == "v2":
        # The variable anywhere in a case description, results section, or table of an
        # open-access article about the condition: where case reports state patient values.
        body = "(" + " OR ".join(_group(variable, section) for section in BODY_SECTIONS) + ")"
        ladder.append(QueryAttempt("body_variable_and_condition", f"{body} AND {condition_ta}"))
        if related:
            ladder.append(
                QueryAttempt(
                    "variable_and_related_condition",
                    f"{variable_ta} AND {_group(related, 'TITLE_ABS')}",
                )
            )
        return ladder
    if related:
        ladder.append(
            QueryAttempt(
                "variable_and_related_condition",
                f"{variable_ta} AND {_group(related, 'TITLE_ABS')}",
            )
        )
    ladder.append(
        QueryAttempt(
            "variable_and_condition_any_field",
            f"{_group(variable)} AND {_group(condition + related)} AND HAS_ABSTRACT:y",
        )
    )
    ladder.append(
        QueryAttempt(
            "variable_reference_values",
            f"{variable_ta} AND {_group(REFERENCE_TERMS, 'TITLE_ABS')}",
        )
    )
    return ladder


def litsense_ladder(lq: LiteratureQuery, options: LadderOptions = V1) -> list[QueryAttempt]:
    variable, condition, related = _core_terms(lq)
    if not variable or not condition:
        return [QueryAttempt("keywords", lq.keywords)]
    context = clean_terms(lq.context_terms, limit=1)

    def phrase(var: str, cond: str) -> str:
        if options.litsense_query == "natural":
            return natural_phrase(var, cond, context)
        return f"{var} {cond}"

    ladder = [QueryAttempt("variable_and_condition", phrase(variable[0], condition[0]))]
    if options.version == "v1" and len(variable) > 1:
        ladder.append(
            QueryAttempt("variable_synonym_and_condition", phrase(variable[1], condition[0]))
        )
    if related:
        ladder.append(
            QueryAttempt("variable_and_related_condition", phrase(variable[0], related[0]))
        )
    if options.version == "v1":
        ladder.append(
            QueryAttempt(
                "variable_reference_values", f"{variable[0]} reference range healthy adults"
            )
        )
    return ladder


def web_search_ladder(lq: LiteratureQuery, options: LadderOptions = V1) -> list[QueryAttempt]:
    """One natural-language query for a neural web search engine.

    A single rung: every web search is billed, so there is no relaxation ladder.
    """
    variable, condition, _ = _core_terms(lq)
    if not variable or not condition:
        return [QueryAttempt("keywords", lq.keywords)]
    context = clean_terms(lq.context_terms, limit=1)
    return [
        QueryAttempt("variable_and_condition", natural_phrase(variable[0], condition[0], context))
    ]


LadderBuilder = Callable[[LiteratureQuery, LadderOptions], list[QueryAttempt]]

LADDERS: dict[str, LadderBuilder] = {
    "europe_pmc": europe_pmc_ladder,
    "litsense": litsense_ladder,
    "openrouter_search": web_search_ladder,
}


def query_ladder(
    source: str, lq: LiteratureQuery, options: LadderOptions = V1
) -> list[QueryAttempt]:
    """Queries to try for ``source``, strictest first. Unknown sources get the keywords."""
    builder = LADDERS.get(source)
    return builder(lq, options) if builder else [QueryAttempt("keywords", lq.keywords)]


# --- relevance scoring --------------------------------------------------------------------------


def _term_pattern(terms: Sequence[str]) -> re.Pattern[str] | None:
    variants: set[str] = set()
    for term in terms:
        variants.add(term)
        words = term.split()
        while len(words) > 1 and words[0].casefold() in _QUALIFIERS:
            words = words[1:]
        variants.add(" ".join(words))
    if not variants:
        return None
    alternation = "|".join(re.escape(v) for v in sorted(variants, key=len, reverse=True))
    return re.compile(rf"(?<![\w-])(?:{alternation})s?(?![\w-])", re.I)


def _document_text(doc: RetrievedDocument) -> str:
    return f"{doc.title or ''} {doc.text}"


def doc_key(doc: RetrievedDocument) -> str:
    return doc.doc_id.strip().lower()


class RelevanceScorer:
    """Lexical score: mentions the variable, the condition, and (for numbers) a nearby value.

    Original weights: variable +3, condition +2 (related condition +1), a number near the
    variable +2 (numeric questions), a context term +0.5. Options for the retrieval changes:

    - ``value_first``: a number near the variable +6 and the exact condition +3, so documents
      that state a value outrank any that do not.
    - ``age_penalty``: -4 when the document is about another age group than the patient's.
    - ``related_penalty``: -2 for documents found only by the related-condition query, so they
      fill empty slots instead of displacing documents about the patient's own condition.
    """

    def __init__(
        self,
        lq: LiteratureQuery,
        *,
        value_first: bool = False,
        age_penalty: bool = False,
        related_penalty: bool = False,
    ) -> None:
        variable, condition, related = _core_terms(lq)
        self._variable = _term_pattern(variable)
        self._condition = _term_pattern(condition)
        self._related = _term_pattern(related)
        self._context = _term_pattern(clean_terms(lq.context_terms, limit=MAX_CONTEXT_TERMS))
        self._value_near_variable: re.Pattern[str] | None = None
        if self._variable is not None and lq.expected_answer_type == "numeric":
            v = self._variable.pattern
            self._value_near_variable = re.compile(
                rf"(?:{v})[^.;]{{0,60}}\d|\d[^.;]{{0,40}}(?:{v})", re.I
            )
        self.value_first = value_first
        self.age_penalty = age_penalty
        self.related_penalty = related_penalty
        self._age_group = lq.patient_age_group

    @property
    def active(self) -> bool:
        return self._variable is not None

    @property
    def numeric(self) -> bool:
        return self._value_near_variable is not None

    def mentions_variable(self, doc: RetrievedDocument) -> bool:
        return self._variable is None or bool(self._variable.search(_document_text(doc)))

    def has_value(self, doc: RetrievedDocument) -> bool:
        """A number near the variable (numeric questions); a mention otherwise."""
        if self._value_near_variable is None:
            return self.mentions_variable(doc)
        return bool(self._value_near_variable.search(_document_text(doc)))

    def score(self, doc: RetrievedDocument, level: str | None = None) -> float:
        if self._variable is None:
            return 0.0
        text = _document_text(doc)
        has_variable = bool(self._variable.search(text))
        score = 3.0 if has_variable else 0.0
        if self._condition is not None and self._condition.search(text):
            score += 3.0 if self.value_first else 2.0
        elif self._related is not None and self._related.search(text):
            score += 1.0
        value_pattern = self._value_near_variable
        if has_variable and value_pattern is not None and value_pattern.search(text):
            score += 6.0 if self.value_first else 2.0
        if self._context is not None and self._context.search(text):
            score += 0.5
        if self.age_penalty and age_mismatch(text, self._age_group):
            score -= 4.0
        if self.related_penalty and level is not None and "related" in level:
            score -= 2.0
        return score

    def rank(
        self, docs: Sequence[RetrievedDocument], levels: dict[str, str] | None = None
    ) -> list[RetrievedDocument]:
        """Highest score first; ties keep the source's own order (sort is stable)."""
        levels = levels or {}
        return sorted(docs, key=lambda d: self.score(d, levels.get(doc_key(d))), reverse=True)

    def sentence_score(self, sentence: str) -> float:
        """How much a sentence is worth keeping in an excerpt (0 = no variable mention)."""
        if self._variable is None or not self._variable.search(sentence):
            return 0.0
        score = 1.0
        if self._value_near_variable is not None and self._value_near_variable.search(sentence):
            score += 3.0
        if self._condition is not None and self._condition.search(sentence):
            score += 1.0
        return score


# --- excerpts -----------------------------------------------------------------------------------

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(\[])")


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_END.split(" ".join(text.split())) if s.strip()]


def excerpt(blocks: Sequence[str], scorer: RelevanceScorer, max_chars: int) -> str | None:
    """The sentences about the variable, best first until ``max_chars``, in document order.

    Sentences stating a value outrank bare mentions. When space remains, the sentence before
    each chosen one is added (it often names the population). None if no sentence mentions the
    variable, so the caller can fall back to the start of the text.
    """
    sentences = [s for block in blocks for s in split_sentences(block)]
    scored = sorted(
        ((scorer.sentence_score(s), i) for i, s in enumerate(sentences)),
        key=lambda item: (-item[0], item[1]),
    )
    chosen: set[int] = set()
    used = 0
    for score, index in scored:
        if score <= 0:
            break
        cost = len(sentences[index]) + 3
        if used + cost <= max_chars or not chosen:
            chosen.add(index)
            used += cost
    if not chosen:
        return None
    for index in sorted(chosen):
        before = index - 1
        if before >= 0 and before not in chosen and used + len(sentences[before]) + 3 <= max_chars:
            chosen.add(before)
            used += len(sentences[before]) + 3
    parts: list[str] = []
    previous: int | None = None
    for index in sorted(chosen):
        if previous is not None and index != previous + 1:
            parts.append("…")
        parts.append(sentences[index])
        previous = index
    text = " ".join(parts)
    return text if len(text) <= max_chars else text[: max_chars - 1].rstrip() + "…"


# --- population ---------------------------------------------------------------------------------

_PEDIATRIC = re.compile(
    r"\b(?:children|child|childhood|pediatric|paediatric|infants?|infancy|neonates?|neonatal|"
    r"newborns?|preterm|adolescents?|toddlers?|boys|girls)\b",
    re.I,
)
_ADULT = re.compile(
    r"\b(?:adults?|elderly|older (?:adults|patients|people)|aged (?:1[89]|[2-9]\d)|women|men|"
    r"postmenopausal|pregnan\w*)\b",
    re.I,
)


def age_mismatch(text: str, patient_age_group: str | None) -> bool:
    """True when the text is about another age group than the patient's (and not also theirs)."""
    if patient_age_group is None:
        return False
    pediatric, adult = bool(_PEDIATRIC.search(text)), bool(_ADULT.search(text))
    if patient_age_group == "adult":
        return pediatric and not adult
    return adult and not pediatric
