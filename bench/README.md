# Retrieval benchmark

Measures whether the documents medsim retrieves are **relevant**, **useful**, and **correct**,
with an LLM judge, and compares retrieval methods on the same questions, including their cost.

## Idea

Correctness needs the patient's real value. A case report already states many values, so the
benchmark hides one, lets medsim retrieve literature for it, and grades each retrieved document
against the hidden value.

| | Set A: hidden value | Set B: value never stated |
|---|---|---|
| Question | A value the case reports, removed from the case text | A common vital or lab the case never mentions |
| Metrics | relevance, usefulness, correctness | relevance, usefulness |

## Steps

Each step appends JSONL to one workspace directory and resumes where it stopped. Rerunning a
step retries failed records only.

```bash
python -m bench --out results/retrieval_benchmark --workers 8 extract --limit 70
```

```bash
python -m bench --out results/retrieval_benchmark --workers 8 redact --set-a 35 --set-b 15
```

```bash
python -m bench --out results/retrieval_benchmark --workers 6 run --configs current,openrouter_search
```

```bash
python -m bench --out results/retrieval_benchmark --workers 8 judge
```

```bash
python -m bench --out results/retrieval_benchmark --workers 8 validate --controls 10 --flips 10
```

```bash
python -m bench --out results/retrieval_benchmark report
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
4. **judge**: grades each unique retrieved document once (pooled across configurations,
   one document per call, blind to the configuration).
5. **validate**: checks the judge (see below).
6. **report**: `report.md` and `report.json` in the workspace; `--snapshot NAME` also keeps a
   copy as `reports/NAME.md`, so each evaluation's report is preserved.

Every command also writes its full log to `logs/<UTC time>_<step>.log` in the workspace, and
`manifest.json` records its parameters, summary, and the key's usage before and after.

### Configurations (`bench/run.py:CONFIGS`)

| Name | Retrieval |
|---|---|
| `current` | medsim's default Europe PMC + LitSense retrieval |
| `current_fixed` | the same, with the Europe PMC retry for replies without results |
| `improved_1to4` | retrieval changes 1–4 (value-first ranking in one list, 50 Europe PMC candidates, animal and age filter, article-body search with excerpts, value-based broadening) |
| `improved_1to5` | plus natural-language LitSense queries |
| `improved_1to6` | plus LLM selection of the final 8 documents |
| `openrouter_search` | OpenRouter's web search server tool (Exa) |
| `sentences`, `no_rerank`, `reference_only` | ablations of the default method |

## Judge rubric

**Pass 1** never sees the true value. The judge reports facets; code turns them into grades.

| Grade | Relevance (0–3) | Usefulness (0–2) |
|---|---|---|
| 3 | exact variable, exact condition, matching population | |
| 2 | exact variable, related condition or partly matching population | a number for the exact variable in the exact or a related condition |
| 1 | only the variable or only the condition | a number from a population without the condition, a related variable, or only a direction in the right condition |
| 0 | neither, or animals / in vitro / incompatible population | nothing usable, or a quote that is not in the document |

The judge must quote its evidence verbatim; if the quote is not found in the document,
usefulness is 0 (`bench/text.py:quote_found`).

**Pass 2** (set A, documents with usefulness ≥ 1) sees the true value.

| Verdict | Correctness |
|---|---|
| within: the true value is inside the document's range (range, mean ± 2 SD, or IQR) | 2 |
| direction: outside the range but in the same low / normal / high category | 1 |
| contradicts: the document points to another category | 0 |
| not comparable | excluded |

**Answer check**: the same comparison for Stage C's final answer (close / same category /
different category).

## Metrics

Per question, then averaged with 95% intervals from a bootstrap that resamples diagnoses (questions
about the same diagnosis are not independent). Differences between methods are paired per
question.

- **Relevance:** mean grade; share of documents graded ≥ 2.
- **Usefulness:** share of questions with at least one useful document; share of useful documents.
- **Correctness (set A):** share of questions with at least one document containing the true
  value; share of number-giving documents pointing the right way; share of questions where most
  of them do.
- **End to end (set A):** final answer close to, or in the same category as, the true value.
- **Cost:** OpenRouter's `usage.cost` for every call (search fees included), per method and step.

## Judge validation

- **Controls:** synthetic documents with known grades: a matching range, a far-off range, an
  off-topic study, and the matching study in dogs.
- **Flipped truth:** "within" verdicts are re-judged with the true value moved far away; they
  should change.
- **Second judge:** a sample is re-graded by a model from another family; the report gives
  Cohen's κ.
- **Human labels:** `validate --export-human N` writes `validate/human_labels.csv`; fill in the
  `human_*` columns and rerun `report`.

## Models and settings

Environment variables with the `MEDSIM_` prefix, as for medsim:

| Variable | Default |
|---|---|
| `MEDSIM_JUDGE_MODEL` | `google/gemini-3.5-flash-lite` |
| `MEDSIM_SECOND_JUDGE_MODEL` | `qwen/qwen3.8-flash` |
| `MEDSIM_EXTRACTOR_MODEL`, `MEDSIM_REDACTOR_MODEL` | the judge model |
| `MEDSIM_JUDGE_MAX_TOKENS`, `MEDSIM_EXTRACTOR_MAX_TOKENS`, `MEDSIM_REDACTOR_MAX_TOKENS` | 4000, 8000, 8000 |

The judges come from model families other than the pipeline's (DeepSeek), so no judge grades
its own family's queries.

## Limits

- Case reports are published because something was unusual, so correctness cannot reach 100%.
  Compare methods with each other, not with a perfect score.
- Set A leans toward values notable enough to report; set B covers the everyday case.
- The judge is an LLM. Read its validation section before trusting absolute numbers.
