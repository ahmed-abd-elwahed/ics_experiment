# Retrieval benchmark report

- Workspace: `results/retrieval_benchmark`
- Judge: `google/gemini-3.5-flash-lite`
- medsim models: `deepseek/deepseek-v4-flash-0731`
- `current`: Europe PMC + LitSense passages, relaxation ladders, lexical rerank (medsim default)
- `openrouter_search`: OpenRouter web search server tool (Exa, 8 results, medical domains), lexical rerank

## Question sets

- Cases extracted: 70; measured values found: 421; eligible as hidden values: 222.
- Set A (hidden value): 35 questions accepted; rejected 2 (stage_a_answers_from_case: 2).
- Set B (value never stated): 15 questions accepted; rejected 1 (stage_a_answers_from_case: 1).
- Compared: 47 questions on which every method ran retrieval; excluded 3: `A:PMC3625585_01:body_mass_index` (current: case_study, openrouter_search: case_study); `A:PMC5477234_01:weight` (current: literature, openrouter_search: case_study); `B:PMC4333364_01:respiratory_rate` (current: literature, openrouter_search: query_builder_declined).

## All questions (sets A and B)

| Metric | current | openrouter_search | openrouter_search − current |
|---|---|---|---|
| Documents returned per question | 8.00 [8.00, 8.00] | 7.66 [7.49, 7.81] | -0.34 [-0.51, -0.19] |
| Mean relevance grade (0–3) | 1.29 [1.12, 1.45] | 1.36 [1.22, 1.50] | +0.07 [-0.06, +0.20] |
| Relevant documents (grade ≥ 2), share | 44% [36, 52] | 35% [29, 42] | -8 pts [-15, -2] |
| Questions with ≥ 1 useful document (usefulness 2) | 66% [52, 80] | 83% [72, 93] | +17 pts [+4, +31] |
| Useful documents (usefulness 2), share | 20% [14, 26] | 23% [18, 27] | +3 pts [-3, +8] |
| Questions with ≥ 1 document containing the true value (correctness 2) | 21% [9, 36] | 39% [24, 58] | +18 pts [-3, +39] |
| Number-giving documents pointing the right way (correctness ≥ 1), share | 61% [44, 77] | 63% [50, 77] | +0 pts [-19, +21] |
| Questions where most number-giving documents point the right way | 58% [39, 73] | 45% [30, 64] | -12 pts [-33, +9] |
| Questions answered from literature | 87% [77, 96] | 81% [69, 91] | -6 pts [-21, +7] |
| Final answer close to the true value | 42% [27, 58] | 52% [36, 70] | +9 pts [+0, +18] |
| Final answer in the true value's category (low/normal/high) | 85% [73, 97] | 82% [67, 94] | -3 pts [-12, +6] |
| Retrieval cost per question (search fees, search/rerank LLM; USD) | $0.00000 | $0.00712 | +0.00712 [+0.00712, +0.00712] |
| medsim LLM cost per question (Stages A–C, USD) | $0.00108 | $0.00085 | -0.00023 [-0.00042, -0.00004] |
| Total cost per question (USD) | $0.00108 | $0.00797 | +0.00689 [+0.00670, +0.00708] |
| Wall time per question (s) | 85.1 [68.3, 105.0] | 86.3 [72.5, 102.3] | +1.23 [-16.26, +18.44] |

## Set A only (hidden value; correctness defined)

| Metric | current | openrouter_search | openrouter_search − current |
|---|---|---|---|
| Documents returned per question | 8.00 [8.00, 8.00] | 7.58 [7.36, 7.76] | -0.42 [-0.64, -0.24] |
| Mean relevance grade (0–3) | 1.39 [1.22, 1.56] | 1.43 [1.25, 1.60] | +0.03 [-0.13, +0.20] |
| Relevant documents (grade ≥ 2), share | 50% [41, 59] | 40% [31, 47] | -10 pts [-18, -3] |
| Questions with ≥ 1 useful document (usefulness 2) | 73% [58, 88] | 91% [82, 100] | +18 pts [+3, +33] |
| Useful documents (usefulness 2), share | 22% [16, 29] | 25% [19, 31] | +3 pts [-4, +11] |
| Questions with ≥ 1 document containing the true value (correctness 2) | 21% [9, 36] | 39% [24, 58] | +18 pts [-3, +39] |
| Number-giving documents pointing the right way (correctness ≥ 1), share | 61% [44, 77] | 63% [50, 77] | +0 pts [-19, +21] |
| Questions where most number-giving documents point the right way | 58% [39, 73] | 45% [30, 64] | -12 pts [-33, +9] |
| Questions answered from literature | 97% [91, 100] | 94% [85, 100] | -3 pts [-15, +6] |
| Final answer close to the true value | 42% [27, 58] | 52% [36, 70] | +9 pts [+0, +18] |
| Final answer in the true value's category (low/normal/high) | 85% [73, 97] | 82% [67, 94] | -3 pts [-12, +6] |

## Set B only (value never stated)

| Metric | current | openrouter_search | openrouter_search − current |
|---|---|---|---|
| Documents returned per question | 8.00 [8.00, 8.00] | 7.86 [7.64, 8.00] | -0.14 [-0.36, +0.00] |
| Mean relevance grade (0–3) | 1.04 [0.71, 1.38] | 1.20 [0.97, 1.46] | +0.16 [-0.05, +0.37] |
| Relevant documents (grade ≥ 2), share | 29% [14, 46] | 26% [13, 40] | -4 pts [-15, +7] |
| Questions with ≥ 1 useful document (usefulness 2) | 50% [21, 71] | 64% [36, 86] | +14 pts [-14, +43] |
| Useful documents (usefulness 2), share | 14% [4, 26] | 16% [8, 24] | +2 pts [-9, +11] |
| Questions answered from literature | 64% [36, 86] | 50% [29, 79] | -14 pts [-50, +29] |

## Cost

All runs, including the excluded questions (their calls were paid for).

| Method | Questions | Retrieval (search fees + search model) | medsim LLM (Stages A–C) | Total | Total per question | Median wall time |
|---|---|---|---|---|---|---|
| current | 50 | $0.0000 | $0.0541 | $0.0541 | $0.00108 | 60.6 s |
| openrouter_search | 50 | $0.3346 | $0.0404 | $0.3750 | $0.00750 | 61.4 s |

## By subgroup (set A)

### Variable category

| Group | n | Questions with ≥ 1 useful document (usefulness 2) — current | Questions with ≥ 1 useful document (usefulness 2) — openrouter_search | Questions with ≥ 1 document containing the true value (correctness 2) — current | Questions with ≥ 1 document containing the true value (correctness 2) — openrouter_search |
|---|---|---|---|---|---|
| anthropometric | 5 | 80% | 80% | 20% | 40% |
| laboratory | 14 | 79% | 93% | 21% | 50% |
| vital_sign | 14 | 64% | 93% | 21% | 29% |

### True value (judge's category)

| Group | n | Questions with ≥ 1 useful document (usefulness 2) — current | Questions with ≥ 1 useful document (usefulness 2) — openrouter_search | Questions with ≥ 1 document containing the true value (correctness 2) — current | Questions with ≥ 1 document containing the true value (correctness 2) — openrouter_search |
|---|---|---|---|---|---|
| high | 16 | 69% | 93% | 19% | 29% |
| low | 9 | 78% | 100% | 33% | 33% |
| normal | 8 | 75% | 100% | 12% | 75% |
| unknown | 2 | – | 0% | – | 0% |

### Variable typical of the diagnosis

| Group | n | Questions with ≥ 1 useful document (usefulness 2) — current | Questions with ≥ 1 useful document (usefulness 2) — openrouter_search | Questions with ≥ 1 document containing the true value (correctness 2) — current | Questions with ≥ 1 document containing the true value (correctness 2) — openrouter_search |
|---|---|---|---|---|---|
| no | 20 | 60% | 85% | 10% | 35% |
| yes | 13 | 92% | 100% | 38% | 46% |

### Documents by source

| Source | Documents judged | Mean relevance | Relevant (≥ 2) | Useful (= 2) |
|---|---|---|---|---|
| europe_pmc | 148 | 1.21 | 44% | 21% |
| litsense | 228 | 1.34 | 44% | 19% |
| openrouter_search | 360 | 1.36 | 35% | 22% |

## Diagnostics

- **current:** answer paths {'synthesizer_unanswerable': 6, 'literature': 41}; source article removed for 8 question(s); 0 document(s) without a judgment.
- **openrouter_search:** answer paths {'literature': 38, 'synthesizer_unanswerable': 9}; source article removed for 9 question(s); 0 document(s) without a judgment.
- **Quote check:** 19 of 2029 pass-1 judgments quoted text that is not in the document (usefulness forced to 0).
- **Pass 2:** 144 of 682 verdicts were "not comparable" (excluded from correctness).
- **Judge errors (all attempts):** 0 pass-1 call(s) failed.

## Judge validation

| Control document | Expected | Passed |
|---|---|---|
| far_range | usefulness 2, correctness 0 or 1 | 10/10 |
| off_topic | relevance 0, usefulness 0 | 10/10 |
| positive | relevance 3, usefulness 2, correctness 2 | 7/10 |
| veterinary | relevance 0, usefulness 0 | 10/10 |

- **Flipped true value:** after moving the true value far away, 6 of 10 "within" verdicts changed. An unchanged verdict is not always an error: when a document reports a wide range, the moved value can still be inside it (see validate/flips.jsonl).
- **Second judge (qwen/qwen3.8-flash), 76 documents:** quadratic-weighted κ = 0.79 for relevance, 0.79 for usefulness.
- **Second judge, correctness verdicts (20 documents):** 10/20 identical, Cohen's κ = 0.33.

## Benchmark spend

| Step | Cost (USD, OpenRouter usage.cost) |
|---|---|
| extract (case facts) | $0.0940 |
| redact + Stage A checks (accepted) | $0.0506 |
| redact + Stage A checks (rejected) | $0.0027 |
| run (all methods; search fees included) | $0.4291 |
| judge pass 1 | $1.1669 |
| judge pass 2 | $0.3451 |
| judge answer check | $0.0817 |
| validation: controls | $0.0303 |
| validation: flipped truth | $0.0055 |
| validation: second judge, pass 1 | $0.0698 |
| validation: second judge, pass 2 | $0.0139 |
| **total** | **$2.2897** |

Cross-check: the OpenRouter key's usage counter, read right after each of the 26 benchmark commands, rose by $2.5927. The counter lags behind requests, so this undercounts; per-call usage.cost above is the accounting source.

