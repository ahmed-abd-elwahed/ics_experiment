# Retrieval benchmark report

- Workspace: `results/retrieval_benchmark`
- Judge: `google/gemini-3.5-flash-lite`
- medsim models: `deepseek/deepseek-v4-flash-0731`
- `current`: Europe PMC + LitSense passages, relaxation ladders, lexical rerank (medsim default)
- `current_fixed`: current method, unchanged except that Europe PMC replies without results are retried (they made Europe PMC drop out on 11 of 50 questions in the `current` run)
- `improved_1to4`: changes 1-4: value-first ranking in one list across sources, 50 Europe PMC candidates, animal/age filter, article-body search with excerpts, value-based broadening without the unhelpful rungs
- `improved_1to5`: changes 1-5: improved_1to4 plus natural-language LitSense queries
- `openrouter_search`: OpenRouter web search server tool (Exa, 8 results, medical domains), lexical rerank

## Question sets

- Cases extracted: 70; measured values found: 421; eligible as hidden values: 222.
- Set A (hidden value): 35 questions accepted; rejected 2 (stage_a_answers_from_case: 2).
- Set B (value never stated): 15 questions accepted; rejected 1 (stage_a_answers_from_case: 1).
- Compared: 45 questions on which every method ran retrieval; excluded 5: `A:PMC3625585_01:body_mass_index` (current: case_study, current_fixed: case_study, improved_1to4: case_study, improved_1to5: literature, openrouter_search: case_study); `A:PMC5477234_01:weight` (current: literature, current_fixed: case_study, improved_1to4: synthesizer_unanswerable, improved_1to5: synthesizer_unanswerable, openrouter_search: case_study); `B:PMC4208417_01:white_cell_count` (current: literature, current_fixed: query_builder_declined, improved_1to4: query_builder_declined, improved_1to5: query_builder_declined, openrouter_search: synthesizer_unanswerable); `B:PMC4333364_01:respiratory_rate` (current: literature, current_fixed: literature, improved_1to4: literature, improved_1to5: synthesizer_unanswerable, openrouter_search: query_builder_declined); `B:PMC9095982_01:c_reactive_protein` (current: literature, current_fixed: literature, improved_1to4: off_topic, improved_1to5: literature, openrouter_search: literature).

## All questions (sets A and B)

| Metric | current | current_fixed | improved_1to4 | improved_1to5 | openrouter_search | current − current_fixed | improved_1to4 − current_fixed | improved_1to5 − current_fixed | openrouter_search − current_fixed |
|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 8.00 [8.00, 8.00] | 8.00 [8.00, 8.00] | 8.00 [8.00, 8.00] | 8.00 [8.00, 8.00] | 7.64 [7.47, 7.80] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | -0.36 [-0.53, -0.20] |
| Mean relevance grade (0–3) | 1.30 [1.12, 1.47] | 1.40 [1.24, 1.54] | 1.69 [1.52, 1.85] | 1.66 [1.47, 1.84] | 1.37 [1.22, 1.52] | -0.10 [-0.20, +0.01] | +0.29 [+0.13, +0.45] | +0.26 [+0.10, +0.42] | -0.03 [-0.16, +0.12] |
| Relevant documents (grade ≥ 2), share | 45% [36, 54] | 51% [44, 57] | 64% [56, 72] | 63% [54, 72] | 36% [30, 43] | -6 pts [-11, +1] | +14 pts [+7, +21] | +12 pts [+4, +21] | -14 pts [-21, -8] |
| Questions with ≥ 1 useful document (usefulness 2) | 67% [52, 81] | 84% [73, 93] | 91% [82, 98] | 89% [80, 98] | 84% [74, 94] | -18 pts [-33, -4] | +7 pts [-4, +18] | +4 pts [-9, +16] | +0 pts [-9, +9] |
| Useful documents (usefulness 2), share | 20% [15, 26] | 24% [18, 30] | 40% [32, 48] | 42% [33, 49] | 23% [18, 27] | -3 pts [-7, +0] | +17 pts [+10, +24] | +18 pts [+10, +26] | -1 pts [-8, +6] |
| Questions with ≥ 1 document containing the true value (correctness 2) | 21% [9, 36] | 36% [21, 52] | 52% [33, 70] | 52% [33, 70] | 39% [24, 58] | -15 pts [-33, +0] | +15 pts [+0, +33] | +15 pts [-6, +36] | +3 pts [-15, +21] |
| Number-giving documents pointing the right way (correctness ≥ 1), share | 61% [44, 77] | 69% [55, 82] | 72% [60, 83] | 70% [59, 81] | 63% [50, 77] | -6 pts [-18, +5] | +4 pts [-10, +19] | +3 pts [-9, +14] | -10 pts [-26, +5] |
| Questions where most number-giving documents point the right way | 58% [39, 73] | 64% [45, 79] | 70% [55, 85] | 70% [52, 85] | 45% [30, 64] | -6 pts [-21, +9] | +6 pts [-15, +27] | +6 pts [-6, +21] | -18 pts [-36, +0] |
| Questions answered from literature | 87% [76, 96] | 91% [82, 98] | 91% [80, 100] | 89% [79, 98] | 82% [70, 93] | -4 pts [-17, +7] | +0 pts [-9, +9] | -2 pts [-12, +7] | -9 pts [-23, +4] |
| Final answer close to the true value | 42% [27, 58] | 45% [30, 64] | 58% [39, 73] | 36% [21, 52] | 52% [36, 70] | -3 pts [-15, +9] | +12 pts [-6, +30] | -9 pts [-30, +9] | +6 pts [-9, +21] |
| Final answer in the true value's category (low/normal/high) | 85% [73, 97] | 82% [70, 94] | 82% [67, 94] | 79% [64, 91] | 82% [67, 94] | +3 pts [-6, +12] | +0 pts [-12, +12] | -3 pts [-12, +6] | +0 pts [-12, +12] |
| Retrieval cost per question (search fees, search/rerank LLM; USD) | $0.00000 | $0.00000 | $0.00000 | $0.00000 | $0.00712 | +0.00000 [+0.00000, +0.00000] | +0.00000 [+0.00000, +0.00000] | +0.00000 [+0.00000, +0.00000] | +0.00712 [+0.00712, +0.00712] |
| medsim LLM cost per question (Stages A–C, USD) | $0.00109 | $0.00106 | $0.00079 | $0.00088 | $0.00084 | +0.00003 [-0.00020, +0.00028] | -0.00027 [-0.00046, -0.00008] | -0.00018 [-0.00037, -0.00001] | -0.00022 [-0.00043, +0.00001] |
| Total cost per question (USD) | $0.00109 | $0.00106 | $0.00079 | $0.00088 | $0.00796 | +0.00003 [-0.00020, +0.00028] | -0.00027 [-0.00046, -0.00008] | -0.00018 [-0.00037, -0.00001] | +0.00690 [+0.00668, +0.00713] |
| Wall time per question (s) | 87.0 [70.4, 106.8] | 84.4 [70.5, 98.2] | 87.4 [74.4, 100.6] | 101.7 [84.4, 121.8] | 87.3 [72.5, 104.1] | +2.60 [-18.98, +26.85] | +3.09 [-10.13, +17.53] | +17.36 [+1.84, +34.06] | +2.95 [-14.53, +22.54] |

## Set A only (hidden value; correctness defined)

| Metric | current | current_fixed | improved_1to4 | improved_1to5 | openrouter_search | current − current_fixed | improved_1to4 − current_fixed | improved_1to5 − current_fixed | openrouter_search − current_fixed |
|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 8.00 [8.00, 8.00] | 8.00 [8.00, 8.00] | 8.00 [8.00, 8.00] | 8.00 [8.00, 8.00] | 7.58 [7.36, 7.76] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | -0.42 [-0.64, -0.24] |
| Mean relevance grade (0–3) | 1.39 [1.22, 1.56] | 1.45 [1.27, 1.63] | 1.77 [1.59, 1.94] | 1.73 [1.52, 1.95] | 1.43 [1.25, 1.60] | -0.06 [-0.17, +0.06] | +0.31 [+0.14, +0.48] | +0.28 [+0.08, +0.47] | -0.03 [-0.21, +0.16] |
| Relevant documents (grade ≥ 2), share | 50% [41, 59] | 54% [46, 61] | 66% [58, 75] | 66% [55, 75] | 40% [31, 47] | -4 pts [-11, +3] | +12 pts [+5, +21] | +12 pts [+2, +21] | -14 pts [-23, -5] |
| Questions with ≥ 1 useful document (usefulness 2) | 73% [58, 88] | 85% [73, 97] | 94% [85, 100] | 91% [79, 100] | 91% [82, 100] | -12 pts [-27, +3] | +9 pts [-3, +21] | +6 pts [-6, +18] | +6 pts [-6, +18] |
| Useful documents (usefulness 2), share | 22% [16, 29] | 24% [17, 31] | 41% [31, 49] | 41% [32, 50] | 25% [19, 31] | -2 pts [-7, +2] | +16 pts [+8, +25] | +16 pts [+8, +26] | +1 pts [-8, +10] |
| Questions with ≥ 1 document containing the true value (correctness 2) | 21% [9, 36] | 36% [21, 52] | 52% [33, 70] | 52% [33, 70] | 39% [24, 58] | -15 pts [-33, +0] | +15 pts [+0, +33] | +15 pts [-6, +36] | +3 pts [-15, +21] |
| Number-giving documents pointing the right way (correctness ≥ 1), share | 61% [44, 77] | 69% [55, 82] | 72% [60, 83] | 70% [59, 81] | 63% [50, 77] | -6 pts [-18, +5] | +4 pts [-10, +19] | +3 pts [-9, +14] | -10 pts [-26, +5] |
| Questions where most number-giving documents point the right way | 58% [39, 73] | 64% [45, 79] | 70% [55, 85] | 70% [52, 85] | 45% [30, 64] | -6 pts [-21, +9] | +6 pts [-15, +27] | +6 pts [-6, +21] | -18 pts [-36, +0] |
| Questions answered from literature | 97% [91, 100] | 94% [85, 100] | 97% [91, 100] | 94% [85, 100] | 94% [85, 100] | +3 pts [-6, +12] | +3 pts [-6, +12] | +0 pts [-9, +9] | +0 pts [-12, +12] |
| Final answer close to the true value | 42% [27, 58] | 45% [30, 64] | 58% [39, 73] | 36% [21, 52] | 52% [36, 70] | -3 pts [-15, +9] | +12 pts [-6, +30] | -9 pts [-30, +9] | +6 pts [-9, +21] |
| Final answer in the true value's category (low/normal/high) | 85% [73, 97] | 82% [70, 94] | 82% [67, 94] | 79% [64, 91] | 82% [67, 94] | +3 pts [-6, +12] | +0 pts [-12, +12] | -3 pts [-12, +6] | +0 pts [-12, +12] |

## Set B only (value never stated)

| Metric | current | current_fixed | improved_1to4 | improved_1to5 | openrouter_search | current − current_fixed | improved_1to4 − current_fixed | improved_1to5 − current_fixed | openrouter_search − current_fixed |
|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 8.00 [8.00, 8.00] | 8.00 [8.00, 8.00] | 8.00 [8.00, 8.00] | 8.00 [8.00, 8.00] | 7.83 [7.58, 8.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | -0.17 [-0.42, +0.00] |
| Mean relevance grade (0–3) | 1.04 [0.67, 1.47] | 1.24 [0.98, 1.51] | 1.47 [1.10, 1.81] | 1.46 [1.08, 1.81] | 1.22 [0.93, 1.52] | -0.20 [-0.40, +0.01] | +0.23 [-0.10, +0.59] | +0.22 [-0.04, +0.50] | -0.02 [-0.21, +0.15] |
| Relevant documents (grade ≥ 2), share | 31% [14, 51] | 42% [32, 51] | 58% [41, 74] | 56% [40, 71] | 27% [14, 43] | -10 pts [-22, +1] | +17 pts [+2, +32] | +15 pts [+2, +28] | -15 pts [-24, -5] |
| Questions with ≥ 1 useful document (usefulness 2) | 50% [17, 75] | 83% [58, 100] | 83% [58, 100] | 83% [58, 100] | 67% [42, 92] | -33 pts [-67, -8] | +0 pts [-25, +25] | +0 pts [-33, +33] | -17 pts [-42, +0] |
| Useful documents (usefulness 2), share | 16% [4, 30] | 22% [10, 35] | 40% [23, 55] | 45% [30, 59] | 16% [8, 25] | -6 pts [-9, -3] | +18 pts [+6, +31] | +23 pts [+8, +38] | -6 pts [-17, +1] |
| Questions answered from literature | 58% [33, 83] | 83% [58, 100] | 75% [50, 100] | 75% [50, 100] | 50% [25, 75] | -25 pts [-58, +8] | -8 pts [-25, +0] | -8 pts [-33, +17] | -33 pts [-67, +0] |

## Cost

All runs, including the excluded questions (their calls were paid for).

| Method | Questions | Retrieval (search fees + search model) | medsim LLM (Stages A–C) | Total | Total per question | Median wall time |
|---|---|---|---|---|---|---|
| current | 50 | $0.0000 | $0.0541 | $0.0541 | $0.00108 | 60.6 s |
| current_fixed | 50 | $0.0000 | $0.0499 | $0.0499 | $0.00100 | 67.6 s |
| improved_1to4 | 50 | $0.0000 | $0.0465 | $0.0465 | $0.00093 | 69.6 s |
| improved_1to5 | 50 | $0.0000 | $0.0443 | $0.0443 | $0.00089 | 83.8 s |
| openrouter_search | 50 | $0.3346 | $0.0404 | $0.3750 | $0.00750 | 61.4 s |

## By subgroup (set A)

### Variable category

| Group | n | Questions with ≥ 1 useful document (usefulness 2) — current | Questions with ≥ 1 useful document (usefulness 2) — current_fixed | Questions with ≥ 1 useful document (usefulness 2) — improved_1to4 | Questions with ≥ 1 useful document (usefulness 2) — improved_1to5 | Questions with ≥ 1 useful document (usefulness 2) — openrouter_search | Questions with ≥ 1 document containing the true value (correctness 2) — current | Questions with ≥ 1 document containing the true value (correctness 2) — current_fixed | Questions with ≥ 1 document containing the true value (correctness 2) — improved_1to4 | Questions with ≥ 1 document containing the true value (correctness 2) — improved_1to5 | Questions with ≥ 1 document containing the true value (correctness 2) — openrouter_search |
|---|---|---|---|---|---|---|---|---|---|---|---|
| anthropometric | 5 | 80% | 80% | 100% | 80% | 80% | 20% | 60% | 60% | 60% | 40% |
| laboratory | 14 | 79% | 79% | 93% | 93% | 93% | 21% | 29% | 50% | 50% | 50% |
| vital_sign | 14 | 64% | 93% | 93% | 93% | 93% | 21% | 36% | 50% | 50% | 29% |

### True value (judge's category)

| Group | n | Questions with ≥ 1 useful document (usefulness 2) — current | Questions with ≥ 1 useful document (usefulness 2) — current_fixed | Questions with ≥ 1 useful document (usefulness 2) — improved_1to4 | Questions with ≥ 1 useful document (usefulness 2) — improved_1to5 | Questions with ≥ 1 useful document (usefulness 2) — openrouter_search | Questions with ≥ 1 document containing the true value (correctness 2) — current | Questions with ≥ 1 document containing the true value (correctness 2) — current_fixed | Questions with ≥ 1 document containing the true value (correctness 2) — improved_1to4 | Questions with ≥ 1 document containing the true value (correctness 2) — improved_1to5 | Questions with ≥ 1 document containing the true value (correctness 2) — openrouter_search |
|---|---|---|---|---|---|---|---|---|---|---|---|
| high | 16 | 69% | 69% | 94% | 88% | 93% | 19% | 25% | 44% | 25% | 29% |
| low | 9 | 78% | 100% | 100% | 89% | 100% | 33% | 44% | 44% | 67% | 33% |
| normal | 8 | 75% | 100% | 88% | 100% | 100% | 12% | 50% | 75% | 88% | 75% |
| unknown | 2 | – | – | – | – | 0% | – | – | – | – | 0% |

### Variable typical of the diagnosis

| Group | n | Questions with ≥ 1 useful document (usefulness 2) — current | Questions with ≥ 1 useful document (usefulness 2) — current_fixed | Questions with ≥ 1 useful document (usefulness 2) — improved_1to4 | Questions with ≥ 1 useful document (usefulness 2) — improved_1to5 | Questions with ≥ 1 useful document (usefulness 2) — openrouter_search | Questions with ≥ 1 document containing the true value (correctness 2) — current | Questions with ≥ 1 document containing the true value (correctness 2) — current_fixed | Questions with ≥ 1 document containing the true value (correctness 2) — improved_1to4 | Questions with ≥ 1 document containing the true value (correctness 2) — improved_1to5 | Questions with ≥ 1 document containing the true value (correctness 2) — openrouter_search |
|---|---|---|---|---|---|---|---|---|---|---|---|
| no | 20 | 60% | 80% | 90% | 85% | 85% | 10% | 35% | 55% | 55% | 35% |
| yes | 13 | 92% | 92% | 100% | 100% | 100% | 38% | 38% | 46% | 46% | 46% |

### Documents by source

| Source | Documents judged | Mean relevance | Relevant (≥ 2) | Useful (= 2) |
|---|---|---|---|---|
| europe_pmc | 846 | 1.61 | 63% | 39% |
| litsense | 594 | 1.37 | 45% | 21% |
| openrouter_search | 344 | 1.37 | 36% | 23% |

## Diagnostics

- **current:** answer paths {'synthesizer_unanswerable': 6, 'literature': 39}; source article removed for 7 question(s); 0 document(s) without a judgment.
- **current_fixed:** answer paths {'literature': 41, 'synthesizer_unanswerable': 4}; source article removed for 7 question(s); 0 document(s) without a judgment.
- **improved_1to4:** answer paths {'literature': 41, 'synthesizer_unanswerable': 4}; source article removed for 7 question(s); 0 document(s) without a judgment.
- **improved_1to5:** answer paths {'literature': 40, 'synthesizer_unanswerable': 5}; source article removed for 9 question(s); 0 document(s) without a judgment.
- **openrouter_search:** answer paths {'literature': 37, 'synthesizer_unanswerable': 8}; source article removed for 9 question(s); 0 document(s) without a judgment.
- **Quote check:** 12 of 1528 pass-1 judgments quoted text that is not in the document (usefulness forced to 0).
- **Pass 2:** 117 of 496 verdicts were "not comparable" (excluded from correctness).
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
| run (all methods; search fees included) | $0.5698 |
| judge pass 1 | $0.8775 |
| judge pass 2 | $0.2484 |
| judge answer check | $0.0581 |
| validation: controls | $0.0303 |
| validation: flipped truth | $0.0055 |
| validation: second judge, pass 1 | $0.0698 |
| validation: second judge, pass 2 | $0.0139 |
| **total** | **$2.0207** |

Cross-check: the OpenRouter key's usage counter, read right after each of the 17 benchmark commands, rose by $1.8297. The counter lags behind requests, so this undercounts; per-call usage.cost above is the accounting source.

