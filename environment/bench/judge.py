"""Step 4: a panel of LLM judges grades medsim's generated answers against the full case.

Every answer is judged independently by each panel model (all calls run in parallel), each
verdict is stored, and the answer's final label is the panel's majority vote; with no majority,
the main (first) judge's label decides. Both metrics' judges see the full, unredacted case
(diagnosis included) and the answer. Masked
correctness (set A) grades the answer against the value that was hidden from medsim: exact,
same category, or different category. Factual consistency (set B) labels the answer consistent or
inconsistent with everything the case states. Retrieved documents are not judged.
"""

from __future__ import annotations

import hashlib
import logging
import time
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from functools import partial
from typing import Any, TypeVar

from bench.schemas import (
    ConsistencyJudgment,
    ConsistencyOutput,
    Item,
    MaskedCorrectnessJudgment,
    MaskedCorrectnessOutput,
    RunRecord,
    calls_cost,
)
from bench.text import count_value
from bench.workspace import JsonlWriter, Workspace, latest_by, read_models
from medsim.errors import ConfigError, LLMError, MedSimError
from medsim.llm.base import LLMClient
from medsim.llm.structured import call_structured
from medsim.models import CaseStudy, ChatMessage, LLMCallRecord

logger = logging.getLogger("bench.judge")

RUBRIC = "v2"

MASKED_CORRECTNESS_PROMPT = """\
A patient simulator answered a question about a patient. The value it was asked for is stated \
in the patient's case report but was hidden from the simulator, so it synthesized one. You see \
the FULL CASE REPORT, including the true DIAGNOSIS and the TRUE value, which is also given \
separately. Decide whether the SIMULATED ANSWER points to the TRUE value, reading the TRUE value \
in the context of the whole case (the patient, the timepoint, and the other findings).

Fields:
- reference_range: the usual reference range you use for this variable in this kind of patient, \
with unit.
- truth_category: the TRUE value relative to that range: "low", "normal", or "high" (for blood \
pressure, use the more abnormal component).
- answer_value: the value or range the simulated answer states, with unit ("" if none).
- rationale: one or two sentences.
- verdict: "exact" = the TRUE value lies inside the range the answer states, or the answer \
states a single value that is clinically the same finding as the TRUE value (within about 10-15% \
or the measurement's usual variability); "same_category" = not exact, but the answer implies the \
same category (low/normal/high) as the TRUE value, including an answer that gives only a \
matching direction (e.g. "elevated"); "different_category" = the answer implies a different \
category than the TRUE value; "not_comparable" = the answer gives no value or direction for \
this variable, gives another variable, or uses units that cannot be converted.
Convert units when needed. Return only a JSON object with exactly these keys."""

FACTUAL_CONSISTENCY_PROMPT = """\
A patient simulator answered a question about a patient. The case report never states the value \
asked for, so the simulator synthesized one. You see the FULL CASE REPORT, including the true \
DIAGNOSIS. Decide whether the SIMULATED ANSWER is factually consistent with everything the case \
report states.

Fields:
- answer_value: the value, range, or finding the simulated answer states, with unit ("" if none).
- conflicting_facts: the verbatim spans of the case report that the answer conflicts with, \
copied exactly; [] if none.
- rationale: one or two sentences.
- verdict: "consistent" = nothing in the case report contradicts the answer, and the answer is \
physiologically plausible for this patient given the diagnosis, findings, treatments, and \
timeline, even if it is not the most typical value; "inconsistent" = the answer contradicts \
something the case report states (a finding, measurement, test result, complication, treatment \
response, or the course of illness), or it is implausible for this patient given the diagnosis \
and findings (e.g. a normal blood pressure in a patient described as in shock, or an adult value \
for an infant).
Judge only against the case report and established physiology; do not require the answer to \
match the value you would have guessed. Return only a JSON object with exactly these keys."""


# Set C: the answer is stated in the case the simulator could read, and need not be a number.
CASE_CORRECTNESS_PROMPT = """\
A patient simulator answered a question about a patient. The answer is stated in the patient's \
case report, which the simulator could read. You see the FULL CASE REPORT, including the true \
DIAGNOSIS, and the TRUE answer as the case states it, which is also given separately. Decide \
whether the SIMULATED ANSWER matches the TRUE answer.

Fields:
- reference_range: for a measurement, the usual reference range you use for this variable in \
this kind of patient, with unit; "" for a finding or history item.
- truth_category: for a measurement, the TRUE value relative to that range: "low", "normal", or \
"high" (for blood pressure, use the more abnormal component); "not_applicable" for a finding or \
history item.
- answer_value: the value, range, or finding the simulated answer states, with unit ("" if none).
- rationale: one or two sentences.
- verdict: "exact" = the answer states the TRUE answer: the same value (a stated range that \
contains it, or a single value within about 10-15% or the measurement's usual variability), or \
the same finding with the details that matter clinically; "same_category" = not exact, but \
consistent with it: the same category (low/normal/high) for a measurement, or the same finding \
with a wrong or missing detail (location, severity, timing) that does not change its meaning; \
"different_category" = the answer contradicts the TRUE answer (another category, a finding the \
case reports as absent, or the reverse); "not_comparable" = the answer does not address this \
question.
Convert units when needed. Return only a JSON object with exactly these keys."""

_CONSISTENCY_INTRO_B = """\
A patient simulator answered a question about a patient. The case report never states the value \
asked for, so the simulator synthesized one."""
_CONSISTENCY_INTRO_C = """\
A patient simulator answered a question about a patient from the patient's case report, which \
it could read."""
assert FACTUAL_CONSISTENCY_PROMPT.startswith(_CONSISTENCY_INTRO_B)
FACTUAL_CONSISTENCY_PROMPT_C = FACTUAL_CONSISTENCY_PROMPT.replace(
    _CONSISTENCY_INTRO_B, _CONSISTENCY_INTRO_C, 1
)


# --- prompts ------------------------------------------------------------------------------------


def _target(item: Item) -> str:
    when = f" ({item.timepoint})" if item.timepoint else ""
    return f"{item.variable}{when}"


def _truth(item: Item, override: str | None = None) -> str:
    assert item.truth is not None
    if override is not None:
        return override
    unit = f" {item.truth.unit}" if item.truth.unit else ""
    return f'{item.truth.value}{unit} (case report: "{item.truth.span}")'


def _full_case(case: CaseStudy) -> str:
    findings = "".join(f"\n- {k}: {v}" for k, v in case.structured_findings.items())
    return case.narrative.strip() + (f"\n\nStructured findings:{findings}" if findings else "")


def masked_correctness_messages(
    item: Item, case: CaseStudy, answer: str, truth: str | None = None
) -> list[ChatMessage]:
    user = (
        f"QUESTION: {item.question}\nTARGET VARIABLE: {_target(item)}\n"
        f"TRUE VALUE: {_truth(item, truth)}\nDIAGNOSIS: {case.diagnosis}\n\n"
        f"FULL CASE REPORT:\n{_full_case(case)}\n\nSIMULATED ANSWER: {answer}"
    )
    prompt = CASE_CORRECTNESS_PROMPT if item.question_set == "C" else MASKED_CORRECTNESS_PROMPT
    return [
        ChatMessage(role="system", content=prompt),
        ChatMessage(role="user", content=user),
    ]


def consistency_messages(item: Item, case: CaseStudy, answer: str) -> list[ChatMessage]:
    user = (
        f"QUESTION: {item.question}\nTARGET VARIABLE: {_target(item)}\n"
        f"DIAGNOSIS: {case.diagnosis}\n\nFULL CASE REPORT:\n{_full_case(case)}\n\n"
        f"SIMULATED ANSWER: {answer}"
    )
    c = item.question_set == "C"
    prompt = FACTUAL_CONSISTENCY_PROMPT_C if c else FACTUAL_CONSISTENCY_PROMPT
    return [
        ChatMessage(role="system", content=prompt),
        ChatMessage(role="user", content=user),
    ]


# --- judge calls --------------------------------------------------------------------------------


def answer_key(item_id: str, config: str, answer: str) -> str:
    return hashlib.sha256(f"{item_id}\x1f{config}\x1f{answer}".encode()).hexdigest()[:20]


def judgeable(run: RunRecord) -> bool:
    """medsim generated an answer (from the case or from literature)."""
    return run.answer_source in ("case_study", "literature") and bool(run.output_answer)


def full_cases(items: Iterable[Item], cases: Mapping[str, CaseStudy]) -> dict[str, CaseStudy]:
    """The unredacted case for each item, by item id.

    Set A items store the redacted case, so theirs comes from the case file, which must still
    state the hidden value (a check that it is the right file; the wording around the value may
    have been edited since the questions were built). Set B and C items already store the
    original case.
    """
    full: dict[str, CaseStudy] = {}
    problems: list[str] = []
    for item in items:
        case = cases.get(item.case_id)
        if item.question_set in ("B", "C"):
            full[item.item_id] = case or item.case
        elif case is None:
            problems.append(f"{item.item_id}: case {item.case_id} is not in the case file")
        elif item.truth is None or not count_value(case.narrative, item.truth.value):
            problems.append(f"{item.item_id}: the case file does not state the hidden value")
        else:
            full[item.item_id] = case
    if problems:
        raise ConfigError(
            "Full case information is missing for set A question(s); pass the case file the "
            "questions were built from with --cases. " + "; ".join(problems[:5])
        )
    return full


@dataclass
class Judge:
    """One judge model.

    Each judgment is retried as a whole, up to ``max_attempts`` times with exponential backoff,
    when the call fails or its reply is unusable. Within an attempt, the client already retries
    transport errors, HTTP 429/5xx and empty replies, and ``call_structured`` retries a cut-off
    reply with double the budget and repairs invalid JSON (including a label outside the
    allowed set) once. A judgment that still fails is stored with ``status="error"`` and is
    retried the next time the step runs.
    """

    llm: LLMClient
    model: str
    max_tokens: int
    max_attempts: int = 3
    backoff_s: float = 2.0
    sleep: Callable[[float], None] = field(default=time.sleep, repr=False)

    def _call(
        self, messages: list[ChatMessage], output: type[Any], records: list[LLMCallRecord]
    ) -> Any:
        """``records`` collects every call of every attempt, so failed attempts are costed."""
        for attempt in range(1, max(1, self.max_attempts) + 1):
            try:
                return call_structured(
                    self.llm, stage="judge", messages=messages, output_model=output,
                    temperature=0.0, max_tokens=self.max_tokens, model=self.model,
                    records=records,
                )  # fmt: skip
            except LLMError as exc:
                if attempt >= self.max_attempts:
                    raise
                delay = self.backoff_s * 2 ** (attempt - 1)
                logger.warning(
                    "judge %s: attempt %d/%d failed (%s); retrying in %.0fs",
                    self.model, attempt, self.max_attempts, str(exc)[:200], delay,
                )  # fmt: skip
                self.sleep(delay)
        raise AssertionError("unreachable")

    def _base(self, item: Item, config: str, answer: str) -> dict[str, Any]:
        return {"item_id": item.item_id, "config": config,
                "answer_key": answer_key(item.item_id, config, answer),
                "judge_model": self.model, "rubric": RUBRIC}  # fmt: skip

    def masked_correctness(
        self, item: Item, case: CaseStudy, config: str, answer: str, *, truth: str | None = None
    ) -> MaskedCorrectnessJudgment:
        records: list[LLMCallRecord] = []
        base = self._base(item, config, answer) | {"truth_override": truth}
        try:
            out: MaskedCorrectnessOutput = self._call(
                masked_correctness_messages(item, case, answer, truth),
                MaskedCorrectnessOutput,
                records,
            )
        except MedSimError as exc:
            return MaskedCorrectnessJudgment(
                **base, status="error", error=str(exc)[:300], llm_calls=records
            )
        return MaskedCorrectnessJudgment(**base, status="ok", output=out, llm_calls=records)

    def consistency(
        self, item: Item, case: CaseStudy, config: str, answer: str
    ) -> ConsistencyJudgment:
        records: list[LLMCallRecord] = []
        base = self._base(item, config, answer)
        try:
            out: ConsistencyOutput = self._call(
                consistency_messages(item, case, answer), ConsistencyOutput, records
            )
        except MedSimError as exc:
            return ConsistencyJudgment(
                **base, status="error", error=str(exc)[:300], llm_calls=records
            )
        return ConsistencyJudgment(**base, status="ok", output=out, llm_calls=records)

    def judge_answer(
        self, item: Item, case: CaseStudy, config: str, answer: str, metric: str | None = None
    ) -> MaskedCorrectnessJudgment | ConsistencyJudgment:
        """One metric's judgment; by default the set's metric (set C needs ``metric``)."""
        metric = metric or SET_METRICS[item.question_set][0]
        if metric == "masked_correctness":
            return self.masked_correctness(item, case, config, answer)
        return self.consistency(item, case, config, answer)


# Which metrics grade each question set's answers.
SET_METRICS: dict[str, tuple[str, ...]] = {
    "A": ("masked_correctness",),
    "B": ("factual_consistency",),
    "C": ("masked_correctness", "factual_consistency"),
}


# --- panel vote --------------------------------------------------------------------------------

J = TypeVar("J", MaskedCorrectnessJudgment, ConsistencyJudgment)


@dataclass(frozen=True)
class Vote:
    """The panel's final label for one answer, and how it was reached."""

    label: str | None  # None: no judge has a verdict yet
    # unanimous / majority / tie_break_main_judge / tie_break_next_judge (main judge had none)
    resolution: str | None
    votes: dict[str, str | None]  # judge model -> its label (None: no verdict), panel order

    @property
    def n_votes(self) -> int:
        return sum(v is not None for v in self.votes.values())


def vote(votes: Mapping[str, str | None]) -> Vote:
    """Majority vote over ``votes`` (judge model -> label), given in panel order.

    A label chosen by more than half of the panel wins. Otherwise (three different labels, or a
    1-1 split because a judge has no verdict) the tie is broken in panel order: the main judge's
    label decides, or, if the main judge has no verdict, the next judge's.
    """
    ordered = dict(votes)
    cast = [label for label in ordered.values() if label is not None]
    if not cast:
        return Vote(None, None, ordered)
    counts = Counter(cast)
    top_label, top = counts.most_common(1)[0]
    if top * 2 > len(ordered):
        resolution = "unanimous" if top == len(ordered) else "majority"
        return Vote(top_label, resolution, ordered)
    leader = next(label for label in cast if counts[label] == top)  # panel order
    main = next(iter(ordered.values()))
    return Vote(
        leader, "tie_break_main_judge" if leader == main else "tie_break_next_judge", ordered
    )


def panel_judgments(path: Any, model_cls: type[J], panel: Sequence[str]) -> dict[str, dict[str, J]]:
    """Successful judgments by each panel model: answer key -> {judge model: judgment}."""
    by_key: dict[str, dict[str, J]] = {}
    for model in panel:
        for key, judged in ok_judgments(path, model_cls, model).items():
            by_key.setdefault(key, {})[model] = judged
    return by_key


def panel_votes(
    judged: Mapping[str, Any], panel: Sequence[str], field_name: str = "verdict"
) -> Vote:
    """The vote on one output field (``verdict`` or, for masked correctness, ``truth_category``)."""
    return vote({
        model: getattr(j.output, field_name) if (j := judged.get(model)) and j.output else None
        for model in panel
    })  # fmt: skip


# --- step ---------------------------------------------------------------------------------------


def latest_runs(ws: Workspace, configs: Iterable[str]) -> dict[str, dict[str, RunRecord]]:
    """Latest successful run record per item, per configuration."""
    runs: dict[str, dict[str, RunRecord]] = {}
    for config in configs:
        latest = latest_by(read_models(ws.run_file(config), RunRecord), lambda r: r.item_id)
        runs[config] = {k: r for k, r in latest.items() if r.status == "ok"}
    return runs


def ok_judgments(path: Any, model_cls: type[J], judge_model: str) -> dict[str, J]:
    """Successful judgments by one model under the current rubric, by answer key."""
    return {
        r.answer_key: r
        for r in read_models(path, model_cls)
        if r.judge_model == judge_model and r.rubric == RUBRIC and r.status == "ok"
        and getattr(r, "truth_override", None) is None
    }  # fmt: skip


def run_judge(
    ws: Workspace,
    items: Sequence[Item],
    configs: Sequence[str],
    panel: Sequence[Judge],
    *,
    cases: Mapping[str, CaseStudy],
    workers: int = 8,
) -> dict[str, Any]:
    """Every generated answer, by every panel judge, against the full case: masked correctness
    for set A, factual consistency for set B, both for set C. ``cases`` is the unredacted case
    file, by case id.

    Each (answer, judge) pair is one independent job; all of them run in one thread pool, so the
    judges work in parallel with each other and across answers. Pairs already judged are skipped,
    so a rerun retries only the failed ones (or judges added to the panel).
    """
    by_id = {i.item_id: i for i in items}
    full = full_cases(items, cases)
    paths = {"masked_correctness": ws.masked_correctness, "factual_consistency": ws.consistency}
    classes: dict[str, Any] = {
        "masked_correctness": MaskedCorrectnessJudgment,
        "factual_consistency": ConsistencyJudgment,
    }
    done = {
        (metric, judge.model): ok_judgments(paths[metric], classes[metric], judge.model)
        for metric in paths
        for judge in panel
    }
    writers = {metric: JsonlWriter(path) for metric, path in paths.items()}
    jobs = []
    for per_item in latest_runs(ws, configs).values():
        for item_id, run in per_item.items():
            item = by_id.get(item_id)
            if item is None or not judgeable(run):
                continue
            answer = run.output_answer or ""
            key = answer_key(item_id, run.config, answer)
            for metric in SET_METRICS[item.question_set]:
                if metric == "masked_correctness" and item.truth is None:
                    continue
                for judge in panel:
                    if key in done[(metric, judge.model)]:
                        continue
                    job = partial(
                        judge.judge_answer, item, full[item_id], run.config, answer, metric
                    )
                    jobs.append((f"{metric} [{judge.model}]", job, writers[metric]))
    counts: Counter[str] = Counter()
    costs: dict[str, float] = {}
    _run_parallel(jobs, counts, costs, workers)
    failed = sum(n for label, n in counts.items() if label.endswith(":error"))
    if failed:
        logger.warning(
            "%d judgment(s) still failed after %d attempts each; run the judge step again to "
            "retry only those", failed, max(j.max_attempts for j in panel),
        )  # fmt: skip
    return {"panel": [j.model for j in panel], "todo": len(jobs), **counts,
            "cost_usd": {k: round(v, 4) for k, v in costs.items()}}  # fmt: skip


def _run_parallel(
    jobs: Sequence[tuple[str, Callable[[], Any], JsonlWriter]],
    counts: Counter[str],
    costs: dict[str, float],
    workers: int,
) -> None:
    """Run labelled jobs in one pool; write each record as it finishes."""
    total: Counter[str] = Counter(label for label, _, _ in jobs)
    finished: Counter[str] = Counter()
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(fn): (label, writer) for label, fn, writer in jobs}
        for future in as_completed(futures):
            label, writer = futures[future]
            record = future.result()
            writer.write(record)
            counts[f"{label}:{record.status}"] += 1
            costs[label] = costs.get(label, 0.0) + calls_cost(record.llm_calls)
            finished[label] += 1
            if finished[label] % 25 == 0 or finished[label] == total[label]:
                logger.info("judge %s: %d/%d", label, finished[label], total[label])
