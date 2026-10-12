"""Knowledge-driven search (Meeting 63, slide 9).

Collect new information, recognize patterns in it, and stop once the information is
satisficing: a pattern is complete. No diagnosis is named until the end.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from medsim.models import LLMCallRecord
from strategies.base import CaseContext, Diagnosis, Question
from strategies.common import (
    CLINICIAN,
    QUESTION_RULES,
    LLMSession,
    LLMStrategy,
    LLMStrategyParams,
)

RECOGNISE = f"""\
{CLINICIAN}

You reason from the data, not from hypotheses. Group what is known into clinical patterns: \
syndromes or problem descriptions such as "febrile illness with a new murmur". Do not name a \
disease. For each pattern, list the findings that are present and the key findings that are \
still missing before the pattern is complete enough to recognize.

Return only a JSON object with keys findings (the facts known about the patient), patterns (a \
list of objects with keys name, present and missing) and basics_covered (true once the \
presenting complaint, its history and the basic examination or vital signs are known)."""

ASK_MISSING = f"""\
{CLINICIAN}

You reason from the data, not from hypotheses. Ask for the most informative finding that is \
still missing from the clinical picture. With nothing known yet, ask for the presenting \
complaint. Do not name or imply a diagnosis.

{QUESTION_RULES}

Return only a JSON object with keys question, fills (the missing finding it asks for) and \
rationale (one sentence)."""


class Pattern(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    present: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)


class ClinicalPicture(BaseModel):
    model_config = ConfigDict(extra="ignore")

    findings: list[str] = Field(default_factory=list)
    patterns: list[Pattern] = Field(default_factory=list)
    basics_covered: bool = False


class GapQuestion(BaseModel):
    model_config = ConfigDict(extra="ignore")

    question: str
    fills: str = ""
    rationale: str = ""


class KnowledgeStrategy(LLMStrategy[LLMStrategyParams]):
    name = "knowledge"
    description = (
        "Knowledge-driven search: asks for the findings a clinical pattern still lacks, and "
        "stops once a pattern is complete; a diagnosis is named only at the end."
    )
    params_model = LLMStrategyParams

    def prompts(self) -> dict[str, str]:
        return {"recognise": RECOGNISE, "ask": ASK_MISSING}

    def new_session(self, context: CaseContext) -> KnowledgeSession:
        return KnowledgeSession(self, context)


class KnowledgeSession(LLMSession):
    def __init__(self, strategy: KnowledgeStrategy, context: CaseContext) -> None:
        super().__init__(strategy, context)
        self.picture = ClinicalPicture()

    def render_picture(self) -> str:
        if not self.picture.patterns:
            return "Clinical picture: (none yet)"
        lines = [
            f"- {p.name}; present: {', '.join(p.present) or '-'}; "
            f"missing: {', '.join(p.missing) or 'nothing'}"
            for p in self.picture.patterns
        ]
        return "Clinical picture:\n" + "\n".join(lines)

    def satisficing(self) -> bool:
        complete = any(p.present and not p.missing for p in self.picture.patterns)
        return complete and self.picture.basics_covered

    def next_question(self) -> Question | None:
        records: list[LLMCallRecord] = []
        if len(self.memory):
            self.picture = self.call(
                RECOGNISE, f"{self.transcript()}\n\n{self.render_picture()}", ClinicalPicture,
                records,
            )  # fmt: skip
            if self.satisficing():
                self.carried.extend(records)
                return None
        turn = self.call(
            ASK_MISSING,
            f"{self.transcript()}\n\n{self.render_picture()}\n\n{self.budget_line()} "
            "Ask the next question.",
            GapQuestion,
            records,
        )
        if not turn.question.strip():
            self.carried.extend(records)
            return None
        return Question(
            turn.question.strip(),
            turn.rationale.strip() or None,
            records,
            trace={"picture": self.picture.model_dump(), "fills": turn.fills},
        )

    def final_diagnosis(self) -> Diagnosis:
        return self.diagnose(
            self.render_picture().replace("Clinical picture", "Patterns before the last answer"),
            trace={"picture": self.picture.model_dump(), "satisficing": self.satisficing()},
            style="Match the clinical picture to the diagnoses it fits.",
        )
