# Retrieval benchmark

Grades the answers medsim generates with a panel of three LLM judges, and compares retrieval
methods on the same questions, including their cost.

## Idea

A case report already states many values, so the benchmark hides one, lets medsim retrieve
literature and answer, and grades the answer against the hidden value (**masked correctness**).
For values the case never states there is no true value, so the answer is instead checked
against everything the case does state, diagnosis included (**factual consistency**). Set C
asks about information the case states, which medsim can answer from the case itself; it is a
reference for how well medsim uses the case, and is graded by both metrics.

| | Set A: hidden value | Set B: value never stated | Set C: information stated |
|---|---|---|---|
| Question | A value the case reports, removed from the case text | A common vital or lab the case never mentions | One fact per case the case states, written by an LLM |
| Case given to medsim | redacted | original | original |
| Retrieval | yes | yes | no (`case_information`) |
| Metric | masked correctness | factual consistency | both |

## Steps

Each step appends JSONL to one workspace directory and resumes where it stopped. Rerunning a
step retries failed records only.

```bash
python -m bench --out environment/results/retrieval_benchmark --workers 8 extract --limit 70
```

```bash
python -m bench --out environment/results/retrieval_benchmark --workers 8 redact --set-a 35 --set-b 15
```

```bash
python -m bench --out environment/results/retrieval_benchmark --workers 6 run --configs current,openrouter_search
```

```bash
python -m bench --out environment/results/retrieval_benchmark --workers 8 judge
```

```bash
python -m bench --out environment/results/retrieval_benchmark --workers 8 validate --controls 10 --flips 10
```

```bash
python -m bench --out environment/results/retrieval_benchmark report
```

1. **extract**: an LLM lists every measured value in each case (variable, value, unit,
   timepoint, verbatim span, category). Code keeps a value only if its span and number are
   verbatim in the case, it is a vital sign, lab, or body measurement, a clinician could ask for
   it without knowing the diagnosis, and the case states that variable only once.
2. **redact**: builds the questions.
   - Set A: an LLM removes the value (and any restatement) from the case. Code then checks
     that the span and number are gone, that no number was added, and that little else changed.
     Finally medsim's own Stage A must fail to answer the question from the redacted case, so
     retrieval really runs.
   - Set B: a variable from a fixed list that the case never mentions, also checked with Stage A.
   - Both record the case's source article (PMCID from the case id, PMID via Europe PMC).
3. **run**: asks medsim each question under each configuration (`bench/run.py:CONFIGS`). The
   case's own source article is removed from every source's results before merging, since it
   would leak the hidden value. The removals are recorded.
4. **judge**: every panel judge grades each generated answer (one answer per call, blind to
   the configuration); the answer's label is the panel's vote. Retrieved documents are not
   judged.
5. **validate**: checks the judge panel (see below).
6. **report**: `report.md` and `report.json` in the workspace; `--snapshot NAME` also keeps a
   copy as `reports/NAME.md`, so each evaluation's report is preserved.

### Precomputed questions (`pool` and `sample`)

Extract and redact are the expensive, model-dependent steps, so they can be run once over the
whole dataset:

```bash
python -m bench --out bench_runs/pool --workers 16 pool --model openai/gpt-6-sol
```

This extracts every case and builds every possible question: each eligible hidden value (set
A) and each case x common variable the case never mentions (set B), with the same checks as
`redact` (the Stage A check uses medsim's resolver model). It writes three files, without the
LLM call logs:

- `cases/combined_272_bench_facts.json`: each case's extracted values and eligibility.
- `cases/combined_272_bench_items.json`: one set A question per case (for the 141 cases that
  have one) and one set B question per case (all 272), selected by the rule in the file's
  `metadata.selection` (set A interleaves categories; set B keeps the 14 variables balanced).
- `cases/archive/combined_272_bench_items_all_candidates.json`: every candidate question,
  accepted and rejected (with reasons), kept for later use.

Each file's `metadata` records the source dataset (with its SHA-256), the code version, the
models, every processing setting, the procedure, the rules, the prompts, statistics, and the
cost. Rerunning `pool`
resumes from its workspace and retries LLM errors. A benchmark then starts with `sample`
instead of `extract` and `redact`:

```bash
python -m bench --out environment/results/new_run sample --set-a 35 --set-b 15
```

`sample` walks the candidates in the same seeded order, with the same `--per-case` limit, as
`redact`, but looks each result up in the pool instead of calling an LLM. Pass
`--items-file cases/archive/combined_272_bench_items_all_candidates.json` to sample from every
candidate instead.

Every command also writes its full log to `logs/<UTC time>_<step>.log` in the workspace, and
`manifest.json` records its parameters, summary, and the key's usage before and after.

### Configurations (`bench/run.py:CONFIGS`)

| Name | Retrieval |
|---|---|
| `current` | the original Europe PMC + LitSense retrieval (pinned explicitly: medsim's defaults now include changes 1–4) |
| `current_fixed` | the same, with the Europe PMC retry for replies without results |
| `improved_1to4` | retrieval changes 1–4 (value-first ranking in one list, 50 Europe PMC candidates, animal and age filter, article-body search with excerpts, value-based broadening); medsim's current default |
| `improved_1to5` | plus natural-language LitSense queries |
| `improved_1to6` | plus LLM selection of the final 8 documents |
| `openrouter_search` | OpenRouter's web search server tool (Exa) |
| `openrouter_exa_instant`, `openrouter_parallel_basic`, `openrouter_perplexity` | `openrouter_search` with the Exa (instant mode), Parallel (basic mode) or Perplexity engine; `deepseek/deepseek-v4.1-flash` issues the search (web search cannot run in the Batch API, so not the `:batch` endpoint) |
| `openrouter_google`, `openrouter_openai` | `openrouter_search` with the model's own (native) search: Google Search via `google/gemini-3.1-flash-lite`, OpenAI web search via `openai/gpt-6-luna`. The documents are the search model's quotations or summaries of the sources it cites. The model decides whether to search: a reply with no search and no citation (it answered from memory) is asked again up to twice (`skipped_search_retries`), is never cached, and its cost is added to the search's |
| `case_information` | no retrieval: medsim answers from the case or not at all (a question the case cannot answer ends on `no_documents`); every stage on `deepseek/deepseek-v4.1-flash:batch`. For set C |
| `gemini_knowledge` | no search: `google/gemini-3-flash-preview` gets the question, the case information as medsim sees it (redacted for set A), and the diagnosis, and gives the value that typically fits; that answer is the one document medsim's stages use. Its cost counts as retrieval (stage `knowledge_source`) |
| `sentences`, `no_rerank`, `reference_only` | ablations of the default method |

### Best-guess fallback and replay

Since 2026-09-29, when the documents give no usable basis for the variable, or the search found
no documents at all, medsim's synthesizer (Stage C) makes its best guess of the value that fits
the patient from the case study and diagnosis instead of declining
(`medsim/stages/synthesizer.py`, rule 6; `medsim/environment.py`). Such an answer takes the
path `best_guess` (answer source `literature`, confidence low, no supporting documents), so the
report can count it separately ("Questions answered with a best guess").

`replay` reruns medsim's stages A-C on an earlier run's documents, without searching again, for
the answers on the given paths:

```bash
python -m bench --out WORKSPACE --workers 24 replay --configs current,... --paths synthesizer_unanswerable
```

With `--search`, the question is searched anew instead (for an original whose search gave
nothing usable, e.g. a skipped native search); the earlier search's cost and time are added to the
new record, as for a retry. The new record is appended (it supersedes the original, which stays in
the file) and records the replay in `replay`: the original's start time, path, and answer, and the retrieval cost and time
it reuses. The retrieval cost is kept and the original retrieval time is added to the new wall
time, so cost and time remain comparable with records that were not replayed. A replayed record
is not replayed again. Then `judge` grades the new answers.

### Set C questions (`set-c`)

```bash
python -m bench --out environment/results/set_c --workers 16 set-c
```

The question writer (`MEDSIM_QUESTION_WRITER_MODEL`; default the main judge) picks one fact per
case that the case states explicitly, preferably a measured value, otherwise a specific
examination, imaging, or history finding, never the diagnosis, a treatment, or an outcome. It
returns the question, the answer, and the verbatim span. Code keeps the question only if the span
is verbatim in the case, a numeric answer occurs in its span, the question does not name the
diagnosis, and a numeric answer does not appear in the question; otherwise the writer rewrites
it once with the reason (`bench/set_c.py`). The questions are also exported to
`cases/combined_272_bench_set_c_items.json`. Then `run --configs case_information`, `judge`, and
`report` as usual; set C answers get both metrics, with set C wording in the judge prompts (the
value was visible, and may be a finding rather than a number).

## Judge panel and majority vote

Three judge models from three families (`MEDSIM_JUDGE_MODELS`; defaults below) each grade every
answer independently, and every judge's verdict is stored (`judge/masked_correctness.jsonl`,
`judge/factual_consistency.jsonl`, one record per answer and judge). The answer's final label is
the panel's **majority vote**: a label chosen by at least two of the three judges. With no
majority (three different labels, or a 1–1 split because one judge failed every retry), the
**main judge** (the first in the list) decides, or, if the main judge has no verdict, the next
judge. The metrics and every report table count only this voted label; the report also shows how
each label was reached (unanimous, majority, tie broken) and how often each pair of judges agrees.

All (answer, judge) calls run in one thread pool (`--workers`), so the judges work in parallel
with each other and across answers. A rerun judges only the missing or failed (answer, judge)
pairs.

## Judge rubric

Each judge grades medsim's final answer whenever medsim generated one (answer source
`literature` or `case_study`), always against the full case information: the unredacted case
report and the true diagnosis. Set A items store only the redacted case, so `judge` and
`validate` read the original from the case file (`--cases`; default: the file the questions
were built from) and stop if a case is missing or no longer states the hidden value. Prompts:
`bench/judge.py`.

**Masked correctness (set A).** The judge sees the question, the full case report, the true
diagnosis, the hidden true value (also given separately), and the answer.

| Verdict | Meaning |
|---|---|
| exact | the true value is inside the range the answer states, or the answer's single value is clinically the same finding (about 10–15% or the measurement's usual variability) |
| same category | not exact, but the same low / normal / high category as the true value |
| different category | the answer implies another category |
| not comparable | no value or direction for this variable, another variable, or units that cannot be converted |

**Factual consistency (set B).** The judge sees the question, the full (unredacted) case
report, the true diagnosis, and the answer, and labels it consistent (nothing in the case
contradicts it and it is plausible for this patient) or inconsistent (it contradicts a stated
fact or is implausible given the diagnosis and findings). It also lists the conflicting case
spans.

## Metrics

For each environment setting (retrieval method), the result is every label of each metric with
the percentage of questions in its set whose voted label it is. The denominator is always
the full question set: every set A question for masked correctness, every set B question for
factual consistency. For example, masked correctness "exact" is 60% when the panel's vote is exact
for 60% of all set A questions.

| Metric (question set) | Labels reported |
|---|---|
| Masked correctness (A, C) | exact, same category (reported as exact + same category), different category, not comparable, no label |
| Factual consistency (B, C) | consistent, inconsistent, no label |

"No label" is not a judge label. It counts questions without a voted label (medsim gave no
answer, the run failed or is missing, or no judge has a verdict yet), so each metric's
labels sum to 100%. Masked correctness "same category" is reported as exact + same category (the
share of answers at least in the true value's category; `bench/report.py:CUMULATIVE`), so exact
is a part of it: same category, different category, not comparable, and no label sum to 100%. Intervals are 95% from a bootstrap that resamples diagnoses (questions about
the same diagnosis are not independent); differences between methods are paired per question.

- **Cost:** OpenRouter's `usage.cost` for every call (search fees included), per method and step.

## Three more answer metrics (2026-10-13)

Added because the two metrics above separate retrieval methods poorly: their labels are
coarse, factual consistency sits at a ceiling of about 97%, and neither looks at the retrieved
documents. Code: `bench/answer_metrics.py` (judging), `bench/zlog.py` (arithmetic),
`results/scripts/make_answer_metrics.py` (scoring). Results and the report:
[../results/answer_metrics/](../results/answer_metrics/).

| | Zlog z-score | Faithfulness | Case alignment |
|---|---|---|---|
| Question | How far is the answer's value from the true value? | Do the retrieved documents support the answer's value? | Does the rest of the case bear on the answer, and which way? |
| Sets | A and C (numeric true values) | A and B | B and C |
| Based on | zlog transformation (Hoffmann et al. 2017) and the proficiency-testing z-score (ISO 13528) | Faithfulness of retrieval-augmented generation (Es et al. 2023, RAGAs) | The three labels of natural language inference (Kryscinski et al. 2019; Sciré et al. 2024) |
| Judge | Reads numbers: per question the reference limits and the true value, per answer the answer's value in the true value's unit | Yes or no, with a verbatim quote from the documents | The level the case leads one to expect, the level the answer states, and a verbatim quote from the case |
| Code | Computes z; the median of the judges' scores | Looks for the quote in the documents (`bench.text.quote_found`); not found = not supported | Looks for the quote in the case; aligned if the levels match, contradicted if not, neutral without an expectation |
| Reported | Mean \|z\| capped at 3; share satisfactory (\|z\| ≤ 2) | Share supported, of all questions | Share aligned, share contradicted, of all questions |

A question medsim did not answer counts as 0 (as 3 for the zlog z-score). Faithfulness has no
value for `gemini_knowledge` and `case_information`, which retrieve no documents.

### Zlog z-score

`zlog(x) = (ln x − (ln LL + ln UL)/2) · 3.92 / (ln UL − ln LL)` puts any result on one scale from
the variable's reference limits, so that the reference interval is −1.96 to +1.96. With the true
value as the assigned value of a proficiency test:

`z = zlog(answer) − zlog(truth) = (ln answer − ln truth) / σ`, `σ = (ln UL − ln LL) / 3.92`

Only the ratio UL / LL enters, so the limits' unit does not matter; the answer and the true
value must share one. ISO 13528 rates |z| ≤ 2 satisfactory and |z| ≥ 3 unsatisfactory.

**Revised scale (the version in use):** σ is multiplied by `max(1, |zlog(truth)| / 3.92)`. In the
first version 22% of scores sat at the cap, many for a very abnormal true value answered with a
similarly abnormal one (haemoglobin 4 g/dL answered as 6.8 scored like a miss). The revision
judges the error against the true value's own deviation when that is far outside the reference
interval; an answer in the middle of the interval still scores 3.92, never satisfactory.
`zlog_score(scale_with_truth=False)` gives the first version.

Rules beyond the two methods (this project's choices):

| Case | Rule |
|---|---|
| Reference limits | Asked once per question from every chat judge and combined by the median (a limit at least half of them leave empty stays empty), so every method and run is scored with the same σ; stored in `results/answer_metrics/zlog_reference.jsonl` |
| Answer given as a range | Continuous ranked probability score of a uniform forecast (Gneiting and Raftery 2007); \|z\| for a single value |
| True value given as a range or bound ("60–70", "> 1000") | 0 for an answer inside it, otherwise the distance to its nearest end |
| One-sided reference range ("< 5") | LL = 15% of UL (recalled from the laboratory literature, not confirmed) |
| No reference interval | σ = 0.15 |
| Truth or answer at or below zero | The same z without logarithms |
| Blood pressure | The systolic value |
| Non-numeric true value ("3+") | Left out (1 of 141 set A questions; 18 of 272 set C questions) |
| Answer without a comparable number, or no answer | 3 |

### Case alignment: two versions

The first version (rubric `m1`) asked for one verdict, aligned / neutral / contradicted, and
counted only explicit statements: 96% of set B answers came back neutral and none contradicted.
The version in use (`m2`) lets the clinical picture set an expectation: the judge gives the
expected level (low / normal / high, or present / absent for a finding; "none" when the case
gives no reason to expect one) and the level the answer states; code compares them. Both
versions' judgments are in `judge/case_alignment.jsonl`, told apart by `rubric`.

### The Jev decision model

`typesafe/jev-1.13` returns a typed choice with probabilities through OpenRouter's decisions
endpoint (`POST /api/alpha/decisions`, one item per request), and no text. `JevClient` runs it
as a fourth judge of masked correctness, factual consistency, faithfulness, and case alignment.
It cannot read out a number (no zlog z-score) or quote a passage (no quote check). Its verdicts
on the two existing metrics are stored in the panel's judgment files, its probabilities in
`rationale`. It is not in the default panel; `make_answer_metrics.py` scores every table with
the three judges and again with Jev added.

### Running it

```bash
python -m bench.answer_metrics --metrics reference                      # reference limits, once
python -m bench.answer_metrics --runs 1-10 --metrics zlog_value,faithfulness,case_alignment
python -m bench.answer_metrics --runs 1-10 --judges typesafe/jev-1.13 \
  --metrics masked_correctness,factual_consistency,faithfulness,case_alignment
PYTHONPATH=environment python environment/results/scripts/make_answer_metrics.py full
PYTHONPATH=environment python environment/results/scripts/make_answer_metrics_report.py
```

Each judge works in its own pool (`--workers` per judge); jobs already done are skipped; the
step stops starting calls on HTTP 402. `make_answer_metrics.py test --run 2 --panel MODEL` gives
one run's sensitivity (the spread of the configurations' means over their bootstrap standard
error, and the pairs whose paired 95% interval excludes zero).

### Result (2026-10-13)

Sensitivity over the judged runs, three judges (spread of the six repeated configurations'
means ÷ pooled run-to-run SD; pairs separated at 2.3 standard errors):

| Metric | Runs | Signal ÷ noise | Pairs separated |
|---|---|---|---|
| Masked correctness: same category | 10 | 0.58 | 3 of 15 |
| Factual consistency: consistent | 10 | 0.22 | 0 of 15 |
| Zlog z-score: mean \|z\| | 10 | 0.52 | 2 of 15 |
| Faithfulness: supported | 9 | 8.13 | 10 of 10 |
| Case alignment: aligned | 9 | 1.05 | 8 of 15 |
| Case alignment: contradicted | 9 | 1.39 | 9 of 15 |

Faithfulness is the metric that separates retrieval methods (21–59% supported); the zlog
z-score shows the answers are equally close whatever the method. Faithfulness and case
alignment by the chat judges cover runs 1–9: the API key reached its total limit during run 10.
The scores are in `results/answer_metrics/answer_metrics.md`; the full account is
`answer_metrics_report.pdf`.

Not done: the planned sanity check of faithfulness (another question's documents should give
"not supported"), and human labels for the new metrics.

## Document metrics: truth coverage and graded relevance (2026-10-16)

Metrics on the retrieved documents themselves, for set A, and the search for the Europe PMC +
LitSense settings that score highest on them. Code: `bench/doc_metrics.py`; report:
`results/scripts/make_doc_metrics_report.py`; results:
[../results/doc_metrics/](../results/doc_metrics/) (`doc_metrics_report.pdf`, `scores.json`).

- **Strict truth coverage** (decides): a document gives a value or range for the variable in
  patients with this or a closely related condition, and the hidden true value lies inside it or
  within about 15%. **Category coverage**: a document puts the true value in the same low /
  normal / high category (a reference range for comparable patients counts).
- **Graded relevance**: each document 0 / 1 / 2; **nDCG@8** against eight grade-2 documents
  (breaks ties) and **precision@8**.
- One judge call (`anthropic/claude-haiku-5.5`) per question grades all eight documents; every
  positive verdict needs a verbatim quote that code finds in the named document.
- Configurations run retrieval only, on one frozen query per question (`queries`; Stages A and B
  with `deepseek/deepseek-v4-flash-0731`). `name+other` combines changes, `name@fresh1` uses
  another set of frozen queries, `name#2` repeats a configuration under another label (same
  cached documents, so it measures the judge's noise). A question where a source failed is
  retrieved again on rerun.

```bash
PYTHONPATH=.:environment python -m bench.doc_metrics queries [--query-set fresh1]
PYTHONPATH=.:environment python -m bench.doc_metrics retrieve --configs baseline,llm_select20
PYTHONPATH=.:environment python -m bench.doc_metrics judge --configs baseline [--shuffled] [--stored 2-6]
PYTHONPATH=.:environment python -m bench.doc_metrics score
```

Result: LLM selection of the final 8 documents from the best 20, with 25 Europe PMC candidates
and MeSH synonyms (`llm_select20+epmc25+q_synonym`), raised strict coverage from 60.3% to 70.2%
(+9.9 points, 95% CI +3.5 to +17.0) and nDCG@8 from 0.691 to 0.750; on two fresh query sets the
gain was +7.1 and +12.1 points. LLM selection alone accounts for most of it. Full-text excerpts,
the lexical rerank and Europe PMC are each worth 20–30 points. The shuffled control scores 0%.

Faithfulness of the answers medsim writes on those documents (`answer`, then `faithfulness`, with
the rubric of `bench.answer_metrics` and the same judge): 22.0% supported for the baseline and
32.6% for the winner (+10.6 points, 95% CI +2.8 to +19.1). For about 44% of questions the
documents cover the truth but the answer is not supported by them, in both configurations: there
the answer-writing stage, not retrieval, loses the value.

## Judge validation

Controls and flips are judged by the whole panel and pass or fail on the voted label; each
judge's verdict is stored with the result.

- **Controls:** synthetic set A answers: the true value itself (expected: exact) and a value
  far from it (expected: same category or different category).
- **Flipped truth:** answers the panel voted "exact" are re-judged with the true value moved far
  away (in the full case text as well); the voted label should change.
- **Panel agreement** (no extra calls): how each label was reached, and Cohen's κ for each pair
  of judges.
- **Human labels:** `validate --export-human N` writes `validate/human_labels.csv`; fill in
  `human_masked_verdict` (set A rows) or `human_consistency` (set B rows: consistent /
  inconsistent) and rerun `report`; the report compares them with the voted label.

## Models and settings

Environment variables with the `MEDSIM_` prefix, as for medsim:

| Variable | Default |
|---|---|
| `MEDSIM_JUDGE_MODELS` (JSON list; the first is the main judge) | `["anthropic/claude-haiku-5.5", "z-ai/glm-5.3-flash", "openai/gpt-6-luna"]` (until 2026-10-13: `["google/gemini-3.5-flash-lite", "qwen/qwen3.8-flash", "openai/gpt-6-luna"]`, whose verdicts stay in the judgment files) |
| `MEDSIM_EXTRACTOR_MODEL`, `MEDSIM_REDACTOR_MODEL` | the main judge |
| `MEDSIM_JUDGE_MAX_TOKENS`, `MEDSIM_EXTRACTOR_MAX_TOKENS`, `MEDSIM_REDACTOR_MAX_TOKENS` | 4000, 8000, 8000 |
| `MEDSIM_JUDGE_MAX_ATTEMPTS`, `MEDSIM_JUDGE_RETRY_BACKOFF_S` | 3, 2.0 |

Each judge's judgment of an answer is retried on its own (backoff 2 s, then 4 s) when the call fails or the reply is
unusable. Each attempt already retries network errors, HTTP 429/5xx and empty replies (2 times),
a reply cut off by `max_tokens` (once, with double the budget) and invalid JSON or a label
outside the allowed set (one repair request). A judgment that fails every attempt is stored as an
error, and rerunning `judge` retries only those.

The judges come from three model families other than the pipeline's (DeepSeek), so no judge
grades its own family's answers. `temperature` is sent only to models whose OpenRouter endpoints
accept it (reasoning models such as `gpt-6-luna` do not); the client drops it automatically when
OpenRouter reports no endpoint for the requested parameters.

## Limits

- Case reports are published because something was unusual, so masked correctness cannot reach
  100%.
  Compare methods with each other, not with a perfect score.
- Set A leans toward values notable enough to report; set B covers the everyday case.
- The judges are LLMs. Read the panel agreement and validation sections before trusting
  absolute numbers.
