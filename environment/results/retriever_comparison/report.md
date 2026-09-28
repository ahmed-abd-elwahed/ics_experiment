# Retrieval benchmark report

- Workspace: `environment/results/retriever_comparison`
- Judge panel: `google/gemini-3.5-flash-lite`, `qwen/qwen3.8-flash`, `openai/gpt-6-luna`. Each answer's label is the panel's majority vote; with no majority, the first (main) judge's label decides.
- medsim models: `deepseek/deepseek-v4-flash-0731`
- `current`: Europe PMC + LitSense passages, relaxation ladders, lexical rerank (the original method)
- `improved_1to4`: changes 1-4: value-first ranking in one list across sources, 50 Europe PMC candidates, animal/age filter, article-body search with excerpts, value-based broadening without the unhelpful rungs (medsim's default since they were measured)
- `openrouter_exa_instant`: openrouter_search with the Exa engine in instant mode; deepseek/deepseek-v4-flash-0731 issues the search
- `openrouter_parallel_basic`: openrouter_search with the Parallel engine in basic mode; deepseek/deepseek-v4-flash-0731 issues the search
- `openrouter_perplexity`: openrouter_search with the Perplexity engine; deepseek/deepseek-v4-flash-0731 issues the search
- `openrouter_google`: openrouter_search with the model's native search, Google Search for google/gemini-3.1-flash-lite, which issues the search
- `openrouter_openai`: openrouter_search with the model's native search, OpenAI web search for openai/gpt-6-luna, which issues the search

## Question sets

- Cases extracted: 272; measured values found: 1235; eligible as hidden values: 536.
- Set A (hidden value): 141 questions accepted; rejected 0 (none).
- Set B (value never stated): 272 questions accepted; rejected 0 (none).
- Every question is scored under every method: each label's percentage is out of all questions in its set. Questions without a successful run (counted as no label): current: 0, improved_1to4: 0, openrouter_exa_instant: 0, openrouter_parallel_basic: 0, openrouter_perplexity: 0, openrouter_google: 0, openrouter_openai: 0.

## All questions (sets A, B)

| Metric | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | openrouter_google | openrouter_openai | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current | openrouter_google − current | openrouter_openai − current |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 7.79 [7.65, 7.90] | 7.85 [7.73, 7.94] | 7.74 [7.62, 7.85] | 7.62 [7.49, 7.75] | 7.67 [7.54, 7.79] | 3.98 [3.77, 4.18] | 3.81 [3.59, 4.03] | +0.06 [-0.09, +0.21] | -0.05 [-0.17, +0.09] | -0.16 [-0.32, +0.00] | -0.11 [-0.25, +0.03] | -3.81 [-4.03, -3.59] | -3.97 [-4.22, -3.72] |
| Questions answered from literature | 86% [82, 90] | 87% [84, 90] | 64% [58, 69] | 83% [79, 87] | 94% [91, 96] | 79% [75, 84] | 77% [73, 82] | +1 pts [-4, +5] | -23 pts [-28, -17] | -3 pts [-8, +2] | +8 pts [+4, +12] | -7 pts [-12, -1] | -9 pts [-14, -4] |
| Masked correctness: exact (% of set A questions) | 38% [29, 46] | 35% [27, 43] | 35% [27, 45] | 28% [20, 35] | 39% [30, 49] | 38% [30, 46] | 35% [27, 43] | -3 pts [-11, +5] | -2 pts [-12, +9] | -10 pts [-20, +0] | +1 pts [-7, +11] | +1 pts [-8, +10] | -3 pts [-11, +6] |
| Masked correctness: same category (% of set A questions) | 42% [33, 51] | 45% [36, 54] | 39% [30, 49] | 45% [36, 54] | 43% [34, 52] | 35% [26, 44] | 42% [33, 51] | +3 pts [-5, +11] | -3 pts [-13, +7] | +4 pts [-6, +13] | +1 pts [-7, +10] | -7 pts [-16, +1] | +0 pts [-8, +8] |
| Masked correctness: different category (% of set A questions) | 12% [7, 18] | 15% [9, 21] | 11% [6, 17] | 18% [12, 26] | 15% [10, 21] | 14% [8, 21] | 15% [9, 21] | +3 pts [-2, +8] | -1 pts [-8, +5] | +6 pts [+1, +13] | +3 pts [-2, +8] | +2 pts [-3, +8] | +3 pts [-3, +9] |
| Masked correctness: not comparable (% of set A questions) | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 1% [0, 2] | 0% [0, 0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +1 pts [+0, +2] | +1 pts [+0, +2] | +0 pts [+0, +0] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 9% [4, 14] | 6% [2, 10] | 15% [9, 21] | 9% [4, 13] | 2% [0, 6] | 12% [6, 18] | 9% [4, 14] | -3 pts [-9, +3] | +6 pts [-1, +14] | +0 pts [-7, +7] | -6 pts [-12, +0] | +4 pts [-4, +11] | +0 pts [-7, +7] |
| Factual consistency: consistent (% of set B questions) | 84% [80, 88] | 84% [79, 88] | 53% [47, 59] | 78% [73, 83] | 93% [89, 96] | 75% [70, 80] | 70% [64, 76] | -0 pts [-7, +6] | -32 pts [-38, -25] | -6 pts [-13, +0] | +8 pts [+4, +14] | -9 pts [-16, -2] | -14 pts [-21, -8] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 0] | 0% [0, 1] | 0% [0, 0] | 0% [0, 1] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | +0 pts [+0, +1] | +0 pts [+0, +0] | +0 pts [+0, +1] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 16% [12, 20] | 16% [12, 21] | 47% [41, 53] | 22% [17, 27] | 7% [4, 11] | 25% [20, 30] | 30% [24, 36] | +0 pts [-6, +6] | +32 pts [+25, +38] | +6 pts [-0, +12] | -8 pts [-14, -4] | +9 pts [+2, +16] | +14 pts [+8, +21] |
| Retrieval cost per question (search fees, search/rerank LLM; USD) | $0.00000 | $0.00000 | $0.00697 | $0.00501 | $0.00500 | $0.04571 | $0.02529 | +0.00000 [+0.00000, +0.00000] | +0.00697 [+0.00688, +0.00706] | +0.00501 [+0.00494, +0.00507] | +0.00500 [+0.00493, +0.00506] | +0.04571 [+0.04388, +0.04746] | +0.02529 [+0.02399, +0.02660] |
| medsim LLM cost per question (Stages A–C, USD) | $0.00110 | $0.00104 | $0.00097 | $0.00111 | $0.00097 | $0.00091 | $0.00085 | -0.00006 [-0.00015, +0.00002] | -0.00014 [-0.00022, -0.00005] | +0.00000 [-0.00009, +0.00009] | -0.00013 [-0.00021, -0.00005] | -0.00019 [-0.00028, -0.00010] | -0.00025 [-0.00033, -0.00018] |
| Total cost per question (USD) | $0.00110 | $0.00104 | $0.00794 | $0.00611 | $0.00597 | $0.04662 | $0.02615 | -0.00006 [-0.00015, +0.00002] | +0.00683 [+0.00670, +0.00696] | +0.00501 [+0.00490, +0.00511] | +0.00487 [+0.00477, +0.00497] | +0.04552 [+0.04369, +0.04729] | +0.02504 [+0.02373, +0.02635] |
| Wall time per question (s) | 86.9 [81.0, 93.5] | 96.4 [90.5, 103.4] | 77.6 [73.2, 82.2] | 86.6 [80.6, 93.1] | 77.5 [72.9, 82.6] | 77.3 [72.6, 82.4] | 79.8 [74.7, 85.4] | +9.50 [+2.55, +16.66] | -9.29 [-15.26, -3.79] | -0.28 [-6.75, +5.87] | -9.40 [-15.49, -3.69] | -9.54 [-16.52, -2.91] | -7.02 [-13.76, -0.53] |
| Time outside medsim's LLM calls per question (≈ retrieval; s) | 10.36 [9.45, 11.34] | 21.03 [19.26, 23.02] | 5.96 [5.51, 6.55] | 6.61 [6.30, 6.92] | 6.36 [6.05, 6.68] | 10.13 [9.73, 10.57] | 13.38 [12.49, 14.55] | +10.67 [+9.20, +12.29] | -4.40 [-5.51, -3.32] | -3.75 [-4.75, -2.82] | -4.00 [-5.00, -3.10] | -0.23 [-1.23, +0.65] | +3.02 [+1.70, +4.41] |

## Set A only (hidden value; masked correctness)

| Metric | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | openrouter_google | openrouter_openai | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current | openrouter_google − current | openrouter_openai − current |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 7.89 [7.72, 8.00] | 7.83 [7.63, 8.00] | 7.82 [7.74, 7.89] | 7.77 [7.69, 7.85] | 7.64 [7.42, 7.81] | 4.18 [3.82, 4.57] | 4.22 [3.84, 4.60] | -0.06 [-0.33, +0.18] | -0.06 [-0.22, +0.13] | -0.11 [-0.27, +0.08] | -0.25 [-0.43, -0.07] | -3.70 [-4.10, -3.31] | -3.67 [-4.10, -3.25] |
| Questions answered from literature | 90% [85, 95] | 93% [88, 97] | 85% [79, 91] | 91% [86, 96] | 96% [93, 99] | 87% [81, 93] | 91% [85, 96] | +3 pts [-4, +10] | -5 pts [-13, +3] | +1 pts [-6, +9] | +6 pts [+0, +13] | -3 pts [-10, +5] | +1 pts [-6, +7] |
| Masked correctness: exact (% of set A questions) | 38% [29, 46] | 35% [27, 43] | 35% [27, 45] | 28% [20, 35] | 39% [30, 49] | 38% [30, 46] | 35% [27, 43] | -3 pts [-11, +5] | -2 pts [-12, +9] | -10 pts [-20, +0] | +1 pts [-7, +11] | +1 pts [-8, +10] | -3 pts [-11, +6] |
| Masked correctness: same category (% of set A questions) | 42% [33, 51] | 45% [36, 54] | 39% [30, 49] | 45% [36, 54] | 43% [34, 52] | 35% [26, 44] | 42% [33, 51] | +3 pts [-5, +11] | -3 pts [-13, +7] | +4 pts [-6, +13] | +1 pts [-7, +10] | -7 pts [-16, +1] | +0 pts [-8, +8] |
| Masked correctness: different category (% of set A questions) | 12% [7, 18] | 15% [9, 21] | 11% [6, 17] | 18% [12, 26] | 15% [10, 21] | 14% [8, 21] | 15% [9, 21] | +3 pts [-2, +8] | -1 pts [-8, +5] | +6 pts [+1, +13] | +3 pts [-2, +8] | +2 pts [-3, +8] | +3 pts [-3, +9] |
| Masked correctness: not comparable (% of set A questions) | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 1% [0, 2] | 0% [0, 0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +1 pts [+0, +2] | +1 pts [+0, +2] | +0 pts [+0, +0] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 9% [4, 14] | 6% [2, 10] | 15% [9, 21] | 9% [4, 13] | 2% [0, 6] | 12% [6, 18] | 9% [4, 14] | -3 pts [-9, +3] | +6 pts [-1, +14] | +0 pts [-7, +7] | -6 pts [-12, +0] | +4 pts [-4, +11] | +0 pts [-7, +7] |

## Set B only (value never stated; factual consistency)

| Metric | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | openrouter_google | openrouter_openai | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current | openrouter_google − current | openrouter_openai − current |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 7.74 [7.55, 7.89] | 7.85 [7.72, 7.97] | 7.70 [7.53, 7.84] | 7.55 [7.35, 7.73] | 7.69 [7.52, 7.83] | 3.87 [3.62, 4.11] | 3.60 [3.37, 3.84] | +0.12 [-0.06, +0.30] | -0.04 [-0.21, +0.13] | -0.19 [-0.41, +0.04] | -0.04 [-0.23, +0.16] | -3.87 [-4.15, -3.58] | -4.13 [-4.40, -3.86] |
| Questions answered from literature | 84% [80, 88] | 84% [79, 88] | 53% [47, 59] | 78% [73, 83] | 93% [89, 96] | 75% [70, 80] | 70% [64, 76] | +0 pts [-6, +6] | -32 pts [-38, -25] | -6 pts [-12, +0] | +8 pts [+4, +14] | -9 pts [-16, -2] | -14 pts [-21, -8] |
| Factual consistency: consistent (% of set B questions) | 84% [80, 88] | 84% [79, 88] | 53% [47, 59] | 78% [73, 83] | 93% [89, 96] | 75% [70, 80] | 70% [64, 76] | -0 pts [-7, +6] | -32 pts [-38, -25] | -6 pts [-13, +0] | +8 pts [+4, +14] | -9 pts [-16, -2] | -14 pts [-21, -8] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 0] | 0% [0, 1] | 0% [0, 0] | 0% [0, 1] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | +0 pts [+0, +1] | +0 pts [+0, +0] | +0 pts [+0, +1] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 16% [12, 20] | 16% [12, 21] | 47% [41, 53] | 22% [17, 27] | 7% [4, 11] | 25% [20, 30] | 30% [24, 36] | +0 pts [-6, +6] | +32 pts [+25, +38] | +6 pts [-0, +12] | -8 pts [-14, -4] | +9 pts [+2, +16] | +14 pts [+8, +21] |

## Cost

All questions that ran.

| Method | Questions | Retrieval (search fees + search model) | medsim LLM (Stages A–C) | Total | Total per question | Median wall time |
|---|---|---|---|---|---|---|
| current | 413 | $0.0000 | $0.4563 | $0.4563 | $0.00110 | 74.1 s |
| improved_1to4 | 413 | $0.0000 | $0.4303 | $0.4303 | $0.00104 | 82.4 s |
| openrouter_exa_instant | 413 | $2.8800 | $0.3989 | $3.2790 | $0.00794 | 63.9 s |
| openrouter_parallel_basic | 413 | $2.0680 | $0.4565 | $2.5245 | $0.00611 | 68.6 s |
| openrouter_perplexity | 413 | $2.0650 | $0.4025 | $2.4675 | $0.00597 | 63.3 s |
| openrouter_google | 413 | $18.8777 | $0.3772 | $19.2549 | $0.04662 | 66.4 s |
| openrouter_openai | 413 | $10.4466 | $0.3523 | $10.7989 | $0.02615 | 66.0 s |

## By subgroup (set A)

### Variable category

| Group | n | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: exact (% of set A questions) — openrouter_google | Masked correctness: exact (% of set A questions) — openrouter_openai | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — openrouter_google | Masked correctness: different category (% of set A questions) — openrouter_openai |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| anthropometric | 22 | 32% | 50% | 41% | 36% | 45% | 45% | 45% | 9% | 9% | 5% | 18% | 9% | 5% | 9% |
| laboratory | 77 | 27% | 26% | 22% | 21% | 32% | 35% | 29% | 10% | 12% | 14% | 12% | 9% | 9% | 13% |
| vital_sign | 42 | 60% | 43% | 57% | 36% | 48% | 40% | 40% | 17% | 24% | 7% | 31% | 29% | 29% | 21% |

### True value (judge's category)

| Group | n | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: exact (% of set A questions) — openrouter_google | Masked correctness: exact (% of set A questions) — openrouter_openai | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — openrouter_google | Masked correctness: different category (% of set A questions) — openrouter_openai |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| high | 73 | 32% | 31% | 32% | 25% | 32% | 35% | 29% | 13% | 17% | 13% | 20% | 13% | 17% | 21% |
| low | 33 | 50% | 39% | 43% | 21% | 44% | 57% | 41% | 3% | 6% | 7% | 14% | 9% | 10% | 6% |
| normal | 42 | 53% | 48% | 63% | 44% | 49% | 45% | 50% | 20% | 22% | 15% | 26% | 23% | 21% | 19% |
| not_applicable | 3 | 0% | 50% | 0% | 100% | 67% | 100% | 100% | 100% | 50% | 100% | 0% | 33% | 0% | 0% |
| unknown | 58 | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% |

### Variable typical of the diagnosis

| Group | n | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: exact (% of set A questions) — openrouter_google | Masked correctness: exact (% of set A questions) — openrouter_openai | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — openrouter_google | Masked correctness: different category (% of set A questions) — openrouter_openai |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| no | 83 | 36% | 36% | 35% | 33% | 45% | 40% | 31% | 18% | 20% | 12% | 24% | 22% | 22% | 19% |
| yes | 58 | 40% | 33% | 36% | 21% | 31% | 36% | 40% | 3% | 7% | 9% | 10% | 5% | 3% | 9% |

## Diagnostics

- **current:** answer paths {'literature': 356, 'synthesizer_unanswerable': 46, 'case_study': 2, 'query_builder_declined': 9}; source article removed for 50 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **improved_1to4:** answer paths {'literature': 360, 'synthesizer_unanswerable': 45, 'case_study': 2, 'off_topic': 2, 'query_builder_declined': 4}; source article removed for 57 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_exa_instant:** answer paths {'synthesizer_unanswerable': 143, 'literature': 263, 'query_builder_declined': 6, 'off_topic': 1}; source article removed for 47 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_parallel_basic:** answer paths {'synthesizer_unanswerable': 62, 'literature': 342, 'no_documents': 1, 'query_builder_declined': 7, 'off_topic': 1}; source article removed for 38 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_perplexity:** answer paths {'synthesizer_unanswerable': 16, 'literature': 388, 'case_study': 2, 'query_builder_declined': 7}; source article removed for 35 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_google:** answer paths {'literature': 327, 'no_documents': 39, 'synthesizer_unanswerable': 40, 'case_study': 1, 'query_builder_declined': 5, 'off_topic': 1}; source article removed for 41 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_openai:** answer paths {'literature': 319, 'synthesizer_unanswerable': 76, 'case_study': 1, 'no_documents': 10, 'query_builder_declined': 7}; source article removed for 47 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **Masked correctness:** 2 of 902 voted labels were "not comparable" (reported as their own label).
- **Judge errors (all attempts, all judges):** 0 judgment(s) failed; rerun the judge step to retry them.

## Judge panel agreement

| Metric | Answers | Unanimous | Majority | Tie broken by the main judge | Tie broken by the next judge | Fewer than all votes |
|---|---|---|---|---|---|---|
| masked correctness | 902 | 75% | 25% | 1% | 0% | 0 |
| factual consistency | 1461 | 99% | 1% | 0% | 0% | 0 |

- **masked correctness, `google/gemini-3.5-flash-lite` vs `qwen/qwen3.8-flash`:** 728/902 identical labels, Cohen's κ = 0.69.
- **masked correctness, `google/gemini-3.5-flash-lite` vs `openai/gpt-6-luna`:** 692/902 identical labels, Cohen's κ = 0.63.
- **masked correctness, `qwen/qwen3.8-flash` vs `openai/gpt-6-luna`:** 824/902 identical labels, Cohen's κ = 0.86.
- **factual consistency, `google/gemini-3.5-flash-lite` vs `qwen/qwen3.8-flash`:** 1452/1461 identical labels, Cohen's κ = -0.00.
- **factual consistency, `google/gemini-3.5-flash-lite` vs `openai/gpt-6-luna`:** 1456/1461 identical labels, Cohen's κ = 0.28.
- **factual consistency, `qwen/qwen3.8-flash` vs `openai/gpt-6-luna`:** 1457/1461 identical labels, Cohen's κ = 0.33.

## Benchmark spend

| Step | Cost (USD, OpenRouter usage.cost) |
|---|---|
| extract (case facts) | $0.0000 |
| redact + Stage A checks (accepted) | $0.0000 |
| redact + Stage A checks (rejected) | $0.0000 |
| run (all methods; search fees included) | $39.2114 |
| judge: masked correctness (google/gemini-3.5-flash-lite) | $0.4989 |
| judge: masked correctness (openai/gpt-6-luna) | $0.1750 |
| judge: masked correctness (qwen/qwen3.8-flash) | $0.3468 |
| judge: factual consistency (google/gemini-3.5-flash-lite) | $0.6486 |
| judge: factual consistency (openai/gpt-6-luna) | $0.1858 |
| judge: factual consistency (qwen/qwen3.8-flash) | $0.2797 |
| validation: controls (panel) | $0.0000 |
| validation: flipped truth (panel) | $0.0000 |
| **total** | **$41.3463** |

Cross-check: the OpenRouter key's usage counter, read right after each of the 4 benchmark commands, rose by $40.2060. The counter lags behind requests, so this undercounts; per-call usage.cost above is the accounting source.

