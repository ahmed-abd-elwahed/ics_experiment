# Retrieval benchmark report

- Workspace: `environment/results/repeats/run_10/sets_ab`
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
| Documents returned per question | 0.98 [0.96, 0.99] | 7.88 [7.79, 7.96] | 7.75 [7.60, 7.87] | 7.69 [7.53, 7.81] | 7.72 [7.61, 7.82] | 7.62 [7.47, 7.74] | -6.91 [-6.98, -6.82] | -0.14 [-0.25, -0.04] | -0.19 [-0.35, -0.07] | -0.16 [-0.29, -0.04] | -0.27 [-0.39, -0.17] |
| Questions answered from literature | 94% [92, 96] | 30% [25, 35] | 48% [43, 53] | 31% [26, 36] | 34% [30, 39] | 62% [57, 67] | +64 pts [+59, +69] | +18 pts [+12, +24] | +1 pts [-5, +6] | +4 pts [-2, +10] | +32 pts [+26, +38] |
| Questions answered with a best guess (documents gave no usable basis) | 4% [2, 6] | 69% [64, 73] | 49% [43, 54] | 67% [61, 72] | 64% [60, 68] | 35% [31, 40] | -65 pts [-70, -60] | -20 pts [-26, -14] | -1 pts [-8, +4] | -4 pts [-10, +2] | -33 pts [-39, -27] |
| Masked correctness: exact (% of set A questions) | 43% [34, 51] | 42% [33, 51] | 40% [32, 49] | 48% [39, 57] | 38% [30, 47] | 40% [31, 49] | +1 pts [-8, +9] | -1 pts [-9, +6] | +6 pts [-2, +14] | -4 pts [-11, +5] | -2 pts [-9, +4] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 87% [80, 92] | 84% [77, 90] | 87% [80, 92] | 87% [81, 93] | 84% [78, 90] | 82% [74, 88] | +2 pts [-3, +8] | +2 pts [-2, +7] | +3 pts [-2, +8] | +0 pts [-6, +6] | -2 pts [-8, +4] |
| Masked correctness: different category (% of set A questions) | 12% [7, 18] | 15% [9, 22] | 13% [7, 19] | 12% [7, 18] | 14% [9, 21] | 18% [12, 25] | -3 pts [-9, +3] | -2 pts [-7, +2] | -3 pts [-8, +2] | -1 pts [-7, +5] | +3 pts [-3, +9] |
| Masked correctness: not comparable (% of set A questions) | 1% [0, 2] | 1% [0, 2] | 1% [0, 2] | 0% [0, 0] | 1% [0, 3] | 0% [0, 0] | +0 pts [+0, +0] | +0 pts [+0, +0] | -1 pts [-2, +0] | +1 pts [+0, +2] | -1 pts [-2, +0] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | +1 pts [+0, +2] | +0 pts [+0, +0] | +1 pts [+0, +2] | +0 pts [+0, +0] | +0 pts [+0, +0] |
| Factual consistency: consistent (% of set B questions) | 98% [96, 99] | 99% [97, 100] | 96% [93, 98] | 97% [95, 99] | 98% [96, 100] | 97% [94, 99] | -1 pts [-3, +1] | -3 pts [-5, -1] | -1 pts [-4, +0] | -0 pts [-2, +1] | -2 pts [-4, +0] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 0] | 0% [0, 0] | 0% [0, 1] | 0% [0, 0] | 0% [0, 0] | 0% [0, 1] | +0 pts [+0, +0] | +0 pts [+0, +1] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +1] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 2% [1, 4] | 1% [0, 3] | 4% [2, 7] | 3% [1, 5] | 2% [0, 4] | 3% [1, 5] | +1 pts [-1, +3] | +3 pts [+1, +5] | +1 pts [-0, +4] | +0 pts [-1, +2] | +1 pts [-0, +4] |
| Retrieval cost per question (search fees, search/rerank LLM; USD) | $0.00072 | $0.00000 | $0.00000 | $0.00700 | $0.00511 | $0.00506 | +0.00072 [+0.00070, +0.00073] | +0.00000 [+0.00000, +0.00000] | +0.00700 [+0.00687, +0.00711] | +0.00511 [+0.00504, +0.00516] | +0.00506 [+0.00498, +0.00514] |
| medsim LLM cost per question (Stages A–C, USD) | $0.00230 | $0.00280 | $0.00314 | $0.00249 | $0.00260 | $0.00291 | -0.00050 [-0.00070, -0.00030] | +0.00034 [+0.00009, +0.00057] | -0.00031 [-0.00057, -0.00007] | -0.00020 [-0.00043, +0.00001] | +0.00011 [-0.00016, +0.00037] |
| Total cost per question (USD) | $0.00302 | $0.00280 | $0.00314 | $0.00949 | $0.00771 | $0.00797 | +0.00022 [+0.00002, +0.00042] | +0.00034 [+0.00009, +0.00057] | +0.00669 [+0.00639, +0.00696] | +0.00491 [+0.00466, +0.00514] | +0.00517 [+0.00490, +0.00544] |
| Wall time per question (s) | 78.0 [74.1, 82.4] | 130.9 [124.0, 138.6] | 110.5 [104.8, 117.1] | 84.4 [79.4, 89.5] | 78.4 [74.4, 82.9] | 92.6 [86.9, 99.3] | -52.90 [-60.78, -45.29] | -20.39 [-28.58, -12.43] | -46.51 [-55.53, -38.48] | -52.45 [-60.43, -44.87] | -38.29 [-46.91, -29.89] |
| Time outside medsim's LLM calls per question (≈ retrieval; s) | 3.07 [3.02, 3.13] | 39.56 [36.47, 43.06] | 21.01 [19.66, 22.26] | 6.57 [6.25, 6.88] | 6.63 [6.30, 7.00] | 6.74 [6.35, 7.11] | -36.49 [-39.99, -33.41] | -18.55 [-21.76, -15.57] | -32.99 [-36.53, -29.89] | -32.93 [-36.41, -29.83] | -32.82 [-36.40, -29.74] |

## Set A only (hidden value; masked correctness)

| Metric | gemini_knowledge | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 0.99 [0.96, 1.00] | 7.83 [7.61, 8.00] | 7.94 [7.82, 8.00] | 7.78 [7.62, 7.89] | 7.78 [7.69, 7.86] | 7.57 [7.37, 7.75] | -6.84 [-7.01, -6.64] | +0.11 [+0.00, +0.28] | -0.05 [-0.28, +0.18] | -0.05 [-0.24, +0.17] | -0.26 [-0.37, -0.11] |
| Questions answered from literature | 96% [92, 99] | 32% [24, 40] | 53% [46, 61] | 37% [28, 47] | 38% [30, 45] | 61% [53, 70] | +64 pts [+54, +73] | +21 pts [+11, +31] | +5 pts [-5, +15] | +6 pts [-6, +16] | +29 pts [+19, +39] |
| Questions answered with a best guess (documents gave no usable basis) | 3% [1, 6] | 66% [57, 74] | 46% [38, 54] | 62% [53, 71] | 62% [55, 70] | 38% [29, 46] | -63 pts [-72, -54] | -20 pts [-29, -10] | -4 pts [-13, +6] | -4 pts [-14, +8] | -28 pts [-39, -18] |
| Masked correctness: exact (% of set A questions) | 43% [34, 51] | 42% [33, 51] | 40% [32, 49] | 48% [39, 57] | 38% [30, 47] | 40% [31, 49] | +1 pts [-8, +9] | -1 pts [-9, +6] | +6 pts [-2, +14] | -4 pts [-11, +5] | -2 pts [-9, +4] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 87% [80, 92] | 84% [77, 90] | 87% [80, 92] | 87% [81, 93] | 84% [78, 90] | 82% [74, 88] | +2 pts [-3, +8] | +2 pts [-2, +7] | +3 pts [-2, +8] | +0 pts [-6, +6] | -2 pts [-8, +4] |
| Masked correctness: different category (% of set A questions) | 12% [7, 18] | 15% [9, 22] | 13% [7, 19] | 12% [7, 18] | 14% [9, 21] | 18% [12, 25] | -3 pts [-9, +3] | -2 pts [-7, +2] | -3 pts [-8, +2] | -1 pts [-7, +5] | +3 pts [-3, +9] |
| Masked correctness: not comparable (% of set A questions) | 1% [0, 2] | 1% [0, 2] | 1% [0, 2] | 0% [0, 0] | 1% [0, 3] | 0% [0, 0] | +0 pts [+0, +0] | +0 pts [+0, +0] | -1 pts [-2, +0] | +1 pts [+0, +2] | -1 pts [-2, +0] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | +1 pts [+0, +2] | +0 pts [+0, +0] | +1 pts [+0, +2] | +0 pts [+0, +0] | +0 pts [+0, +0] |

## Set B only (value never stated; factual consistency)

| Metric | gemini_knowledge | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 0.97 [0.95, 0.99] | 7.91 [7.79, 8.00] | 7.65 [7.43, 7.82] | 7.64 [7.43, 7.81] | 7.69 [7.53, 7.83] | 7.64 [7.44, 7.80] | -6.94 [-7.02, -6.83] | -0.26 [-0.44, -0.12] | -0.27 [-0.45, -0.12] | -0.22 [-0.37, -0.09] | -0.27 [-0.44, -0.14] |
| Questions answered from literature | 93% [90, 96] | 29% [23, 34] | 46% [39, 52] | 27% [21, 33] | 32% [27, 38] | 63% [57, 68] | +65 pts [+58, +71] | +17 pts [+9, +24] | -1 pts [-8, +5] | +4 pts [-4, +11] | +34 pts [+26, +41] |
| Questions answered with a best guess (documents gave no usable basis) | 4% [2, 7] | 70% [64, 75] | 50% [44, 57] | 69% [64, 75] | 65% [59, 71] | 34% [29, 40] | -66 pts [-72, -60] | -20 pts [-27, -12] | -0 pts [-7, +6] | -4 pts [-12, +4] | -36 pts [-43, -28] |
| Factual consistency: consistent (% of set B questions) | 98% [96, 99] | 99% [97, 100] | 96% [93, 98] | 97% [95, 99] | 98% [96, 100] | 97% [94, 99] | -1 pts [-3, +1] | -3 pts [-5, -1] | -1 pts [-4, +0] | -0 pts [-2, +1] | -2 pts [-4, +0] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 0] | 0% [0, 0] | 0% [0, 1] | 0% [0, 0] | 0% [0, 0] | 0% [0, 1] | +0 pts [+0, +0] | +0 pts [+0, +1] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +1] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 2% [1, 4] | 1% [0, 3] | 4% [2, 7] | 3% [1, 5] | 2% [0, 4] | 3% [1, 5] | +1 pts [-1, +3] | +3 pts [+1, +5] | +1 pts [-0, +4] | +0 pts [-1, +2] | +1 pts [-0, +4] |

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
| anthropometric | 22 | 55% | 64% | 59% | 59% | 50% | 55% | 0% | 5% | 0% | 5% | 14% | 9% |
| laboratory | 77 | 34% | 30% | 29% | 34% | 29% | 30% | 12% | 13% | 12% | 12% | 9% | 17% |
| vital_sign | 42 | 52% | 52% | 52% | 67% | 50% | 50% | 19% | 24% | 21% | 17% | 24% | 24% |

### True value (judge's category)

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| high | 73 | 36% | 28% | 33% | 43% | 31% | 35% | 12% | 17% | 13% | 14% | 14% | 15% |
| low | 34 | 47% | 57% | 35% | 43% | 37% | 39% | 3% | 0% | 6% | 10% | 7% | 15% |
| normal | 44 | 50% | 54% | 55% | 59% | 54% | 46% | 21% | 23% | 18% | 10% | 19% | 26% |
| not_applicable | 2 | 100% | 100% | 100% | 100% | 50% | 100% | 0% | 0% | 0% | 0% | 50% | 0% |
| unknown | 2 | 0% | – | – | 0% | – | – | 0% | – | – | 0% | – | – |

### Variable typical of the diagnosis

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| no | 83 | 46% | 45% | 46% | 51% | 41% | 42% | 17% | 23% | 19% | 17% | 20% | 20% |
| yes | 58 | 38% | 38% | 33% | 43% | 34% | 36% | 5% | 3% | 3% | 5% | 5% | 14% |

## Diagnostics

- **gemini_knowledge:** answer paths {'literature': 389, 'best_guess': 15, 'case_study': 2, 'query_builder_declined': 7}; source article removed for 0 question(s); 0 answer(s) without any judge's verdict; 1 answer(s) voted on by fewer than all 3 judges.
- **current:** answer paths {'best_guess': 283, 'literature': 123, 'case_study': 3, 'query_builder_declined': 3, 'synthesizer_unanswerable': 1}; source article removed for 54 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **improved_1to4:** answer paths {'literature': 199, 'best_guess': 201, 'case_study': 2, 'query_builder_declined': 11}; source article removed for 60 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_exa_instant:** answer paths {'literature': 126, 'best_guess': 277, 'query_builder_declined': 9, 'case_study': 1}; source article removed for 43 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_parallel_basic:** answer paths {'literature': 141, 'best_guess': 266, 'query_builder_declined': 5, 'case_study': 1}; source article removed for 33 question(s); 0 answer(s) without any judge's verdict; 1 answer(s) voted on by fewer than all 3 judges.
- **openrouter_perplexity:** answer paths {'best_guess': 146, 'literature': 257, 'case_study': 2, 'query_builder_declined': 7, 'withheld': 1}; source article removed for 47 question(s); 0 answer(s) without any judge's verdict; 5 answer(s) voted on by fewer than all 3 judges.
- **Masked correctness:** 5 of 844 voted labels were "not comparable" (reported as their own label).
- **Judge errors (all attempts, all judges):** 730 judgment(s) failed; rerun the judge step to retry them.

## Judge panel agreement

| Metric | Answers | Unanimous | Majority | Tie broken by the main judge | Tie broken by the next judge | Fewer than all votes |
|---|---|---|---|---|---|---|
| masked correctness | 844 | 73% | 26% | 1% | 0% | 3 |
| factual consistency | 1590 | 99% | 1% | 0% | 0% | 4 |

- **masked correctness, `google/gemini-3.5-flash-lite` vs `qwen/qwen3.8-flash`:** 668/841 identical labels, Cohen's κ = 0.67.
- **masked correctness, `google/gemini-3.5-flash-lite` vs `openai/gpt-6-luna`:** 652/843 identical labels, Cohen's κ = 0.64.
- **masked correctness, `qwen/qwen3.8-flash` vs `openai/gpt-6-luna`:** 753/842 identical labels, Cohen's κ = 0.83.
- **factual consistency, `google/gemini-3.5-flash-lite` vs `qwen/qwen3.8-flash`:** 1575/1586 identical labels, Cohen's κ = -0.00.
- **factual consistency, `google/gemini-3.5-flash-lite` vs `openai/gpt-6-luna`:** 1584/1590 identical labels, Cohen's κ = 0.25.
- **factual consistency, `qwen/qwen3.8-flash` vs `openai/gpt-6-luna`:** 1581/1586 identical labels, Cohen's κ = 0.28.

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
| judge: factual consistency (google/gemini-3.5-flash-lite) | $0.7516 |
| judge: factual consistency (openai/gpt-6-luna) | $0.1987 |
| judge: factual consistency (qwen/qwen3.8-flash) | $0.2683 |
| validation: controls (panel) | $0.0000 |
| validation: flipped truth (panel) | $0.0000 |
| **total** | **$16.7057** |

Cross-check: the OpenRouter key's usage counter, read right after each of the 4 benchmark commands, rose by $4.3762. The counter lags behind requests, so this undercounts; per-call usage.cost above is the accounting source.

