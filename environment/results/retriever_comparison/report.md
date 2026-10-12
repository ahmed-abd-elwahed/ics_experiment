# Retrieval benchmark report

- Workspace: `environment/results/retriever_comparison`
- Judge panel: `anthropic/claude-haiku-5.5`, `z-ai/glm-5.3-flash`, `openai/gpt-6-luna`. Each answer's label is the panel's majority vote; with no majority, the first (main) judge's label decides.
- medsim models: `deepseek/deepseek-v4-flash-0731`
- `current`: Europe PMC + LitSense passages, relaxation ladders, lexical rerank (the original method)
- `gemini_knowledge`: no search: google/gemini-3-flash-preview is the source, given the question, the case information (as medsim sees it), and the diagnosis, and asked for the value that typically fits; medsim's stages as usual
- `improved_1to4`: changes 1-4: value-first ranking in one list across sources, 50 Europe PMC candidates, animal/age filter, article-body search with excerpts, value-based broadening without the unhelpful rungs (medsim's default since they were measured)
- `openrouter_exa_instant`: openrouter_search with the Exa engine in instant mode; deepseek/deepseek-v4.1-flash issues the search
- `openrouter_google`: openrouter_search with the model's native search, Google Search for google/gemini-3.1-flash-lite, which issues the search
- `openrouter_openai`: openrouter_search with the model's native search, OpenAI web search for openai/gpt-6-luna, which issues the search
- `openrouter_parallel_basic`: openrouter_search with the Parallel engine in basic mode; deepseek/deepseek-v4.1-flash issues the search
- `openrouter_perplexity`: openrouter_search with the Perplexity engine; deepseek/deepseek-v4.1-flash issues the search

## Question sets

- Cases extracted: 272; measured values found: 1235; eligible as hidden values: 536.
- Set A (hidden value): 141 questions accepted; rejected 0 (none).
- Set B (value never stated): 272 questions accepted; rejected 0 (none).
- Every question is scored under every method: each label's percentage is out of all questions in its set. Questions without a successful run (counted as no label): current: 0, gemini_knowledge: 0, improved_1to4: 0, openrouter_exa_instant: 0, openrouter_google: 0, openrouter_openai: 0, openrouter_parallel_basic: 0, openrouter_perplexity: 0.

## All questions (sets A, B)

| Metric | current | gemini_knowledge | improved_1to4 | openrouter_exa_instant | openrouter_google | openrouter_openai | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_google − current | openrouter_openai − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 7.71 [7.55, 7.84] | 0.97 [0.96, 0.99] | 7.81 [7.68, 7.92] | 7.65 [7.50, 7.78] | 4.44 [4.26, 4.61] | 3.78 [3.56, 4.00] | 7.61 [7.47, 7.73] | 7.67 [7.54, 7.79] | -6.74 [-6.86, -6.59] | +0.10 [-0.04, +0.25] | -0.06 [-0.22, +0.11] | -3.27 [-3.48, -3.07] | -3.92 [-4.17, -3.66] | -0.10 [-0.28, +0.08] | -0.04 [-0.17, +0.11] |
| Questions answered from literature | 86% [83, 90] | 94% [92, 96] | 87% [84, 90] | 64% [58, 69] | 82% [78, 86] | 77% [73, 82] | 83% [79, 87] | 94% [91, 96] | +8 pts [+4, +12] | +1 pts [-4, +5] | -23 pts [-28, -17] | -4 pts [-9, +1] | -9 pts [-14, -4] | -4 pts [-9, +1] | +8 pts [+3, +12] |
| Questions answered with a best guess (documents gave no usable basis) | 10% [7, 13] | 3% [2, 5] | 10% [7, 14] | 33% [28, 38] | 15% [11, 19] | 19% [15, 24] | 15% [11, 19] | 4% [2, 6] | -7 pts [-11, -3] | +0 pts [-4, +5] | +23 pts [+17, +29] | +5 pts [+0, +10] | +9 pts [+5, +14] | +5 pts [+0, +10] | -6 pts [-10, -2] |
| Masked correctness: exact (% of set A questions) | 47% [38, 56] | 46% [37, 55] | 41% [33, 50] | 43% [34, 53] | 45% [36, 54] | 44% [35, 53] | 38% [29, 46] | 42% [33, 51] | -1 pts [-9, +7] | -6 pts [-13, +1] | -4 pts [-12, +6] | -2 pts [-11, +6] | -3 pts [-10, +5] | -9 pts [-17, -1] | -5 pts [-14, +4] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 85% [78, 91] | 87% [81, 93] | 83% [76, 89] | 84% [78, 90] | 82% [75, 89] | 84% [78, 90] | 82% [75, 89] | 84% [77, 89] | +2 pts [-3, +8] | -2 pts [-7, +3] | -1 pts [-7, +5] | -3 pts [-9, +3] | -1 pts [-6, +5] | -3 pts [-9, +3] | -1 pts [-7, +4] |
| Masked correctness: different category (% of set A questions) | 15% [9, 21] | 13% [7, 19] | 16% [11, 23] | 15% [9, 22] | 17% [11, 24] | 16% [10, 22] | 18% [11, 25] | 16% [11, 23] | -2 pts [-8, +3] | +1 pts [-3, +6] | +0 pts [-6, +6] | +2 pts [-4, +9] | +1 pts [-5, +6] | +3 pts [-3, +9] | +1 pts [-4, +7] |
| Masked correctness: not comparable (% of set A questions) | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +1 pts [+0, +2] | +1 pts [+0, +2] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | +0 pts [+0, +0] | +1 pts [+0, +2] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] |
| Factual consistency: consistent (% of set B questions) | 95% [92, 98] | 97% [94, 99] | 97% [94, 99] | 96% [93, 98] | 97% [94, 99] | 96% [93, 98] | 96% [93, 98] | 97% [95, 99] | +1 pts [-1, +4] | +1 pts [-1, +4] | +1 pts [-2, +3] | +1 pts [-1, +4] | +0 pts [-2, +3] | +0 pts [-3, +4] | +2 pts [+0, +5] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 1% [0, 3] | 0% [0, 0] | +0 pts [+0, +0] | +1 pts [+0, +2] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +1 pts [+0, +3] | +0 pts [+0, +0] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 5% [2, 8] | 3% [1, 6] | 3% [1, 5] | 4% [2, 7] | 3% [1, 6] | 4% [2, 7] | 3% [1, 6] | 3% [1, 5] | -1 pts [-4, +1] | -2 pts [-5, +0] | -1 pts [-3, +2] | -1 pts [-4, +1] | -0 pts [-3, +2] | -1 pts [-4, +1] | -2 pts [-5, +0] |
| Retrieval cost per question (search fees, search/rerank LLM; USD) | $0.00000 | $0.00072 | $0.00000 | $0.00697 | $0.05012 | $0.02529 | $0.00501 | $0.00500 | +0.00072 [+0.00070, +0.00073] | +0.00000 [+0.00000, +0.00000] | +0.00697 [+0.00688, +0.00706] | +0.05012 [+0.04907, +0.05114] | +0.02529 [+0.02399, +0.02660] | +0.00501 [+0.00494, +0.00507] | +0.00500 [+0.00493, +0.00506] |
| medsim LLM cost per question (Stages A–C, USD) | $0.00107 | $0.00088 | $0.00101 | $0.00091 | $0.00094 | $0.00086 | $0.00108 | $0.00098 | -0.00019 [-0.00028, -0.00010] | -0.00006 [-0.00014, +0.00002] | -0.00016 [-0.00025, -0.00007] | -0.00014 [-0.00022, -0.00006] | -0.00022 [-0.00029, -0.00014] | +0.00001 [-0.00008, +0.00010] | -0.00009 [-0.00017, -0.00002] |
| Total cost per question (USD) | $0.00107 | $0.00160 | $0.00101 | $0.00789 | $0.05106 | $0.02615 | $0.00609 | $0.00598 | +0.00053 [+0.00044, +0.00061] | -0.00006 [-0.00014, +0.00002] | +0.00682 [+0.00669, +0.00694] | +0.04998 [+0.04895, +0.05101] | +0.02508 [+0.02377, +0.02640] | +0.00502 [+0.00491, +0.00513] | +0.00491 [+0.00481, +0.00501] |
| Wall time per question (s) | 86.1 [80.2, 92.4] | 72.8 [69.8, 76.3] | 94.3 [89.0, 100.5] | 74.2 [70.1, 78.8] | 82.4 [77.6, 87.6] | 79.9 [75.0, 85.3] | 84.2 [78.6, 90.4] | 78.8 [73.9, 84.1] | -13.22 [-19.55, -7.13] | +8.25 [+2.24, +14.30] | -11.85 [-18.05, -5.92] | -3.64 [-10.86, +3.05] | -6.13 [-12.52, -0.14] | -1.82 [-7.76, +3.77] | -7.27 [-13.43, -1.65] |
| Time outside medsim's LLM calls per question (≈ retrieval; s) | 10.36 [9.45, 11.34] | 4.76 [4.35, 5.29] | 21.03 [19.26, 23.02] | 5.96 [5.52, 6.56] | 11.05 [10.55, 11.59] | 13.38 [12.49, 14.55] | 6.61 [6.30, 6.92] | 6.36 [6.05, 6.68] | -5.60 [-6.70, -4.62] | +10.67 [+9.20, +12.29] | -4.40 [-5.51, -3.32] | +0.69 [-0.32, +1.60] | +3.02 [+1.70, +4.42] | -3.75 [-4.75, -2.82] | -4.00 [-5.00, -3.10] |

## Set A only (hidden value; masked correctness)

| Metric | current | gemini_knowledge | improved_1to4 | openrouter_exa_instant | openrouter_google | openrouter_openai | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_google − current | openrouter_openai − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 7.89 [7.72, 8.00] | 0.99 [0.96, 1.00] | 7.83 [7.63, 8.00] | 7.77 [7.62, 7.88] | 4.58 [4.28, 4.88] | 4.22 [3.84, 4.60] | 7.77 [7.69, 7.85] | 7.64 [7.42, 7.81] | -6.90 [-7.01, -6.74] | -0.06 [-0.33, +0.18] | -0.12 [-0.33, +0.09] | -3.30 [-3.62, -2.99] | -3.67 [-4.10, -3.25] | -0.11 [-0.27, +0.08] | -0.25 [-0.43, -0.07] |
| Questions answered from literature | 91% [85, 96] | 95% [91, 98] | 93% [88, 97] | 85% [79, 91] | 91% [86, 95] | 91% [85, 96] | 91% [86, 96] | 96% [93, 99] | +4 pts [-2, +10] | +2 pts [-5, +9] | -6 pts [-14, +2] | +0 pts [-6, +7] | +0 pts [-6, +7] | +1 pts [-7, +8] | +6 pts [-1, +12] |
| Questions answered with a best guess (documents gave no usable basis) | 8% [3, 13] | 4% [1, 7] | 5% [2, 9] | 14% [9, 20] | 9% [4, 14] | 9% [4, 14] | 9% [4, 13] | 2% [0, 6] | -4 pts [-10, +1] | -3 pts [-9, +3] | +6 pts [-1, +14] | +1 pts [-6, +7] | +1 pts [-6, +7] | +1 pts [-6, +8] | -6 pts [-12, +1] |
| Masked correctness: exact (% of set A questions) | 47% [38, 56] | 46% [37, 55] | 41% [33, 50] | 43% [34, 53] | 45% [36, 54] | 44% [35, 53] | 38% [29, 46] | 42% [33, 51] | -1 pts [-9, +7] | -6 pts [-13, +1] | -4 pts [-12, +6] | -2 pts [-11, +6] | -3 pts [-10, +5] | -9 pts [-17, -1] | -5 pts [-14, +4] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 85% [78, 91] | 87% [81, 93] | 83% [76, 89] | 84% [78, 90] | 82% [75, 89] | 84% [78, 90] | 82% [75, 89] | 84% [77, 89] | +2 pts [-3, +8] | -2 pts [-7, +3] | -1 pts [-7, +5] | -3 pts [-9, +3] | -1 pts [-6, +5] | -3 pts [-9, +3] | -1 pts [-7, +4] |
| Masked correctness: different category (% of set A questions) | 15% [9, 21] | 13% [7, 19] | 16% [11, 23] | 15% [9, 22] | 17% [11, 24] | 16% [10, 22] | 18% [11, 25] | 16% [11, 23] | -2 pts [-8, +3] | +1 pts [-3, +6] | +0 pts [-6, +6] | +2 pts [-4, +9] | +1 pts [-5, +6] | +3 pts [-3, +9] | +1 pts [-4, +7] |
| Masked correctness: not comparable (% of set A questions) | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +1 pts [+0, +2] | +1 pts [+0, +2] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | +0 pts [+0, +0] | +1 pts [+0, +2] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] |

## Set B only (value never stated; factual consistency)

| Metric | current | gemini_knowledge | improved_1to4 | openrouter_exa_instant | openrouter_google | openrouter_openai | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_google − current | openrouter_openai − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 7.62 [7.39, 7.80] | 0.97 [0.94, 0.99] | 7.79 [7.63, 7.92] | 7.59 [7.38, 7.76] | 4.36 [4.15, 4.56] | 3.56 [3.32, 3.79] | 7.52 [7.32, 7.71] | 7.69 [7.52, 7.83] | -6.65 [-6.83, -6.43] | +0.18 [+0.00, +0.36] | -0.03 [-0.25, +0.19] | -3.25 [-3.51, -3.00] | -4.06 [-4.34, -3.78] | -0.10 [-0.34, +0.16] | +0.07 [-0.11, +0.28] |
| Questions answered from literature | 84% [80, 88] | 94% [91, 97] | 84% [79, 88] | 53% [47, 59] | 78% [73, 83] | 71% [64, 76] | 78% [73, 83] | 93% [89, 96] | +10 pts [+5, +15] | +0 pts [-6, +6] | -31 pts [-38, -24] | -6 pts [-13, +0] | -14 pts [-20, -7] | -6 pts [-12, +0] | +8 pts [+4, +14] |
| Questions answered with a best guess (documents gave no usable basis) | 11% [8, 15] | 3% [1, 5] | 13% [9, 18] | 43% [37, 49] | 19% [14, 23] | 25% [20, 31] | 18% [13, 24] | 5% [2, 7] | -8 pts [-13, -4] | +2 pts [-4, +8] | +32 pts [+25, +39] | +8 pts [+1, +14] | +14 pts [+8, +20] | +7 pts [+1, +14] | -6 pts [-11, -2] |
| Factual consistency: consistent (% of set B questions) | 95% [92, 98] | 97% [94, 99] | 97% [94, 99] | 96% [93, 98] | 97% [94, 99] | 96% [93, 98] | 96% [93, 98] | 97% [95, 99] | +1 pts [-1, +4] | +1 pts [-1, +4] | +1 pts [-2, +3] | +1 pts [-1, +4] | +0 pts [-2, +3] | +0 pts [-3, +4] | +2 pts [+0, +5] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 1% [0, 3] | 0% [0, 0] | +0 pts [+0, +0] | +1 pts [+0, +2] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +1 pts [+0, +3] | +0 pts [+0, +0] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 5% [2, 8] | 3% [1, 6] | 3% [1, 5] | 4% [2, 7] | 3% [1, 6] | 4% [2, 7] | 3% [1, 6] | 3% [1, 5] | -1 pts [-4, +1] | -2 pts [-5, +0] | -1 pts [-3, +2] | -1 pts [-4, +1] | -0 pts [-3, +2] | -1 pts [-4, +1] | -2 pts [-5, +0] |

## Cost

All questions that ran.

| Method | Questions | Retrieval (search fees + search model) | medsim LLM (Stages A–C) | Total | Total per question | Median wall time |
|---|---|---|---|---|---|---|
| current | 413 | $0.0000 | $0.4426 | $0.4426 | $0.00107 | 74.2 s |
| gemini_knowledge | 413 | $0.2954 | $0.3649 | $0.6604 | $0.00160 | 63.9 s |
| improved_1to4 | 413 | $0.0000 | $0.4164 | $0.4164 | $0.00101 | 81.0 s |
| openrouter_exa_instant | 413 | $2.8800 | $0.3779 | $3.2579 | $0.00789 | 62.1 s |
| openrouter_google | 413 | $20.6996 | $0.3867 | $21.0862 | $0.05106 | 71.4 s |
| openrouter_openai | 413 | $10.4466 | $0.3534 | $10.8001 | $0.02615 | 66.9 s |
| openrouter_parallel_basic | 413 | $2.0680 | $0.4479 | $2.5160 | $0.00609 | 68.6 s |
| openrouter_perplexity | 413 | $2.0650 | $0.4048 | $2.4698 | $0.00598 | 64.5 s |

## By subgroup (set A)

### Variable category

| Group | n | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_google | Masked correctness: exact (% of set A questions) — openrouter_openai | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_google | Masked correctness: different category (% of set A questions) — openrouter_openai | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| anthropometric | 22 | 45% | 59% | 55% | 55% | 59% | 50% | 50% | 45% | 9% | 5% | 9% | 5% | 9% | 9% | 18% | 14% |
| laboratory | 77 | 36% | 32% | 30% | 27% | 36% | 31% | 29% | 32% | 13% | 16% | 14% | 17% | 12% | 14% | 12% | 10% |
| vital_sign | 42 | 67% | 64% | 55% | 67% | 52% | 64% | 48% | 57% | 21% | 12% | 24% | 17% | 31% | 21% | 29% | 29% |

### True value (judge's category)

| Group | n | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_google | Masked correctness: exact (% of set A questions) — openrouter_openai | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_google | Masked correctness: different category (% of set A questions) — openrouter_openai | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| high | 73 | 41% | 36% | 31% | 33% | 36% | 35% | 32% | 34% | 17% | 17% | 19% | 17% | 16% | 19% | 15% | 14% |
| low | 34 | 56% | 45% | 45% | 45% | 55% | 48% | 32% | 48% | 6% | 6% | 3% | 12% | 9% | 6% | 15% | 9% |
| normal | 40 | 50% | 60% | 54% | 59% | 49% | 57% | 50% | 50% | 18% | 11% | 26% | 14% | 29% | 17% | 26% | 25% |
| not_applicable | 4 | 50% | 100% | 100% | 100% | 100% | 100% | 100% | 50% | 50% | 0% | 0% | 0% | 0% | 0% | 0% | 50% |
| unknown | 1 | – | – | 0% | – | – | – | – | – | – | – | 0% | – | – | – | – | – |

### Variable typical of the diagnosis

| Group | n | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_google | Masked correctness: exact (% of set A questions) — openrouter_openai | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_google | Masked correctness: different category (% of set A questions) — openrouter_openai | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| no | 83 | 43% | 49% | 42% | 47% | 48% | 47% | 41% | 48% | 23% | 17% | 23% | 19% | 25% | 22% | 24% | 22% |
| yes | 58 | 52% | 41% | 40% | 38% | 40% | 40% | 33% | 33% | 3% | 7% | 7% | 9% | 5% | 7% | 9% | 9% |

## Diagnostics

- **current:** answer paths {'literature': 357, 'best_guess': 41, 'case_study': 2, 'query_builder_declined': 13}; source article removed for 50 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **gemini_knowledge:** answer paths {'literature': 389, 'best_guess': 13, 'case_study': 2, 'query_builder_declined': 9}; source article removed for 0 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **improved_1to4:** answer paths {'literature': 360, 'best_guess': 43, 'case_study': 2, 'off_topic': 2, 'query_builder_declined': 6}; source article removed for 57 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_exa_instant:** answer paths {'best_guess': 137, 'literature': 264, 'case_study': 1, 'query_builder_declined': 10, 'off_topic': 1}; source article removed for 47 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_google:** answer paths {'literature': 340, 'best_guess': 63, 'case_study': 1, 'query_builder_declined': 8, 'off_topic': 1}; source article removed for 43 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_openai:** answer paths {'literature': 320, 'best_guess': 80, 'case_study': 1, 'query_builder_declined': 12}; source article removed for 47 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_parallel_basic:** answer paths {'best_guess': 62, 'literature': 342, 'query_builder_declined': 8, 'off_topic': 1}; source article removed for 38 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_perplexity:** answer paths {'best_guess': 16, 'literature': 388, 'case_study': 2, 'query_builder_declined': 7}; source article removed for 35 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **Masked correctness:** 2 of 1127 voted labels were "not comparable" (reported as their own label).
- **Judge errors (all attempts, all judges):** 0 judgment(s) failed; rerun the judge step to retry them.

## Judge panel agreement

| Metric | Answers | Unanimous | Majority | Tie broken by the main judge | Tie broken by the next judge | Fewer than all votes |
|---|---|---|---|---|---|---|
| masked correctness | 1127 | 82% | 17% | 1% | 0% | 0 |
| factual consistency | 2099 | 99% | 1% | 0% | 0% | 0 |

- **masked correctness, `anthropic/claude-haiku-5.5` vs `z-ai/glm-5.3-flash`:** 994/1127 identical labels, Cohen's κ = 0.81.
- **masked correctness, `anthropic/claude-haiku-5.5` vs `openai/gpt-6-luna`:** 967/1127 identical labels, Cohen's κ = 0.77.
- **masked correctness, `z-ai/glm-5.3-flash` vs `openai/gpt-6-luna`:** 1005/1127 identical labels, Cohen's κ = 0.83.
- **factual consistency, `anthropic/claude-haiku-5.5` vs `z-ai/glm-5.3-flash`:** 2088/2099 identical labels, Cohen's κ = 0.47.
- **factual consistency, `anthropic/claude-haiku-5.5` vs `openai/gpt-6-luna`:** 2085/2099 identical labels, Cohen's κ = 0.12.
- **factual consistency, `z-ai/glm-5.3-flash` vs `openai/gpt-6-luna`:** 2092/2099 identical labels, Cohen's κ = 0.22.

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
| judge: masked correctness (z-ai/glm-5.3-flash) | $0.2015 |
| judge: masked correctness (anthropic/claude-haiku-5.5) | $0.3099 |
| judge: masked correctness (typesafe/jev-1.13) | $0.0473 |
| judge: factual consistency (google/gemini-3.5-flash-lite) | $0.9288 |
| judge: factual consistency (openai/gpt-6-luna) | $0.2633 |
| judge: factual consistency (qwen/qwen3.8-flash) | $0.3883 |
| judge: factual consistency (anthropic/claude-haiku-5.5) | $0.4230 |
| judge: factual consistency (z-ai/glm-5.3-flash) | $0.2304 |
| judge: factual consistency (typesafe/jev-1.13) | $0.0738 |
| validation: controls (panel) | $0.0000 |
| validation: flipped truth (panel) | $0.0000 |
| **total** | **$45.8048** |

Cross-check: the OpenRouter key's usage counter, read right after each of the 15 benchmark commands, rose by $48.3180. The counter lags behind requests, so this undercounts; per-call usage.cost above is the accounting source.

