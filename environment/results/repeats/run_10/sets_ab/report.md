# Retrieval benchmark report

- Workspace: `environment/results/repeats/run_10/sets_ab`
- Judge panel: `anthropic/claude-haiku-5.5`, `z-ai/glm-5.3-flash`, `openai/gpt-6-luna`. Each answer's label is the panel's majority vote; with no majority, the first (main) judge's label decides.
- `gemini_knowledge`: no search: google/gemini-3-flash-preview is the source, given the question, the case information (as medsim sees it), and the diagnosis, and asked for the value that typically fits; medsim's stages as usual
- `current`: Europe PMC + LitSense passages, relaxation ladders, lexical rerank (the original method)
- `improved_1to4`: changes 1-4: value-first ranking in one list across sources, 50 Europe PMC candidates, animal/age filter, article-body search with excerpts, value-based broadening without the unhelpful rungs (medsim's default since they were measured)
- `openrouter_exa_instant`: openrouter_search with the Exa engine in instant mode; deepseek/deepseek-v4.1-flash issues the search
- `openrouter_parallel_basic`: openrouter_search with the Parallel engine in basic mode; deepseek/deepseek-v4.1-flash issues the search
- `openrouter_perplexity`: openrouter_search with the Perplexity engine; deepseek/deepseek-v4.1-flash issues the search

## Question sets

- Cases extracted: 272; measured values found: 1235; eligible as hidden values: 536.
- Set A (hidden value): 141 questions accepted; rejected 0 (none).
- Set B (value never stated): 272 questions accepted; rejected 0 (none).
- Every question is scored under every method: each label's percentage is out of all questions in its set. Questions without a successful run (counted as no label): gemini_knowledge: 0, current: 0, improved_1to4: 0, openrouter_exa_instant: 0, openrouter_parallel_basic: 0, openrouter_perplexity: 0.

## All questions (sets A, B)

| Metric | gemini_knowledge | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 0.98 [0.96, 0.99] | 7.88 [7.78, 7.96] | 7.75 [7.60, 7.87] | 7.69 [7.54, 7.81] | 7.72 [7.61, 7.82] | 7.62 [7.47, 7.74] | -6.91 [-6.98, -6.81] | -0.14 [-0.26, -0.04] | -0.19 [-0.35, -0.07] | -0.16 [-0.28, -0.04] | -0.27 [-0.39, -0.16] |
| Questions answered from literature | 94% [92, 96] | 30% [25, 34] | 48% [43, 53] | 31% [25, 36] | 34% [30, 39] | 62% [57, 67] | +64 pts [+59, +69] | +18 pts [+12, +24] | +1 pts [-5, +6] | +4 pts [-2, +10] | +32 pts [+26, +38] |
| Questions answered with a best guess (documents gave no usable basis) | 4% [2, 6] | 69% [64, 73] | 49% [44, 54] | 67% [61, 72] | 64% [60, 69] | 35% [31, 40] | -65 pts [-70, -60] | -20 pts [-26, -14] | -1 pts [-7, +4] | -4 pts [-10, +2] | -33 pts [-39, -27] |
| Masked correctness: exact (% of set A questions) | 44% [35, 52] | 48% [39, 57] | 42% [33, 51] | 50% [41, 59] | 41% [32, 50] | 41% [33, 50] | -4 pts [-11, +4] | -6 pts [-12, +1] | +2 pts [-5, +10] | -6 pts [-15, +2] | -6 pts [-14, +1] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 85% [78, 91] | 84% [77, 90] | 86% [79, 91] | 84% [78, 90] | 87% [82, 92] | 81% [73, 88] | +1 pts [-5, +6] | +1 pts [-3, +6] | +0 pts [-5, +5] | +3 pts [-3, +9] | -4 pts [-10, +3] |
| Masked correctness: different category (% of set A questions) | 13% [8, 20] | 15% [9, 22] | 13% [8, 20] | 15% [9, 21] | 12% [7, 18] | 19% [12, 27] | -1 pts [-7, +4] | -1 pts [-6, +3] | +0 pts [-5, +6] | -3 pts [-9, +3] | +4 pts [-2, +10] |
| Masked correctness: not comparable (% of set A questions) | 1% [0, 2] | 1% [0, 2] | 1% [0, 2] | 0% [0, 0] | 1% [0, 2] | 0% [0, 0] | +0 pts [+0, +0] | +0 pts [+0, +0] | -1 pts [-2, +0] | +0 pts [+0, +0] | -1 pts [-2, +0] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | +1 pts [+0, +2] | +0 pts [+0, +0] | +1 pts [+0, +2] | +0 pts [+0, +0] | +0 pts [+0, +0] |
| Factual consistency: consistent (% of set B questions) | 98% [96, 99] | 98% [96, 100] | 94% [91, 97] | 97% [94, 99] | 98% [96, 99] | 97% [94, 99] | -0 pts [-2, +1] | -4 pts [-7, -2] | -1 pts [-4, +1] | -0 pts [-3, +1] | -1 pts [-4, +1] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 0] | 0% [0, 1] | 2% [0, 4] | 0% [0, 1] | 0% [0, 1] | 0% [0, 1] | -0 pts [-1, +0] | +1 pts [+0, +3] | +0 pts [-1, +1] | +0 pts [-1, +1] | +0 pts [-1, +1] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 2% [1, 4] | 1% [0, 3] | 4% [2, 6] | 3% [1, 5] | 2% [0, 4] | 3% [1, 5] | +1 pts [-1, +3] | +3 pts [+1, +5] | +1 pts [-0, +4] | +0 pts [-1, +2] | +1 pts [-0, +4] |
| Retrieval cost per question (search fees, search/rerank LLM; USD) | $0.00072 | $0.00000 | $0.00000 | $0.00700 | $0.00511 | $0.00506 | +0.00072 [+0.00070, +0.00073] | +0.00000 [+0.00000, +0.00000] | +0.00700 [+0.00687, +0.00711] | +0.00511 [+0.00504, +0.00516] | +0.00506 [+0.00498, +0.00514] |
| medsim LLM cost per question (Stages A–C, USD) | $0.00230 | $0.00280 | $0.00314 | $0.00249 | $0.00260 | $0.00291 | -0.00050 [-0.00070, -0.00030] | +0.00034 [+0.00009, +0.00058] | -0.00031 [-0.00057, -0.00008] | -0.00020 [-0.00042, +0.00001] | +0.00011 [-0.00016, +0.00037] |
| Total cost per question (USD) | $0.00302 | $0.00280 | $0.00314 | $0.00949 | $0.00771 | $0.00797 | +0.00022 [+0.00001, +0.00042] | +0.00034 [+0.00009, +0.00058] | +0.00669 [+0.00640, +0.00695] | +0.00491 [+0.00467, +0.00515] | +0.00517 [+0.00489, +0.00544] |
| Wall time per question (s) | 78.0 [73.9, 82.4] | 130.9 [123.8, 138.3] | 110.5 [104.6, 116.9] | 84.4 [79.4, 89.6] | 78.4 [74.2, 82.9] | 92.6 [86.5, 99.0] | -52.90 [-60.56, -45.20] | -20.39 [-28.58, -12.15] | -46.51 [-55.31, -38.15] | -52.45 [-60.09, -44.77] | -38.29 [-46.65, -29.58] |
| Time outside medsim's LLM calls per question (≈ retrieval; s) | 3.07 [3.02, 3.13] | 39.56 [36.44, 42.93] | 21.01 [19.68, 22.32] | 6.57 [6.24, 6.88] | 6.63 [6.30, 6.99] | 6.74 [6.36, 7.10] | -36.49 [-39.89, -33.35] | -18.55 [-21.63, -15.48] | -32.99 [-36.37, -29.78] | -32.93 [-36.28, -29.79] | -32.82 [-36.16, -29.63] |

## Set A only (hidden value; masked correctness)

| Metric | gemini_knowledge | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 0.99 [0.96, 1.00] | 7.83 [7.61, 8.00] | 7.94 [7.82, 8.00] | 7.78 [7.64, 7.89] | 7.78 [7.68, 7.86] | 7.57 [7.37, 7.75] | -6.84 [-7.01, -6.64] | +0.11 [+0.00, +0.29] | -0.05 [-0.26, +0.18] | -0.05 [-0.24, +0.17] | -0.26 [-0.38, -0.11] |
| Questions answered from literature | 96% [92, 99] | 32% [24, 41] | 53% [45, 61] | 37% [28, 47] | 38% [30, 45] | 61% [53, 70] | +64 pts [+54, +72] | +21 pts [+11, +31] | +5 pts [-5, +15] | +6 pts [-6, +16] | +29 pts [+19, +39] |
| Questions answered with a best guess (documents gave no usable basis) | 3% [1, 6] | 66% [57, 74] | 46% [38, 54] | 62% [53, 71] | 62% [55, 70] | 38% [29, 46] | -63 pts [-72, -54] | -20 pts [-29, -9] | -4 pts [-13, +6] | -4 pts [-14, +8] | -28 pts [-39, -18] |
| Masked correctness: exact (% of set A questions) | 44% [35, 52] | 48% [39, 57] | 42% [33, 51] | 50% [41, 59] | 41% [32, 50] | 41% [33, 50] | -4 pts [-11, +4] | -6 pts [-12, +1] | +2 pts [-5, +10] | -6 pts [-15, +2] | -6 pts [-14, +1] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 85% [78, 91] | 84% [77, 90] | 86% [79, 91] | 84% [78, 90] | 87% [82, 92] | 81% [73, 88] | +1 pts [-5, +6] | +1 pts [-3, +6] | +0 pts [-5, +5] | +3 pts [-3, +9] | -4 pts [-10, +3] |
| Masked correctness: different category (% of set A questions) | 13% [8, 20] | 15% [9, 22] | 13% [8, 20] | 15% [9, 21] | 12% [7, 18] | 19% [12, 27] | -1 pts [-7, +4] | -1 pts [-6, +3] | +0 pts [-5, +6] | -3 pts [-9, +3] | +4 pts [-2, +10] |
| Masked correctness: not comparable (% of set A questions) | 1% [0, 2] | 1% [0, 2] | 1% [0, 2] | 0% [0, 0] | 1% [0, 2] | 0% [0, 0] | +0 pts [+0, +0] | +0 pts [+0, +0] | -1 pts [-2, +0] | +0 pts [+0, +0] | -1 pts [-2, +0] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | +1 pts [+0, +2] | +0 pts [+0, +0] | +1 pts [+0, +2] | +0 pts [+0, +0] | +0 pts [+0, +0] |

## Set B only (value never stated; factual consistency)

| Metric | gemini_knowledge | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 0.97 [0.95, 0.99] | 7.91 [7.80, 8.00] | 7.65 [7.44, 7.82] | 7.64 [7.44, 7.81] | 7.69 [7.53, 7.83] | 7.64 [7.44, 7.80] | -6.94 [-7.02, -6.84] | -0.26 [-0.44, -0.12] | -0.27 [-0.45, -0.12] | -0.22 [-0.37, -0.09] | -0.27 [-0.44, -0.14] |
| Questions answered from literature | 93% [90, 96] | 29% [23, 34] | 46% [39, 52] | 27% [22, 33] | 32% [27, 38] | 63% [57, 68] | +65 pts [+59, +71] | +17 pts [+9, +24] | -1 pts [-8, +5] | +4 pts [-4, +11] | +34 pts [+27, +41] |
| Questions answered with a best guess (documents gave no usable basis) | 4% [2, 7] | 70% [64, 75] | 50% [44, 57] | 69% [63, 75] | 65% [60, 71] | 34% [29, 39] | -66 pts [-72, -60] | -20 pts [-27, -12] | -0 pts [-7, +6] | -4 pts [-12, +3] | -36 pts [-43, -28] |
| Factual consistency: consistent (% of set B questions) | 98% [96, 99] | 98% [96, 100] | 94% [91, 97] | 97% [94, 99] | 98% [96, 99] | 97% [94, 99] | -0 pts [-2, +1] | -4 pts [-7, -2] | -1 pts [-4, +1] | -0 pts [-3, +1] | -1 pts [-4, +1] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 0] | 0% [0, 1] | 2% [0, 4] | 0% [0, 1] | 0% [0, 1] | 0% [0, 1] | -0 pts [-1, +0] | +1 pts [+0, +3] | +0 pts [-1, +1] | +0 pts [-1, +1] | +0 pts [-1, +1] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 2% [1, 4] | 1% [0, 3] | 4% [2, 6] | 3% [1, 5] | 2% [0, 4] | 3% [1, 5] | +1 pts [-1, +3] | +3 pts [+1, +5] | +1 pts [-0, +4] | +0 pts [-1, +2] | +1 pts [-0, +4] |

## Cost

All questions that ran.

| Method | Questions | Retrieval (search fees + search model) | medsim LLM (Stages A–C) | Total | Total per question | Median wall time |
|---|---|---|---|---|---|---|
| gemini_knowledge | 413 | $0.2961 | $0.9505 | $1.2465 | $0.00302 | 67.8 s |
| current | 413 | $0.0000 | $1.1567 | $1.1567 | $0.00280 | 116.7 s |
| improved_1to4 | 413 | $0.0000 | $1.2961 | $1.2961 | $0.00314 | 94.4 s |
| openrouter_exa_instant | 413 | $2.8921 | $1.0276 | $3.9197 | $0.00949 | 75.0 s |
| openrouter_parallel_basic | 413 | $2.1107 | $1.0743 | $3.1851 | $0.00771 | 68.7 s |
| openrouter_perplexity | 413 | $2.0911 | $1.2008 | $3.2919 | $0.00797 | 77.6 s |

## By subgroup (set A)

### Variable category

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| anthropometric | 22 | 50% | 59% | 64% | 59% | 55% | 45% | 5% | 9% | 0% | 5% | 14% | 18% |
| laboratory | 77 | 32% | 38% | 30% | 36% | 27% | 30% | 16% | 12% | 12% | 14% | 8% | 17% |
| vital_sign | 42 | 62% | 60% | 52% | 69% | 60% | 60% | 14% | 24% | 24% | 21% | 19% | 24% |

### True value (judge's category)

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| high | 73 | 36% | 34% | 32% | 46% | 33% | 35% | 14% | 18% | 13% | 18% | 12% | 17% |
| low | 33 | 45% | 66% | 41% | 48% | 41% | 44% | 6% | 0% | 6% | 9% | 9% | 12% |
| normal | 40 | 56% | 57% | 57% | 56% | 54% | 46% | 19% | 22% | 22% | 15% | 14% | 30% |
| not_applicable | 3 | 100% | 100% | 100% | 100% | 100% | 100% | 0% | 0% | 0% | 0% | 0% | 0% |
| unknown | 2 | 0% | – | – | 0% | – | – | 0% | – | – | 0% | – | – |

### Variable typical of the diagnosis

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| no | 83 | 48% | 49% | 48% | 52% | 43% | 43% | 19% | 22% | 20% | 19% | 17% | 24% |
| yes | 58 | 38% | 45% | 33% | 47% | 38% | 38% | 5% | 5% | 3% | 9% | 5% | 12% |

## Diagnostics

- **gemini_knowledge:** answer paths {'literature': 389, 'best_guess': 15, 'case_study': 2, 'query_builder_declined': 7}; source article removed for 0 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **current:** answer paths {'best_guess': 283, 'literature': 123, 'case_study': 3, 'query_builder_declined': 3, 'synthesizer_unanswerable': 1}; source article removed for 54 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **improved_1to4:** answer paths {'literature': 199, 'best_guess': 201, 'case_study': 2, 'query_builder_declined': 11}; source article removed for 60 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_exa_instant:** answer paths {'literature': 126, 'best_guess': 277, 'query_builder_declined': 9, 'case_study': 1}; source article removed for 43 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_parallel_basic:** answer paths {'literature': 141, 'best_guess': 266, 'query_builder_declined': 5, 'case_study': 1}; source article removed for 33 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_perplexity:** answer paths {'best_guess': 146, 'literature': 257, 'case_study': 2, 'query_builder_declined': 7, 'withheld': 1}; source article removed for 47 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **Masked correctness:** 4 of 844 voted labels were "not comparable" (reported as their own label).
- **Judge errors (all attempts, all judges):** 730 judgment(s) failed; rerun the judge step to retry them.

## Judge panel agreement

| Metric | Answers | Unanimous | Majority | Tie broken by the main judge | Tie broken by the next judge | Fewer than all votes |
|---|---|---|---|---|---|---|
| masked correctness | 844 | 82% | 17% | 0% | 0% | 0 |
| factual consistency | 1590 | 99% | 1% | 0% | 0% | 0 |

- **masked correctness, `anthropic/claude-haiku-5.5` vs `z-ai/glm-5.3-flash`:** 748/844 identical labels, Cohen's κ = 0.82.
- **masked correctness, `anthropic/claude-haiku-5.5` vs `openai/gpt-6-luna`:** 732/844 identical labels, Cohen's κ = 0.79.
- **masked correctness, `z-ai/glm-5.3-flash` vs `openai/gpt-6-luna`:** 754/844 identical labels, Cohen's κ = 0.83.
- **factual consistency, `anthropic/claude-haiku-5.5` vs `z-ai/glm-5.3-flash`:** 1582/1590 identical labels, Cohen's κ = 0.69.
- **factual consistency, `anthropic/claude-haiku-5.5` vs `openai/gpt-6-luna`:** 1577/1590 identical labels, Cohen's κ = 0.23.
- **factual consistency, `z-ai/glm-5.3-flash` vs `openai/gpt-6-luna`:** 1581/1590 identical labels, Cohen's κ = 0.31.

## Benchmark spend

| Step | Cost (USD, OpenRouter usage.cost) |
|---|---|
| extract (case facts) | $0.0000 |
| redact + Stage A checks (accepted) | $0.0000 |
| redact + Stage A checks (rejected) | $0.0000 |
| run (all methods; search fees included) | $14.0959 |
| judge: masked correctness (google/gemini-3.5-flash-lite) | $0.9214 |
| judge: masked correctness (openai/gpt-6-luna) | $0.1594 |
| judge: masked correctness (qwen/qwen3.8-flash) | $0.3104 |
| judge: masked correctness (typesafe/jev-1.13) | $0.0354 |
| judge: masked correctness (z-ai/glm-5.3-flash) | $0.1194 |
| judge: masked correctness (anthropic/claude-haiku-5.5) | $0.2348 |
| judge: factual consistency (google/gemini-3.5-flash-lite) | $0.7516 |
| judge: factual consistency (openai/gpt-6-luna) | $0.1987 |
| judge: factual consistency (qwen/qwen3.8-flash) | $0.2683 |
| judge: factual consistency (typesafe/jev-1.13) | $0.0558 |
| judge: factual consistency (anthropic/claude-haiku-5.5) | $0.3187 |
| judge: factual consistency (z-ai/glm-5.3-flash) | $0.1495 |
| validation: controls (panel) | $0.0000 |
| validation: flipped truth (panel) | $0.0000 |
| **total** | **$17.6193** |

Cross-check: the OpenRouter key's usage counter, read right after each of the 6 benchmark commands, rose by $5.1781. The counter lags behind requests, so this undercounts; per-call usage.cost above is the accounting source.

