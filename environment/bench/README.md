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
| `openrouter_exa_instant`, `openrouter_parallel_basic`, `openrouter_perplexity` | `openrouter_search` with the Exa (instant mode), Parallel (basic mode) or Perplexity engine; `deepseek/deepseek-v4-flash-0731` issues the search |
| `openrouter_google`, `openrouter_openai` | `openrouter_search` with the model's own (native) search: Google Search via `google/gemini-3.1-flash-lite`, OpenAI web search via `openai/gpt-6-luna`. The documents are the search model's quotations or summaries of the sources it cites |
| `case_information` | no retrieval: medsim answers from the case or not at all (a question the case cannot answer ends on `no_documents`); every stage on `deepseek/deepseek-v4-flash-0731`. For set C |
| `sentences`, `no_rerank`, `reference_only` | ablations of the default method |

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
| Masked correctness (A, C) | exact, same category, different category, not comparable, no label |
| Factual consistency (B, C) | consistent, inconsistent, no label |

"No label" is not a judge label. It counts questions without a voted label (medsim gave no
answer, the run failed or is missing, or no judge has a verdict yet), so each metric's
rows sum to 100%. Intervals are 95% from a bootstrap that resamples diagnoses (questions about
the same diagnosis are not independent); differences between methods are paired per question.

- **Cost:** OpenRouter's `usage.cost` for every call (search fees included), per method and step.

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
| `MEDSIM_JUDGE_MODELS` (JSON list; the first is the main judge) | `["google/gemini-3.5-flash-lite", "qwen/qwen3.8-flash", "openai/gpt-6-luna"]` |
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
