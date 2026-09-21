"""Cross-query consistency store for facts answered during a session."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, Field, ValidationError

from medsim import rules, units
from medsim.models import Confidence, LedgerFact

LEDGER_FORMAT_VERSION: Final = 2


class _CaseEntries(BaseModel):
    facts: dict[str, LedgerFact] = Field(default_factory=dict)  # fact key -> fact
    queries: dict[str, str] = Field(default_factory=dict)  # normalized query -> fact key


class _LedgerState(BaseModel):
    version: Literal[2] = LEDGER_FORMAT_VERSION
    cases: dict[str, _CaseEntries] = Field(default_factory=dict)  # case_id -> entries


class FactLedger:
    """Stores ``(clinical_variable, value, unit, source_doc_ids)`` facts per case.

    Facts are scoped by ``case_id`` and keyed by ``variable@timepoint`` within a case, so a
    lookup only hits facts recorded for the same case id.
    """

    def __init__(self) -> None:
        self._state = _LedgerState()

    # -- keys -----------------------------------------------------------------------------------

    @staticmethod
    def key_for(query: str, clinical_variable: str | None = None) -> str:
        variable = rules.canonical_variable(query)
        if variable is None and clinical_variable:
            variable = rules.canonical_variable(clinical_variable) or re.sub(
                r"\W+", "_", clinical_variable.lower()
            ).strip("_")
        point = rules.timepoint(query) or (rules.timepoint(clinical_variable or "") or None)
        if variable is None:
            return "query:" + rules.normalize_query(query)
        return rules.ledger_key(variable, point)

    # -- lookups --------------------------------------------------------------------------------

    def lookup(
        self, query: str, clinical_variable: str | None = None, *, case_id: str
    ) -> LedgerFact | None:
        """Find an equivalent question previously answered for ``case_id``.

        Matches on exact normalized text or on the same ``variable@timepoint`` key.
        """
        entries = self._state.cases.get(case_id)
        if entries is None:
            return None
        key = entries.queries.get(rules.normalize_query(query))
        if key is None:
            key = self.key_for(query, clinical_variable)
        return entries.facts.get(key)

    def render_answer(self, fact: LedgerFact, query: str) -> str:
        """The stored answer verbatim, plus a deterministic conversion if another unit is asked."""
        wanted = units.requested_unit(query)
        if wanted is None:
            return fact.answer
        value_unit = self._numeric(fact)
        if value_unit is None:
            return fact.answer
        value, unit = value_unit
        variable = fact.clinical_variable.split("@", 1)[0]
        if unit == wanted or not units.can_convert(unit, wanted, variable):
            return fact.answer
        converted = units.convert(value, unit, wanted, variable)
        return f"{fact.answer} ({units.format_value(converted, wanted)})"

    @staticmethod
    def _numeric(fact: LedgerFact) -> tuple[float, str] | None:
        unit = units.normalize_unit(fact.unit)
        if unit is not None:
            try:
                return float(fact.value), unit
            except ValueError:
                pass
        return units.parse_value_unit(fact.answer)

    # -- writes ---------------------------------------------------------------------------------

    def record(
        self,
        *,
        case_id: str,
        query: str,
        answer: str,
        answer_source: Literal["case_study", "literature"],
        clinical_variable: str | None = None,
        value: str | None = None,
        unit: str | None = None,
        source_doc_ids: list[str] | None = None,
        evidence: list[str] | None = None,
        confidence: Confidence = "high",
    ) -> LedgerFact:
        key = self.key_for(query, clinical_variable)
        if value is None:
            parsed = units.parse_value_unit(answer)
            if parsed is not None:
                value, unit = f"{parsed[0]:g}", parsed[1]
        fact = LedgerFact(
            case_id=case_id,
            clinical_variable=key,
            value=value if value is not None else answer,
            unit=units.normalize_unit(unit),
            source_doc_ids=list(source_doc_ids or []),
            answer=answer,
            query=query,
            answer_source=answer_source,
            evidence=list(evidence or []),
            confidence=confidence,
        )
        entries = self._state.cases.setdefault(case_id, _CaseEntries())
        entries.facts[key] = fact
        entries.queries[rules.normalize_query(query)] = key
        return fact

    def reset(self, case_id: str | None = None) -> None:
        """Clear facts for one case, or for every case when ``case_id`` is None."""
        if case_id is None:
            self._state = _LedgerState()
        else:
            self._state.cases.pop(case_id, None)

    # -- views & persistence --------------------------------------------------------------------

    @property
    def case_ids(self) -> list[str]:
        return list(self._state.cases)

    @property
    def facts(self) -> list[LedgerFact]:
        return [fact for entries in self._state.cases.values() for fact in entries.facts.values()]

    def facts_for(self, case_id: str) -> list[LedgerFact]:
        entries = self._state.cases.get(case_id)
        return list(entries.facts.values()) if entries else []

    def __len__(self) -> int:
        return sum(len(entries.facts) for entries in self._state.cases.values())

    def prompt_block(self, case_id: str) -> str:
        """Facts already established for ``case_id`` only; other cases never leak into prompts."""
        facts = self.facts_for(case_id)
        if not facts:
            return "(none)"
        lines = []
        for fact in facts:
            unit = f" {fact.unit}" if fact.unit else ""
            lines.append(
                f'- {fact.clinical_variable}: {fact.value}{unit} — "{fact.answer}" '
                f"(source: {fact.answer_source})"
            )
        return "\n".join(lines)

    def to_json(self) -> str:
        return self._state.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, data: str) -> FactLedger:
        try:
            state = _LedgerState.model_validate_json(data)
        except ValidationError as exc:
            try:
                version = json.loads(data).get("version")
            except (ValueError, AttributeError):
                version = None
            if version is not None and version != LEDGER_FORMAT_VERSION:
                raise ValueError(
                    f"Ledger format version {version} is not supported (expected "
                    f"{LEDGER_FORMAT_VERSION}); older ledgers have no case ids, so start a new "
                    "session instead of loading this file."
                ) from None
            raise ValueError(f"Invalid ledger file: {exc}") from None
        ledger = cls()
        ledger._state = state
        return ledger

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> FactLedger:
        return cls.from_json(Path(path).read_text(encoding="utf-8"))
