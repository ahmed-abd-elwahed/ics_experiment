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
- `gemini_knowledge`: no search: google/gemini-3-flash-preview is the source, given the question, the case information (as medsim sees it), and the diagnosis, and asked for the value that typically fits; medsim's stages as usual

## Question sets

- Cases extracted: 272; measured values found: 1235; eligible as hidden values: 536.
- Set A (hidden value): 141 questions accepted; rejected 0 (none).
- Set B (value never stated): 272 questions accepted; rejected 0 (none).
- Every question is scored under every method: each label's percentage is out of all questions in its set. Questions without a successful run (counted as no label): current: 0, improved_1to4: 0, openrouter_exa_instant: 0, openrouter_parallel_basic: 0, openrouter_perplexity: 0, openrouter_google: 0, openrouter_openai: 0, gemini_knowledge: 0.

## All questions (sets A, B)

| Metric | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | openrouter_google | openrouter_openai | gemini_knowledge | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current | openrouter_google − current | openrouter_openai − current | gemini_knowledge − current |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 7.71 [7.55, 7.84] | 7.81 [7.68, 7.92] | 7.65 [7.50, 7.78] | 7.61 [7.47, 7.73] | 7.67 [7.54, 7.79] | 4.44 [4.26, 4.61] | 3.78 [3.56, 4.00] | 0.97 [0.96, 0.99] | +0.10 [-0.04, +0.25] | -0.06 [-0.22, +0.11] | -0.10 [-0.28, +0.08] | -0.04 [-0.17, +0.11] | -3.27 [-3.48, -3.07] | -3.92 [-4.17, -3.66] | -6.74 [-6.86, -6.59] |
| Questions answered from literature | 86% [83, 90] | 87% [84, 90] | 64% [58, 69] | 83% [79, 87] | 94% [91, 96] | 82% [78, 86] | 77% [73, 82] | 94% [92, 96] | +1 pts [-4, +5] | -23 pts [-28, -17] | -4 pts [-9, +1] | +8 pts [+3, +12] | -4 pts [-9, +1] | -9 pts [-14, -4] | +8 pts [+4, +12] |
| Questions answered with a best guess (documents gave no usable basis) | 10% [7, 13] | 10% [7, 14] | 33% [28, 38] | 15% [11, 19] | 4% [2, 6] | 15% [11, 19] | 19% [15, 24] | 3% [2, 5] | +0 pts [-4, +5] | +23 pts [+17, +29] | +5 pts [+0, +10] | -6 pts [-10, -2] | +5 pts [+0, +10] | +9 pts [+5, +14] | -7 pts [-11, -3] |
| Masked correctness: exact (% of set A questions) | 43% [34, 51] | 37% [29, 45] | 43% [34, 52] | 33% [26, 42] | 39% [30, 49] | 41% [32, 50] | 42% [33, 51] | 43% [34, 52] | -6 pts [-13, +2] | +0 pts [-9, +9] | -9 pts [-17, -1] | -4 pts [-11, +5] | -1 pts [-10, +7] | -1 pts [-8, +7] | +1 pts [-7, +7] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 87% [81, 93] | 82% [75, 88] | 86% [79, 91] | 81% [73, 88] | 84% [78, 90] | 83% [76, 89] | 85% [79, 91] | 87% [80, 92] | -5 pts [-10, +0] | -1 pts [-8, +4] | -6 pts [-12, -1] | -3 pts [-8, +3] | -4 pts [-10, +1] | -2 pts [-8, +4] | -1 pts [-6, +4] |
| Masked correctness: different category (% of set A questions) | 13% [7, 19] | 17% [11, 24] | 13% [8, 20] | 19% [12, 27] | 15% [10, 21] | 16% [10, 23] | 15% [9, 21] | 13% [8, 20] | +4 pts [-1, +9] | +1 pts [-5, +7] | +6 pts [+1, +12] | +2 pts [-4, +7] | +4 pts [-2, +9] | +2 pts [-4, +8] | +1 pts [-4, +6] |
| Masked correctness: not comparable (% of set A questions) | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 0% [0, 0] | 1% [0, 2] | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | +0 pts [+0, +0] | +1 pts [+0, +2] | +0 pts [+0, +0] | +1 pts [+0, +2] | +1 pts [+0, +2] | +0 pts [+0, +0] | +0 pts [+0, +0] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 0% [0, 0] | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | +1 pts [+0, +2] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] |
| Factual consistency: consistent (% of set B questions) | 95% [92, 98] | 97% [95, 99] | 96% [93, 98] | 96% [94, 98] | 97% [95, 99] | 97% [94, 99] | 96% [93, 98] | 97% [94, 99] | +2 pts [-0, +4] | +1 pts [-2, +3] | +1 pts [-2, +4] | +2 pts [+0, +5] | +1 pts [-1, +4] | +0 pts [-2, +3] | +1 pts [-1, +4] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 0] | 0% [0, 1] | 0% [0, 0] | 0% [0, 1] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | +0 pts [+0, +1] | +0 pts [+0, +0] | +0 pts [+0, +1] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 5% [2, 8] | 3% [1, 5] | 4% [2, 7] | 3% [1, 6] | 3% [1, 5] | 3% [1, 6] | 4% [2, 7] | 3% [1, 6] | -2 pts [-5, +0] | -1 pts [-3, +2] | -1 pts [-4, +1] | -2 pts [-5, +0] | -1 pts [-4, +1] | -0 pts [-3, +2] | -1 pts [-4, +1] |
| Retrieval cost per question (search fees, search/rerank LLM; USD) | $0.00000 | $0.00000 | $0.00697 | $0.00501 | $0.00500 | $0.05012 | $0.02529 | $0.00072 | +0.00000 [+0.00000, +0.00000] | +0.00697 [+0.00688, +0.00706] | +0.00501 [+0.00494, +0.00507] | +0.00500 [+0.00493, +0.00506] | +0.05012 [+0.04907, +0.05114] | +0.02529 [+0.02399, +0.02660] | +0.00072 [+0.00070, +0.00073] |
| medsim LLM cost per question (Stages A–C, USD) | $0.00107 | $0.00101 | $0.00091 | $0.00108 | $0.00098 | $0.00094 | $0.00086 | $0.00088 | -0.00006 [-0.00014, +0.00002] | -0.00016 [-0.00025, -0.00007] | +0.00001 [-0.00008, +0.00010] | -0.00009 [-0.00017, -0.00002] | -0.00014 [-0.00022, -0.00006] | -0.00022 [-0.00029, -0.00014] | -0.00019 [-0.00028, -0.00010] |
| Total cost per question (USD) | $0.00107 | $0.00101 | $0.00789 | $0.00609 | $0.00598 | $0.05106 | $0.02615 | $0.00160 | -0.00006 [-0.00014, +0.00002] | +0.00682 [+0.00669, +0.00694] | +0.00502 [+0.00491, +0.00513] | +0.00491 [+0.00481, +0.00501] | +0.04998 [+0.04895, +0.05101] | +0.02508 [+0.02377, +0.02640] | +0.00053 [+0.00044, +0.00061] |
| Wall time per question (s) | 86.1 [80.2, 92.4] | 94.3 [89.0, 100.5] | 74.2 [70.1, 78.8] | 84.2 [78.6, 90.4] | 78.8 [73.9, 84.1] | 82.4 [77.6, 87.6] | 79.9 [75.0, 85.3] | 72.8 [69.8, 76.3] | +8.25 [+2.24, +14.30] | -11.85 [-18.05, -5.92] | -1.82 [-7.76, +3.77] | -7.27 [-13.43, -1.65] | -3.64 [-10.86, +3.05] | -6.13 [-12.52, -0.14] | -13.22 [-19.55, -7.13] |
| Time outside medsim's LLM calls per question (≈ retrieval; s) | 10.36 [9.45, 11.34] | 21.03 [19.26, 23.02] | 5.96 [5.52, 6.56] | 6.61 [6.30, 6.92] | 6.36 [6.05, 6.68] | 11.05 [10.55, 11.59] | 13.38 [12.49, 14.55] | 4.76 [4.35, 5.29] | +10.67 [+9.20, +12.29] | -4.40 [-5.51, -3.32] | -3.75 [-4.75, -2.82] | -4.00 [-5.00, -3.10] | +0.69 [-0.32, +1.60] | +3.02 [+1.70, +4.42] | -5.60 [-6.70, -4.62] |

## Set A only (hidden value; masked correctness)

| Metric | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | openrouter_google | openrouter_openai | gemini_knowledge | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current | openrouter_google − current | openrouter_openai − current | gemini_knowledge − current |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 7.89 [7.72, 8.00] | 7.83 [7.63, 8.00] | 7.77 [7.62, 7.88] | 7.77 [7.69, 7.85] | 7.64 [7.42, 7.81] | 4.58 [4.28, 4.88] | 4.22 [3.84, 4.60] | 0.99 [0.96, 1.00] | -0.06 [-0.33, +0.18] | -0.12 [-0.33, +0.09] | -0.11 [-0.27, +0.08] | -0.25 [-0.43, -0.07] | -3.30 [-3.62, -2.99] | -3.67 [-4.10, -3.25] | -6.90 [-7.01, -6.74] |
| Questions answered from literature | 91% [85, 96] | 93% [88, 97] | 85% [79, 91] | 91% [86, 96] | 96% [93, 99] | 91% [86, 95] | 91% [85, 96] | 95% [91, 98] | +2 pts [-5, +9] | -6 pts [-14, +2] | +1 pts [-7, +8] | +6 pts [-1, +12] | +0 pts [-6, +7] | +0 pts [-6, +7] | +4 pts [-2, +10] |
| Questions answered with a best guess (documents gave no usable basis) | 8% [3, 13] | 5% [2, 9] | 14% [9, 20] | 9% [4, 13] | 2% [0, 6] | 9% [4, 14] | 9% [4, 14] | 4% [1, 7] | -3 pts [-9, +3] | +6 pts [-1, +14] | +1 pts [-6, +8] | -6 pts [-12, +1] | +1 pts [-6, +7] | +1 pts [-6, +7] | -4 pts [-10, +1] |
| Masked correctness: exact (% of set A questions) | 43% [34, 51] | 37% [29, 45] | 43% [34, 52] | 33% [26, 42] | 39% [30, 49] | 41% [32, 50] | 42% [33, 51] | 43% [34, 52] | -6 pts [-13, +2] | +0 pts [-9, +9] | -9 pts [-17, -1] | -4 pts [-11, +5] | -1 pts [-10, +7] | -1 pts [-8, +7] | +1 pts [-7, +7] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 87% [81, 93] | 82% [75, 88] | 86% [79, 91] | 81% [73, 88] | 84% [78, 90] | 83% [76, 89] | 85% [79, 91] | 87% [80, 92] | -5 pts [-10, +0] | -1 pts [-8, +4] | -6 pts [-12, -1] | -3 pts [-8, +3] | -4 pts [-10, +1] | -2 pts [-8, +4] | -1 pts [-6, +4] |
| Masked correctness: different category (% of set A questions) | 13% [7, 19] | 17% [11, 24] | 13% [8, 20] | 19% [12, 27] | 15% [10, 21] | 16% [10, 23] | 15% [9, 21] | 13% [8, 20] | +4 pts [-1, +9] | +1 pts [-5, +7] | +6 pts [+1, +12] | +2 pts [-4, +7] | +4 pts [-2, +9] | +2 pts [-4, +8] | +1 pts [-4, +6] |
| Masked correctness: not comparable (% of set A questions) | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 0% [0, 0] | 1% [0, 2] | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | +0 pts [+0, +0] | +1 pts [+0, +2] | +0 pts [+0, +0] | +1 pts [+0, +2] | +1 pts [+0, +2] | +0 pts [+0, +0] | +0 pts [+0, +0] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 0% [0, 0] | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | +1 pts [+0, +2] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] |

## Set B only (value never stated; factual consistency)

| Metric | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | openrouter_google | openrouter_openai | gemini_knowledge | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current | openrouter_google − current | openrouter_openai − current | gemini_knowledge − current |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 7.62 [7.39, 7.80] | 7.79 [7.63, 7.92] | 7.59 [7.38, 7.76] | 7.52 [7.32, 7.71] | 7.69 [7.52, 7.83] | 4.36 [4.15, 4.56] | 3.56 [3.32, 3.79] | 0.97 [0.94, 0.99] | +0.18 [+0.00, +0.36] | -0.03 [-0.25, +0.19] | -0.10 [-0.34, +0.16] | +0.07 [-0.11, +0.28] | -3.25 [-3.51, -3.00] | -4.06 [-4.34, -3.78] | -6.65 [-6.83, -6.43] |
| Questions answered from literature | 84% [80, 88] | 84% [79, 88] | 53% [47, 59] | 78% [73, 83] | 93% [89, 96] | 78% [73, 83] | 71% [64, 76] | 94% [91, 97] | +0 pts [-6, +6] | -31 pts [-38, -24] | -6 pts [-12, +0] | +8 pts [+4, +14] | -6 pts [-13, +0] | -14 pts [-20, -7] | +10 pts [+5, +15] |
| Questions answered with a best guess (documents gave no usable basis) | 11% [8, 15] | 13% [9, 18] | 43% [37, 49] | 18% [13, 24] | 5% [2, 7] | 19% [14, 23] | 25% [20, 31] | 3% [1, 5] | +2 pts [-4, +8] | +32 pts [+25, +39] | +7 pts [+1, +14] | -6 pts [-11, -2] | +8 pts [+1, +14] | +14 pts [+8, +20] | -8 pts [-13, -4] |
| Factual consistency: consistent (% of set B questions) | 95% [92, 98] | 97% [95, 99] | 96% [93, 98] | 96% [94, 98] | 97% [95, 99] | 97% [94, 99] | 96% [93, 98] | 97% [94, 99] | +2 pts [-0, +4] | +1 pts [-2, +3] | +1 pts [-2, +4] | +2 pts [+0, +5] | +1 pts [-1, +4] | +0 pts [-2, +3] | +1 pts [-1, +4] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 0] | 0% [0, 1] | 0% [0, 0] | 0% [0, 1] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | +0 pts [+0, +1] | +0 pts [+0, +0] | +0 pts [+0, +1] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 5% [2, 8] | 3% [1, 5] | 4% [2, 7] | 3% [1, 6] | 3% [1, 5] | 3% [1, 6] | 4% [2, 7] | 3% [1, 6] | -2 pts [-5, +0] | -1 pts [-3, +2] | -1 pts [-4, +1] | -2 pts [-5, +0] | -1 pts [-4, +1] | -0 pts [-3, +2] | -1 pts [-4, +1] |

## Cost

All questions that ran.

| Method | Questions | Retrieval (search fees + search model) | medsim LLM (Stages A–C) | Total | Total per question | Median wall time |
|---|---|---|---|---|---|---|
| current | 413 | $0.0000 | $0.4426 | $0.4426 | $0.00107 | 74.2 s |
| improved_1to4 | 413 | $0.0000 | $0.4164 | $0.4164 | $0.00101 | 81.0 s |
| openrouter_exa_instant | 413 | $2.8800 | $0.3779 | $3.2579 | $0.00789 | 62.1 s |
| openrouter_parallel_basic | 413 | $2.0680 | $0.4479 | $2.5160 | $0.00609 | 68.6 s |
| openrouter_perplexity | 413 | $2.0650 | $0.4048 | $2.4698 | $0.00598 | 64.5 s |
| openrouter_google | 413 | $20.6996 | $0.3867 | $21.0862 | $0.05106 | 71.4 s |
| openrouter_openai | 413 | $10.4466 | $0.3534 | $10.8001 | $0.02615 | 66.9 s |
| gemini_knowledge | 413 | $0.2954 | $0.3649 | $0.6604 | $0.00160 | 63.9 s |

## By subgroup (set A)

### Variable category

| Group | n | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: exact (% of set A questions) — openrouter_google | Masked correctness: exact (% of set A questions) — openrouter_openai | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — openrouter_google | Masked correctness: different category (% of set A questions) — openrouter_openai | Masked correctness: different category (% of set A questions) — gemini_knowledge |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| anthropometric | 22 | 45% | 55% | 55% | 45% | 45% | 50% | 50% | 59% | 9% | 9% | 5% | 18% | 9% | 5% | 9% | 5% |
| laboratory | 77 | 29% | 26% | 27% | 27% | 32% | 35% | 31% | 30% | 12% | 14% | 16% | 13% | 9% | 12% | 13% | 14% |
| vital_sign | 42 | 67% | 48% | 64% | 38% | 48% | 48% | 57% | 60% | 17% | 26% | 14% | 31% | 29% | 31% | 21% | 17% |

### True value (judge's category)

| Group | n | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: exact (% of set A questions) — openrouter_google | Masked correctness: exact (% of set A questions) — openrouter_openai | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — openrouter_google | Masked correctness: different category (% of set A questions) — openrouter_openai | Masked correctness: different category (% of set A questions) — gemini_knowledge |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| high | 73 | 34% | 30% | 31% | 27% | 31% | 34% | 35% | 35% | 14% | 18% | 16% | 19% | 13% | 15% | 18% | 14% |
| low | 33 | 52% | 39% | 45% | 27% | 44% | 55% | 42% | 48% | 3% | 6% | 6% | 13% | 9% | 10% | 6% | 3% |
| normal | 43 | 53% | 50% | 62% | 46% | 49% | 41% | 53% | 52% | 16% | 25% | 13% | 26% | 23% | 24% | 18% | 20% |
| not_applicable | 3 | 0% | 50% | 0% | 100% | 67% | 100% | 100% | 100% | 100% | 50% | 100% | 0% | 33% | 0% | 0% | 0% |
| unknown | 1 | – | 0% | – | – | – | – | – | – | – | 0% | – | – | – | – | – | – |

### Variable typical of the diagnosis

| Group | n | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: exact (% of set A questions) — openrouter_google | Masked correctness: exact (% of set A questions) — openrouter_openai | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — openrouter_google | Masked correctness: different category (% of set A questions) — openrouter_openai | Masked correctness: different category (% of set A questions) — gemini_knowledge |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| no | 83 | 43% | 40% | 46% | 37% | 45% | 45% | 42% | 47% | 19% | 24% | 17% | 25% | 22% | 25% | 19% | 18% |
| yes | 58 | 41% | 33% | 38% | 28% | 31% | 36% | 41% | 38% | 3% | 7% | 9% | 10% | 5% | 3% | 9% | 7% |

## Diagnostics

- **current:** answer paths {'literature': 357, 'best_guess': 41, 'case_study': 2, 'query_builder_declined': 13}; source article removed for 50 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **improved_1to4:** answer paths {'literature': 360, 'best_guess': 43, 'case_study': 2, 'off_topic': 2, 'query_builder_declined': 6}; source article removed for 57 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_exa_instant:** answer paths {'best_guess': 137, 'literature': 264, 'case_study': 1, 'query_builder_declined': 10, 'off_topic': 1}; source article removed for 47 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_parallel_basic:** answer paths {'best_guess': 62, 'literature': 342, 'query_builder_declined': 8, 'off_topic': 1}; source article removed for 38 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_perplexity:** answer paths {'best_guess': 16, 'literature': 388, 'case_study': 2, 'query_builder_declined': 7}; source article removed for 35 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_google:** answer paths {'literature': 340, 'best_guess': 63, 'case_study': 1, 'query_builder_declined': 8, 'off_topic': 1}; source article removed for 43 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_openai:** answer paths {'literature': 320, 'best_guess': 80, 'case_study': 1, 'query_builder_declined': 12}; source article removed for 47 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **gemini_knowledge:** answer paths {'literature': 389, 'best_guess': 13, 'case_study': 2, 'query_builder_declined': 9}; source article removed for 0 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **Masked correctness:** 3 of 1127 voted labels were "not comparable" (reported as their own label).
- **Judge errors (all attempts, all judges):** 0 judgment(s) failed; rerun the judge step to retry them.

## Judge panel agreement

| Metric | Answers | Unanimous | Majority | Tie broken by the main judge | Tie broken by the next judge | Fewer than all votes |
|---|---|---|---|---|---|---|
| masked correctness | 1127 | 74% | 25% | 1% | 0% | 0 |
| factual consistency | 2099 | 99% | 1% | 0% | 0% | 0 |

- **masked correctness, `google/gemini-3.5-flash-lite` vs `qwen/qwen3.8-flash`:** 897/1127 identical labels, Cohen's κ = 0.67.
- **masked correctness, `google/gemini-3.5-flash-lite` vs `openai/gpt-6-luna`:** 868/1127 identical labels, Cohen's κ = 0.63.
- **masked correctness, `qwen/qwen3.8-flash` vs `openai/gpt-6-luna`:** 1029/1127 identical labels, Cohen's κ = 0.86.
- **factual consistency, `google/gemini-3.5-flash-lite` vs `qwen/qwen3.8-flash`:** 2088/2099 identical labels, Cohen's κ = -0.00.
- **factual consistency, `google/gemini-3.5-flash-lite` vs `openai/gpt-6-luna`:** 2092/2099 identical labels, Cohen's κ = 0.22.
- **factual consistency, `qwen/qwen3.8-flash` vs `openai/gpt-6-luna`:** 2095/2099 identical labels, Cohen's κ = 0.33.

## Benchmark spend

| Step | Cost (USD, OpenRouter usage.cost) |
|---|---|
| extract (case facts) | $0.0000 |
| redact + Stage A checks (accepted) | $0.0000 |
| redact + Stage A checks (rejected) | $0.0000 |
| run (all methods; search fees included) | $41.6492 |
| judge: masked correctness (google/gemini-3.5-flash-lite) | $0.6237 |
| judge: masked correctness (openai/gpt-6-luna) | $0.2191 |
| judge: masked correctness (qwen/qwen3.8-flash) | $0.4465 |
| judge: factual consistency (google/gemini-3.5-flash-lite) | $0.9288 |
| judge: factual consistency (openai/gpt-6-luna) | $0.2633 |
| judge: factual consistency (qwen/qwen3.8-flash) | $0.3883 |
| validation: controls (panel) | $0.0000 |
| validation: flipped truth (panel) | $0.0000 |
| **total** | **$44.5189** |

Cross-check: the OpenRouter key's usage counter, read right after each of the 13 benchmark commands, rose by $46.0167. The counter lags behind requests, so this undercounts; per-call usage.cost above is the accounting source.

