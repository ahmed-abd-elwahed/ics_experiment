# Retrieval benchmark report

- Workspace: `environment/results/repeats/run_09/sets_ab`
- Judge panel: `google/gemini-3.5-flash-lite`, `qwen/qwen3.8-flash`, `openai/gpt-6-luna`. Each answer's label is the panel's majority vote; with no majority, the first (main) judge's label decides.
- `gemini_knowledge`: no search: google/gemini-3-flash-preview is the source, given the question, the case information (as medsim sees it), and the diagnosis, and asked for the value that typically fits; medsim's stages as usual
- `current`: Europe PMC + LitSense passages, relaxation ladders, lexical rerank (the original method)
- `improved_1to4`: changes 1-4: value-first ranking in one list across sources, 50 Europe PMC candidates, animal/age filter, article-body search with excerpts, value-based broadening without the unhelpful rungs (medsim's default since they were measured)
- `openrouter_exa_instant`: openrouter_search with the Exa engine in instant mode; deepseek/deepseek-v4-flash-0731 issues the search
- `openrouter_parallel_basic`: openrouter_search with the Parallel engine in basic mode; deepseek/deepseek-v4-flash-0731 issues the search
- `openrouter_perplexity`: openrouter_search with the Perplexity engine; deepseek/deepseek-v4-flash-0731 issues the search

## Question sets

- Cases extracted: 272; measured values found: 1235; eligible as hidden values: 536.
- Set A (hidden value): 141 questions accepted; rejected 0 (none).
- Set B (value never stated): 272 questions accepted; rejected 0 (none).
- Every question is scored under every method: each label's percentage is out of all questions in its set. Questions without a successful run (counted as no label): gemini_knowledge: 0, current: 0, improved_1to4: 0, openrouter_exa_instant: 0, openrouter_parallel_basic: 0, openrouter_perplexity: 0.

## All questions (sets A, B)

| Metric | gemini_knowledge | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 0.98 [0.97, 1.00] | 7.81 [7.67, 7.92] | 7.86 [7.75, 7.95] | 7.81 [7.72, 7.89] | 7.65 [7.53, 7.75] | 7.61 [7.48, 7.71] | -6.82 [-6.94, -6.69] | +0.06 [-0.04, +0.17] | +0.00 [-0.12, +0.13] | -0.16 [-0.29, -0.01] | -0.20 [-0.35, -0.05] |
| Questions answered from literature | 90% [88, 93] | 31% [26, 35] | 49% [44, 54] | 33% [28, 38] | 35% [30, 40] | 62% [56, 67] | +60 pts [+55, +66] | +19 pts [+13, +25] | +3 pts [-3, +9] | +5 pts [-1, +11] | +31 pts [+25, +38] |
| Questions answered with a best guess (documents gave no usable basis) | 8% [5, 11] | 67% [62, 72] | 49% [44, 54] | 66% [61, 71] | 62% [58, 67] | 36% [30, 41] | -59 pts [-65, -54] | -18 pts [-24, -12] | -1 pts [-8, +5] | -5 pts [-11, +1] | -31 pts [-38, -24] |
| Masked correctness: exact (% of set A questions) | 43% [35, 52] | 45% [36, 54] | 44% [35, 53] | 43% [35, 52] | 40% [32, 49] | 40% [31, 49] | -1 pts [-9, +7] | -1 pts [-9, +7] | -1 pts [-11, +9] | -4 pts [-12, +4] | -5 pts [-13, +3] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 84% [77, 90] | 87% [80, 92] | 87% [80, 92] | 88% [82, 93] | 83% [76, 89] | 85% [79, 90] | -3 pts [-9, +3] | +0 pts [-5, +5] | +1 pts [-4, +7] | -4 pts [-9, +1] | -1 pts [-8, +5] |
| Masked correctness: different category (% of set A questions) | 16% [10, 22] | 11% [6, 17] | 13% [7, 19] | 11% [6, 17] | 16% [10, 24] | 14% [9, 21] | +4 pts [-2, +10] | +1 pts [-4, +7] | +0 pts [-6, +6] | +5 pts [+1, +10] | +3 pts [-3, +9] |
| Masked correctness: not comparable (% of set A questions) | 1% [0, 2] | 2% [0, 5] | 1% [0, 2] | 1% [0, 2] | 1% [0, 2] | 1% [0, 2] | -1 pts [-3, +0] | -1 pts [-3, +0] | -1 pts [-3, +0] | -1 pts [-4, +1] | -1 pts [-4, +1] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] |
| Factual consistency: consistent (% of set B questions) | 98% [96, 100] | 97% [95, 99] | 97% [95, 99] | 99% [98, 100] | 98% [96, 99] | 97% [95, 99] | +1 pts [-1, +3] | +0 pts [-2, +2] | +2 pts [+0, +4] | +0 pts [-2, +3] | -0 pts [-3, +2] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 0] | 0% [0, 0] | 0% [0, 1] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | +0 pts [+0, +0] | +0 pts [+0, +1] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 2% [0, 4] | 3% [1, 5] | 2% [1, 4] | 1% [0, 2] | 2% [1, 4] | 3% [1, 5] | -1 pts [-3, +1] | -0 pts [-2, +1] | -2 pts [-4, +0] | -0 pts [-3, +2] | +0 pts [-2, +3] |
| Retrieval cost per question (search fees, search/rerank LLM; USD) | $0.00072 | $0.00000 | $0.00000 | $0.00711 | $0.00507 | $0.00506 | +0.00072 [+0.00070, +0.00073] | +0.00000 [+0.00000, +0.00000] | +0.00711 [+0.00704, +0.00716] | +0.00507 [+0.00500, +0.00515] | +0.00506 [+0.00498, +0.00513] |
| medsim LLM cost per question (Stages A–C, USD) | $0.00205 | $0.00263 | $0.00289 | $0.00287 | $0.00279 | $0.00322 | -0.00058 [-0.00079, -0.00039] | +0.00026 [-0.00002, +0.00053] | +0.00024 [-0.00004, +0.00052] | +0.00016 [-0.00009, +0.00042] | +0.00059 [+0.00032, +0.00085] |
| Total cost per question (USD) | $0.00277 | $0.00263 | $0.00289 | $0.00997 | $0.00786 | $0.00828 | +0.00014 [-0.00008, +0.00033] | +0.00026 [-0.00002, +0.00053] | +0.00735 [+0.00707, +0.00764] | +0.00524 [+0.00496, +0.00549] | +0.00565 [+0.00537, +0.00593] |
| Wall time per question (s) | 77.4 [73.5, 81.8] | 128.4 [120.2, 136.6] | 109.8 [103.4, 117.0] | 105.8 [98.9, 113.2] | 92.2 [87.9, 97.3] | 100.7 [95.0, 107.0] | -50.98 [-59.00, -42.45] | -18.59 [-29.57, -7.41] | -22.52 [-32.93, -12.66] | -36.15 [-45.75, -27.15] | -27.62 [-37.39, -17.85] |
| Time outside medsim's LLM calls per question (≈ retrieval; s) | 3.15 [3.06, 3.24] | 36.66 [33.66, 39.81] | 15.99 [14.99, 17.07] | 6.95 [6.67, 7.23] | 6.94 [6.63, 7.28] | 6.49 [6.20, 6.77] | -33.51 [-36.71, -30.54] | -20.67 [-23.62, -17.94] | -29.70 [-32.80, -26.77] | -29.71 [-32.82, -26.80] | -30.16 [-33.23, -27.24] |

## Set A only (hidden value; masked correctness)

| Metric | gemini_knowledge | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 0.99 [0.96, 1.00] | 7.83 [7.64, 8.00] | 7.94 [7.82, 8.00] | 7.72 [7.54, 7.87] | 7.59 [7.40, 7.77] | 7.62 [7.42, 7.79] | -6.84 [-7.01, -6.66] | +0.11 [+0.00, +0.28] | -0.11 [-0.31, +0.09] | -0.24 [-0.41, -0.05] | -0.21 [-0.41, +0.01] |
| Questions answered from literature | 91% [86, 95] | 36% [28, 44] | 52% [43, 61] | 42% [33, 51] | 40% [33, 49] | 63% [54, 72] | +55 pts [+45, +64] | +16 pts [+6, +28] | +6 pts [-4, +15] | +4 pts [-5, +14] | +27 pts [+16, +39] |
| Questions answered with a best guess (documents gave no usable basis) | 8% [4, 12] | 62% [53, 70] | 47% [37, 56] | 57% [48, 65] | 57% [49, 65] | 35% [27, 45] | -54 pts [-64, -44] | -15 pts [-25, -5] | -5 pts [-14, +5] | -4 pts [-14, +5] | -26 pts [-38, -15] |
| Masked correctness: exact (% of set A questions) | 43% [35, 52] | 45% [36, 54] | 44% [35, 53] | 43% [35, 52] | 40% [32, 49] | 40% [31, 49] | -1 pts [-9, +7] | -1 pts [-9, +7] | -1 pts [-11, +9] | -4 pts [-12, +4] | -5 pts [-13, +3] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 84% [77, 90] | 87% [80, 92] | 87% [80, 92] | 88% [82, 93] | 83% [76, 89] | 85% [79, 90] | -3 pts [-9, +3] | +0 pts [-5, +5] | +1 pts [-4, +7] | -4 pts [-9, +1] | -1 pts [-8, +5] |
| Masked correctness: different category (% of set A questions) | 16% [10, 22] | 11% [6, 17] | 13% [7, 19] | 11% [6, 17] | 16% [10, 24] | 14% [9, 21] | +4 pts [-2, +10] | +1 pts [-4, +7] | +0 pts [-6, +6] | +5 pts [+1, +10] | +3 pts [-3, +9] |
| Masked correctness: not comparable (% of set A questions) | 1% [0, 2] | 2% [0, 5] | 1% [0, 2] | 1% [0, 2] | 1% [0, 2] | 1% [0, 2] | -1 pts [-3, +0] | -1 pts [-3, +0] | -1 pts [-3, +0] | -1 pts [-4, +1] | -1 pts [-4, +1] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] |

## Set B only (value never stated; factual consistency)

| Metric | gemini_knowledge | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 0.98 [0.96, 1.00] | 7.79 [7.63, 7.92] | 7.82 [7.66, 7.94] | 7.85 [7.74, 7.93] | 7.68 [7.51, 7.81] | 7.60 [7.43, 7.75] | -6.81 [-6.94, -6.65] | +0.03 [-0.09, +0.15] | +0.06 [-0.09, +0.22] | -0.12 [-0.29, +0.05] | -0.19 [-0.39, +0.01] |
| Questions answered from literature | 90% [86, 94] | 28% [22, 34] | 47% [41, 53] | 29% [23, 35] | 33% [27, 38] | 61% [55, 67] | +62 pts [+55, +69] | +20 pts [+11, +28] | +1 pts [-6, +8] | +5 pts [-3, +13] | +34 pts [+25, +42] |
| Questions answered with a best guess (documents gave no usable basis) | 8% [5, 12] | 70% [63, 76] | 50% [44, 57] | 70% [64, 76] | 65% [59, 71] | 36% [30, 42] | -62 pts [-68, -54] | -19 pts [-27, -11] | +0 pts [-7, +8] | -5 pts [-13, +3] | -34 pts [-42, -26] |
| Factual consistency: consistent (% of set B questions) | 98% [96, 100] | 97% [95, 99] | 97% [95, 99] | 99% [98, 100] | 98% [96, 99] | 97% [95, 99] | +1 pts [-1, +3] | +0 pts [-2, +2] | +2 pts [+0, +4] | +0 pts [-2, +3] | -0 pts [-3, +2] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 0] | 0% [0, 0] | 0% [0, 1] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | +0 pts [+0, +0] | +0 pts [+0, +1] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 2% [0, 4] | 3% [1, 5] | 2% [1, 4] | 1% [0, 2] | 2% [1, 4] | 3% [1, 5] | -1 pts [-3, +1] | -0 pts [-2, +1] | -2 pts [-4, +0] | -0 pts [-3, +2] | +0 pts [-2, +3] |

## Cost

All questions that ran.

| Method | Questions | Retrieval (search fees + search model) | medsim LLM (Stages A–C) | Total | Total per question | Median wall time |
|---|---|---|---|---|---|---|
| gemini_knowledge | 413 | $0.2970 | $0.8456 | $1.1426 | $0.00277 | 67.2 s |
| current | 413 | $0.0000 | $1.0855 | $1.0855 | $0.00263 | 113.1 s |
| improved_1to4 | 413 | $0.0000 | $1.1916 | $1.1916 | $0.00289 | 94.8 s |
| openrouter_exa_instant | 413 | $2.9355 | $1.1839 | $4.1193 | $0.00997 | 88.0 s |
| openrouter_parallel_basic | 413 | $2.0951 | $1.1526 | $3.2476 | $0.00786 | 79.8 s |
| openrouter_perplexity | 413 | $2.0911 | $1.3290 | $3.4201 | $0.00828 | 87.7 s |

## By subgroup (set A)

### Variable category

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| anthropometric | 22 | 50% | 55% | 50% | 50% | 55% | 55% | 5% | 9% | 5% | 5% | 14% | 5% |
| laboratory | 77 | 34% | 30% | 32% | 34% | 30% | 29% | 16% | 9% | 12% | 9% | 13% | 9% |
| vital_sign | 42 | 57% | 67% | 62% | 57% | 52% | 52% | 21% | 17% | 19% | 19% | 24% | 29% |

### True value (judge's category)

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| high | 73 | 34% | 35% | 36% | 35% | 32% | 32% | 16% | 11% | 17% | 10% | 15% | 17% |
| low | 33 | 53% | 47% | 42% | 48% | 39% | 38% | 7% | 3% | 6% | 6% | 13% | 6% |
| normal | 43 | 51% | 62% | 59% | 53% | 55% | 57% | 22% | 16% | 11% | 21% | 21% | 16% |
| not_applicable | 2 | 100% | 50% | 100% | 100% | 100% | – | 0% | 50% | 0% | 0% | 0% | – |

### Variable typical of the diagnosis

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| no | 83 | 45% | 49% | 48% | 45% | 42% | 40% | 22% | 17% | 18% | 17% | 23% | 20% |
| yes | 58 | 41% | 38% | 38% | 41% | 38% | 40% | 7% | 3% | 5% | 3% | 7% | 5% |

## Diagnostics

- **gemini_knowledge:** answer paths {'literature': 373, 'best_guess': 33, 'case_study': 2, 'query_builder_declined': 5}; source article removed for 0 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **current:** answer paths {'literature': 126, 'best_guess': 277, 'case_study': 3, 'withheld': 1, 'query_builder_declined': 6}; source article removed for 53 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **improved_1to4:** answer paths {'literature': 203, 'best_guess': 203, 'case_study': 1, 'query_builder_declined': 6}; source article removed for 60 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_exa_instant:** answer paths {'literature': 138, 'best_guess': 271, 'case_study': 2, 'query_builder_declined': 2}; source article removed for 44 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_parallel_basic:** answer paths {'best_guess': 258, 'literature': 146, 'case_study': 3, 'query_builder_declined': 5, 'off_topic': 1}; source article removed for 36 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_perplexity:** answer paths {'best_guess': 147, 'literature': 256, 'case_study': 2, 'query_builder_declined': 7, 'off_topic': 1}; source article removed for 45 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **Masked correctness:** 8 of 846 voted labels were "not comparable" (reported as their own label).
- **Judge errors (all attempts, all judges):** 676 judgment(s) failed; rerun the judge step to retry them.

## Judge panel agreement

| Metric | Answers | Unanimous | Majority | Tie broken by the main judge | Tie broken by the next judge | Fewer than all votes |
|---|---|---|---|---|---|---|
| masked correctness | 846 | 73% | 26% | 0% | 0% | 0 |
| factual consistency | 1598 | 100% | 0% | 0% | 0% | 0 |

- **masked correctness, `google/gemini-3.5-flash-lite` vs `qwen/qwen3.8-flash`:** 674/846 identical labels, Cohen's κ = 0.67.
- **masked correctness, `google/gemini-3.5-flash-lite` vs `openai/gpt-6-luna`:** 652/846 identical labels, Cohen's κ = 0.63.
- **masked correctness, `qwen/qwen3.8-flash` vs `openai/gpt-6-luna`:** 752/846 identical labels, Cohen's κ = 0.82.
- **factual consistency, `google/gemini-3.5-flash-lite` vs `qwen/qwen3.8-flash`:** 1593/1598 identical labels, Cohen's κ = 0.28.
- **factual consistency, `google/gemini-3.5-flash-lite` vs `openai/gpt-6-luna`:** 1592/1598 identical labels, Cohen's κ = -0.00.
- **factual consistency, `qwen/qwen3.8-flash` vs `openai/gpt-6-luna`:** 1595/1598 identical labels, Cohen's κ = -0.00.

## Benchmark spend

| Step | Cost (USD, OpenRouter usage.cost) |
|---|---|
| extract (case facts) | $0.0000 |
| redact + Stage A checks (accepted) | $0.0000 |
| redact + Stage A checks (rejected) | $0.0000 |
| run (all methods; search fees included) | $14.2067 |
| judge: masked correctness (google/gemini-3.5-flash-lite) | $0.4674 |
| judge: masked correctness (openai/gpt-6-luna) | $0.1615 |
| judge: masked correctness (qwen/qwen3.8-flash) | $0.3131 |
| judge: factual consistency (google/gemini-3.5-flash-lite) | $0.7053 |
| judge: factual consistency (openai/gpt-6-luna) | $0.1990 |
| judge: factual consistency (qwen/qwen3.8-flash) | $0.2692 |
| validation: controls (panel) | $0.0000 |
| validation: flipped truth (panel) | $0.0000 |
| **total** | **$16.3223** |

Cross-check: the OpenRouter key's usage counter, read right after each of the 4 benchmark commands, rose by $0.9521. The counter lags behind requests, so this undercounts; per-call usage.cost above is the accounting source.

