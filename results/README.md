# Retrieval comparison: medsim retrieval vs. OpenRouter web search

Seven retrieval methods, evaluated on the same 50 questions built from
`cases/combined_272_whole_chunking.json` (2026-09-21, UTC). The benchmark is described in
[bench/README.md](../bench/README.md). Raw data, logs, and every evaluation's report are in
[retrieval_benchmark/](retrieval_benchmark/).

| Method | What it is |
|---|---|
| **Current (original)** | medsim's Europe PMC + LitSense retrieval as first evaluated |
| **Current + Europe PMC fix** | the same code, with Europe PMC's malformed replies retried (a bug found during this work) |
| **Changes 1–4** | value-first ranking in one list, animal and age filter, article-body search with excerpts around the variable, reworked fallback searches |
| **Changes 1–5** | plus natural-language LitSense queries |
| **Changes 1–6** | plus an LLM that picks the 8 documents |
| **OpenRouter search** | OpenRouter's `openrouter:web_search` tool (Exa, 8 results, medical domains) |
| **OpenRouter search, improved** | the same search with changes 1–3 applied to its results |

## Summary

- **Changes 1–4 beat OpenRouter search on the retrieval metrics at an eighth of the cost.**
  - A larger share of their documents is relevant (63% vs 35%, +28 points, 95% interval +20 to +36).
  - A larger share is useful (39% vs 22%, +18 points, +10 to +26).
  - Questions with at least one useful document: 91% vs 84%, +7 points (−2 to +18).
  - Questions with a document whose range contains the true value: 53% vs 41%, +12 points
    (−6 to +31).
  - The last two gains point the same way but are not conclusive on 44 questions.
  - Cost: $0.00093 vs $0.0075 per question. The time is similar: 96 s vs 83 s on average, almost
    all of it medsim's own LLM calls; retrieval itself takes 8 s vs 9 s.
- **Much of the original gap was a bug.** Europe PMC sometimes answers HTTP 200 with
  `{"version":"6.9"}` and no results. The retriever cached that reply and dropped Europe PMC, which
  happened on 11 of 50 questions in the first run. Fixing only that raised questions with a useful
  document from 68% to 86% (+18 points, +2 to +34).
- **Change 5 (natural-language LitSense queries) had no measurable effect** on any retrieval
  metric.
- **Change 6 (LLM selection) is not worth its price.** It finds a useful document for the most
  questions (93%) and has the highest share of useful documents (43%). But it doubles the cost
  ($0.00178 per question), almost doubles the time (196 s vs 102 s on average, because the
  selection call itself takes about 90 s), and does not improve correctness.
- **OpenRouter search improves too with changes 1–3 applied,** at the same price: relevant
  documents +13 points (+7 to +18), useful documents +11 points (+6 to +17). It still trails
  changes 1–4 on relevant documents (−15 points, −24 to −7) and costs 8× as much.
- **Better retrieval did not clearly carry through to the final answer.** No method is
  significantly closer to the true value than the others, and every method puts about 80% of
  answers in the right low / normal / high category. With 32 questions and Stage C sampling at
  temperature 0.2, the final-answer rows are noisy.
- **Recommendation:** make changes 1–4 the default (the Europe PMC fix already is), leave 5 and 6
  off, and keep OpenRouter search as an optional source. Confirm on a fresh question set first
  (see [How much to trust these numbers](#how-much-to-trust-these-numbers)).

## The comparison table

Generated from the judgments by
[scripts/make_tables.py](scripts/make_tables.py) (also saved as [tables.md](tables.md)). The
quality rows use the 44 questions on which every method retrieved; 6 are excluded because under
at least one method medsim answered without retrieving (Stage A answered from the case, or
Stage B declined). The cost rows use all 50 questions, since those calls were paid for.

### Quality (44 questions on which every method retrieved; 32 with a hidden value)

| Metric | Current (original) | Current + Europe PMC fix | Changes 1–4 | Changes 1–5 | Changes 1–6 | OpenRouter search | OpenRouter search, improved |
|---|---|---|---|---|---|---|---|
| Mean relevance grade (0–3) | 1.29 | 1.39 | 1.67 | 1.64 | 1.62 | 1.35 | 1.59 |
| Relevant documents (grade ≥ 2), share | 45% | 50% | 63% | 62% | 59% | 35% | 48% |
| Questions with ≥ 1 useful document (usefulness 2) | 68% | 86% | 91% | 89% | 93% | 84% | 86% |
| Useful documents (usefulness 2), share | 21% | 24% | 39% | 41% | 43% | 22% | 33% |
| Questions with ≥ 1 document containing the true value (correctness 2) | 22% | 38% | 53% | 50% | 47% | 41% | 47% |
| Number-giving documents pointing the right way (correctness ≥ 1), share | 60% | 68% | 72% | 70% | 70% | 63% | 65% |
| Questions where most number-giving documents point the right way | 56% | 62% | 69% | 69% | 72% | 44% | 56% |
| Final answer close to the true value | 44% | 47% | 59% | 38% | 47% | 53% | 56% |
| Final answer in the true value's category (low/normal/high) | 84% | 81% | 81% | 78% | 78% | 81% | 78% |
| Questions answered from literature | 86% | 91% | 91% | 89% | 93% | 82% | 91% |

### Cost and time (all 50 questions, including excluded ones)

| | Current (original) | Current + Europe PMC fix | Changes 1–4 | Changes 1–5 | Changes 1–6 | OpenRouter search | OpenRouter search, improved |
|---|---|---|---|---|---|---|---|
| Retrieval: search fees and search/rerank LLM, 50 questions | $0.0000 | $0.0000 | $0.0000 | $0.0000 | $0.0457 | $0.3346 | $0.3426 |
| medsim LLM (Stages A–C), 50 questions | $0.0541 | $0.0499 | $0.0465 | $0.0443 | $0.0433 | $0.0404 | $0.0343 |
| **Total, 50 questions** | **$0.0541** | **$0.0499** | **$0.0465** | **$0.0443** | **$0.0889** | **$0.3750** | **$0.3770** |
| **Total per question** | **$0.00108** | **$0.00100** | **$0.00093** | **$0.00089** | **$0.00178** | **$0.00750** | **$0.00754** |
| Projected per 1,000 questions | $1.08 | $1.00 | $0.93 | $0.89 | $1.78 | $7.50 | $7.54 |
| **Average time per question** | **87 s** | **79 s** | **96 s** | **102 s** | **196 s** | **83 s** | **83 s** |
| … of which medsim's LLM calls (Stages A–C), average | 75 s | 72 s | 89 s | 89 s | 95 s | 75 s | 72 s |
| … of which retrieval (everything else), average | 12 s | 7 s | 8 s | 12 s | 101 s | 9 s | 11 s |
| Median time per question | 61 s | 68 s | 70 s | 84 s | 181 s | 61 s | 72 s |

Times are wall-clock seconds per question, averaged over the latest run of each question. medsim's
own LLM calls (Stages A–C, DeepSeek with reasoning) take most of the time, and how long they take
depends on provider load at the time of each evaluation. So differences in the average of 10–20
s between methods mostly reflect when they ran, not the retrieval method. The retrieval row is
the rest: search requests, full-text fetching, LitSense's shared rate limit (1 request per second
across all parallel questions), and for changes 1–6 the LLM selection call (about 90 s of
reasoning). Averages include slow outliers, such as questions retried after a provider error, so
the median is shown too.

### Paired differences (95% CI; bold = interval excludes zero)

| Comparison | Relevant documents (grade ≥ 2), share | Questions with ≥ 1 useful document (usefulness 2) | Useful documents (usefulness 2), share | Questions with ≥ 1 document containing the true value (correctness 2) | Questions where most number-giving documents point the right way | Final answer close to the true value |
|---|---|---|---|---|---|---|
| Changes 1–4 − OpenRouter search | **+28 pts [+20, +36]** | +7 pts [-2, +18] | **+18 pts [+10, +26]** | +12 pts [-6, +31] | +25 pts [+0, +50] | +6 pts [-16, +28] |
| Changes 1–4 − Current + Europe PMC fix | **+13 pts [+6, +21]** | +5 pts [-7, +16] | **+15 pts [+9, +22]** | +16 pts [-3, +34] | +6 pts [-16, +28] | +12 pts [-6, +31] |
| Current + Europe PMC fix − Current (original) | +6 pts [-1, +12] | **+18 pts [+2, +34]** | +3 pts [-0, +7] | +16 pts [+0, +34] | +6 pts [-9, +22] | +3 pts [-9, +16] |
| Changes 1–5 − Changes 1–4 | -1 pts [-8, +5] | -2 pts [-11, +5] | +1 pts [-5, +7] | -3 pts [-25, +19] | +0 pts [-19, +19] | **-22 pts [-44, -3]** |
| Changes 1–6 − Changes 1–5 | -3 pts [-9, +3] | +5 pts [+0, +11] | +3 pts [-3, +8] | -3 pts [-22, +19] | +3 pts [-9, +16] | +9 pts [-9, +28] |
| OpenRouter search, improved − OpenRouter search | **+13 pts [+7, +18]** | +2 pts [-5, +11] | **+11 pts [+6, +17]** | +6 pts [-6, +19] | +12 pts [-9, +34] | +3 pts [-12, +19] |
| Changes 1–4 − OpenRouter search, improved | **+15 pts [+7, +24]** | +5 pts [-4, +14] | +7 pts [-1, +15] | +6 pts [-19, +28] | +12 pts [-9, +34] | +3 pts [-19, +25] |

Cost comes from OpenRouter's `usage.cost` for each call. It includes search fees (Exa: $0.007 per
search), the search model's tokens, the reranker's tokens (change 6), and medsim's Stages A–C.
Europe PMC and LitSense are free.

Per-set results, subgroup tables, and results per source are in the latest report,
[reports/final_all_methods.md](retrieval_benchmark/reports/final_all_methods.md).

## Evaluation log

Every evaluation is recorded in `retrieval_benchmark/`:
- a report snapshot in `reports/`
- the full log of every command in `logs/`
- each command's parameters, summary, and key usage in `manifest.json`
- every run and judgment in the JSONL files

A run that fails on a transient provider error is rerun for the failed questions only, and the
retry is logged too.

| # | When (UTC, 2026-09-21) | Evaluation | Configurations run | Run time | Cost: runs / judging | Report snapshot |
|---|---|---|---|---|---|---|
| 0 | 11:58–12:54 | First comparison (extraction, questions, runs, judge, judge validation) | `current`, `openrouter_search` | about 25 min for both (6 workers) | $0.4291 / $0.5317, plus $0.1473 to build the questions and $0.1195 validation | [eval0_current_vs_openrouter.md](retrieval_benchmark/reports/eval0_current_vs_openrouter.md) |
| 1 | 14:51–15:47 | Changes 1–4, and the Europe PMC fix alone as a reference | `current_fixed`, `improved_1to4` | 29.2 min first pass for both (6 workers, one configuration after the other), then retries for 6 transient failures | $0.0964 / $0.4535 | [eval1_changes_1to4.md](retrieval_benchmark/reports/eval1_changes_1to4.md) |
| 2 | 15:47–15:59 | Changes 1–5 | `improved_1to5` | 8.9 min (12 workers, shared pool), then 1.7 min retrying 3 | $0.0443 / $0.1988 | [eval2_changes_1to5.md](retrieval_benchmark/reports/eval2_changes_1to5.md) |
| 3 | 15:59–16:22 | Changes 1–6 | `improved_1to6` | 16.4 min (the reranker adds an LLM call per question), then 5.9 min retrying 2 | $0.0889 / $0.1515 | [eval3_changes_1to6.md](retrieval_benchmark/reports/eval3_changes_1to6.md) |
| 4 | 16:23–16:33 | Improved OpenRouter search | `openrouter_search_improved` | 7.7 min, no failures | $0.3770 / $0.2583 | [eval4_openrouter_improved.md](retrieval_benchmark/reports/eval4_openrouter_improved.md) |
| – | 16:33–16:51 | Judge validation extended to the new methods' documents | all | 17 min (the second judge reasons slowly) | $0.2032 | [final_all_methods.md](retrieval_benchmark/reports/final_all_methods.md) |

Each evaluation's report compares the methods that existed at that point, on the questions all of
them retrieved for. Adding methods removes questions from that common set, so earlier snapshots
differ slightly from the final table: 47 questions in evaluation 0, 45 in evaluations 1–2, and 44
in evaluations 3–4.

## What each change does and what it did

The changes came from an analysis of the first run, where the current method lost for four
reasons:
- **It kept documents without a value.** 44% of kept documents had no number near the variable,
  while its own candidates often had better ones.
- **About 10% of kept documents were animal studies.**
- **Its fallback searches were rarely useful**, 0–13% of the time.
- **It read only abstracts, cut at 1,500 characters.**

All changes sit behind settings that are off by default (see the main [README](../README.md)).

| Change | What it does | Code | Effect measured |
|---|---|---|---|
| Europe PMC fix | Retries HTTP 200 replies without results and never caches them. It also ignores such replies in an old cache. | `medsim/retrieval/europe_pmc.py` | Europe PMC failures: 11 of 50 questions → 0. Questions with a useful document 68% → 86% (+18 pts, +2 to +34). |
| 1. Rank for values | A number near the variable is worth +6 (was +2) and the exact disease +3 (was +2). One list ranks all sources together instead of 4 documents from each. Europe PMC returns 50 candidates instead of 25. | `query_formulation.py` (`RelevanceScorer`), `aggregator.py` (`_merge_global`) | Together with 2–4: documents stating a number 35% → 51% of kept documents; useful documents 24% → 39% (+15 pts, +9 to +22). |
| 2. Population filter | Drops animal studies, using Europe PMC MeSH tags ("Animals" without "Humans"), LitSense species tags, and animal words in titles. Ranks other age groups lower (−4), using the patient's age from the case. | `population.py`, `rules.age_group` | 135 animal documents dropped over 50 questions. Wrong-population documents 20% → 10%. |
| 3. Article bodies and excerpts | Adds a Europe PMC search of case, results, and table sections (`CASE:`/`RESULTS:`/`TABLE:` for the variable, with the disease in the title or abstract). For open-access hits it reads the full text (Europe PMC `fullTextXML`) and keeps the sentences and table rows about the variable. Other long texts get a window around the variable instead of their first 1,500 characters. | `query_formulation.py` (`europe_pmc_ladder`, `excerpt`), `fulltext.py`, `aggregator.py` (`_excerpt`) | 7.3 documents per question from full text and 17 windows per question. Documents not mentioning the variable 20% → 14%. |
| 4. Fallback searches | Removes the searches that never gave a useful document (LitSense synonym and reference-range, Europe PMC any-field and reference-range). Broadens only while fewer than 3 documents state a value (body-search hits count). Documents found only through a related disease rank lower (−2). | `query_formulation.py`, `aggregator.py` (`_search_source`) | Documents about an unrelated disease 21% → 15%. |
| 5. Natural LitSense query | Sends "serum albumin in elderly patients with biloma" instead of "serum albumin biloma". | `query_formulation.py` (`litsense_ladder`) | No measurable effect (e.g. useful documents +1 pt, −5 to +7). |
| 6. LLM selection | DeepSeek Flash reads the best 20 candidates and picks those stating a value for this patient; the rest of the 8 slots are filled in ranked order. If the call fails, the ranked order stands. | `rerank.py`, `aggregator.py` (`_llm_select`) | It picked 3.6 documents per question on average. Questions with a useful document +5 pts (0 to +11); other metrics unchanged. Cost 2× and average time 1.9× that of changes 1–5 (retrieval 12 s → 101 s). |
| Improved OpenRouter search | Asks for 10 results (the same $0.007 Exa fee) with 3,000-character excerpts. Reads the Europe PMC full text of PMC hits and keeps the sentences about the variable, then applies changes 1 and 2. | `bench/run.py` (`openrouter_search_improved`), `aggregator.py` | 3.6 documents per question from full text. Documents not mentioning the variable 53% → 39%; relevant +13 pts, useful +11 pts. |

What the judge saw in each method's documents (44 questions):

| Share of kept documents | Current | + Europe PMC fix | Changes 1–4 | Changes 1–5 | Changes 1–6 | OpenRouter | OpenRouter, improved |
|---|---|---|---|---|---|---|---|
| Do not mention the variable | 26% | 20% | 14% | 13% | 15% | 53% | 39% |
| About the patient's exact disease | 46% | 42% | 49% | 45% | 48% | 68% | 67% |
| About an unrelated disease | 20% | 21% | 15% | 19% | 21% | 5% | 7% |
| Wrong population (animals, other age group) | 20% | 20% | 10% | 11% | 10% | 4% | 3% |
| Give a number for the variable | 31% | 35% | 51% | 52% | 58% | 28% | 39% |

The two families still fail differently:
- **medsim's methods find the variable** but still often land on a related disease.
- **Web search finds the disease** but often misses the variable.

This is why the improved medsim method wins on relevant documents, and why reading full texts
helped both.

## Speed

After evaluation 1, the benchmark was changed to run faster:
- **One thread pool for every (method, question) pair**, so a slow question in one method does not
  hold back another. The default is now 12 parallel questions (was 4, with 6 used in practice).
  LitSense's 1 request per second is shared by all threads, so it isn't exceeded.
- **Empty model replies are retried inside the OpenRouter client.** They were transient failures
  on about 5% of DeepSeek calls, and each needed a whole second pass.
- **The judge's pass 1 and answer checks run together** in one pool of 16.
- **The search cache writes each entry through its own temporary file.** With the old shared
  temporary file name, two threads caching the same query could crash a search.

Result: a method now takes 7.7–8.9 minutes for 50 questions, instead of about 14.6 minutes. Changes
1–6 take 16.4 minutes because the reranker adds one slow LLM call per question. Judging 810
documents and answers took 1.4 minutes.

## How the benchmark works

- **Questions.** An LLM listed the measured values in 70 randomly chosen cases.
  - **35 questions hide one of those values** (set A). The value is removed from the case, code
    checks it is gone, and medsim's Stage A must fail to answer from the redacted case.
  - **15 questions ask for a common vital sign or lab that the case never mentions** (set B).
  - The case's own published article is removed from every method's results; it came back on
    7–13 of 50 questions, depending on the method.
- **Grading.** Every unique retrieved document (2,029 in total) is graded once by
  `google/gemini-3.5-flash-lite`, which does not know which method found it.
  - **Relevant (0–3):** is it about the variable, the disease, and a comparable population?
  - **Useful (0–2):** does it give a number for the variable in that or a related disease? The
    evidence must be quoted verbatim.
  - **Correct (0–2), set A only:** does its number fit the hidden value? 2 means inside the
    range, 1 means the same low / normal / high category.
  - **Final answer, set A only:** is medsim's value close to the hidden value, or at least in the
    same category?
- **Statistics.** Means with 95% intervals from a bootstrap that resamples diagnoses. Differences
  between methods are paired on the same questions.

## How much to trust these numbers

- **Judge checks:**
  - **Synthetic control documents:** 37 of 40 graded as expected. The 3 misses were relevance 2
    instead of 3 on a generic "48 patients with X" study.
  - **Flipped true value:** 14 of 18 "within" verdicts changed when the true value was moved far
    away. The ones that stayed were documents with very wide ranges that still contain the moved
    value.
  - **Second judge** (`qwen/qwen3.8-flash`, 201 documents): κ = 0.74 for relevance and 0.70 for
    usefulness, which is good agreement.
  - **Correctness verdicts** (69 documents): 43 identical, κ = 0.48, which is moderate. Treat the
    correctness rows as indicative.
- **Designed and tested on the same 50 questions.** Changes 1–4 target failures seen on these
  questions, so their gains are probably optimistic. A fresh set of 50 questions (a new seed)
  would cost about $1.10 for these two methods and fits in the remaining budget.
- **Many comparisons.** The paired table has 42 tests, so one or two "significant" results can be
  chance. Changes 1–5 vs 1–4 on "final answer close" (−22 points) is probably one: their
  retrieval metrics are the same, and Stage C samples at temperature 0.2.
- **Small sample:** 44 questions, 32 with a hidden value.
- **Token budgets on retries.** Retries of questions where DeepSeek used its whole reasoning
  budget in Stage A or B ran with a 16,000-token budget. A complete reply is the same at any
  budget, so this recovers questions without changing the retrieval comparison.
- **Speed changes mid-benchmark.** Evaluations 2–4 ran with the speed changes and the empty-reply
  retry. That affects run time and how many questions needed a retry, not which documents were
  retrieved.

## Cost accounting

| What | USD (per-call `usage.cost`) |
|---|---|
| Building the questions (extraction, redaction, Stage A checks) | 0.1473 |
| All method runs (7 methods × 50 questions, search fees included) | 1.0357 |
| Judging (2,029 documents, 682 correctness checks, 223 answer checks) | 1.5937 |
| Judge validation (controls, flipped truth, second judge) | 0.3227 |
| **Benchmark total** | **3.0995** |

The OpenRouter key's usage went from $0.0197 before this work to $3.1675 after it. The $3.148
difference is the benchmark total plus about $0.05 of setup probes and smoke tests. That leaves
$1.83 of the $5 limit.

## Reproduce

Every step resumes from the saved data, and searches are cached in `.medsim_cache/`.

```bash
python -m bench --out results/retrieval_benchmark run --configs current,current_fixed,improved_1to4,improved_1to5,improved_1to6,openrouter_search,openrouter_search_improved
```

```bash
python -m bench --out results/retrieval_benchmark --workers 16 judge
```

```bash
python -m bench --out results/retrieval_benchmark report --baseline current_fixed --snapshot final_all_methods
```

```bash
python results/scripts/make_tables.py
```

## Files

| File | Contents |
|---|---|
| `tables.md`, `scripts/make_tables.py` | The comparison tables above, and the script that builds them |
| `retrieval_benchmark/reports/*.md` | Report snapshot after each evaluation |
| `retrieval_benchmark/report.md`, `report.json` | Latest report; every number and per-question score |
| `retrieval_benchmark/logs/*.log` | Full log of every benchmark command |
| `retrieval_benchmark/manifest.json` | Parameters, summaries, and key usage of every command |
| `retrieval_benchmark/items.jsonl`, `rejected_items.jsonl`, `facts.jsonl` | The 50 questions, rejected candidates, extracted values |
| `retrieval_benchmark/runs/<method>.jsonl` | medsim's output per question: documents, queries, costs, LLM calls, filter/excerpt/rerank statistics |
| `retrieval_benchmark/judge/*.jsonl` | Judge verdicts with rationales and verbatim evidence |
| `retrieval_benchmark/validate/` | Controls, flipped-truth checks, second-judge verdicts, human-label sheet |
