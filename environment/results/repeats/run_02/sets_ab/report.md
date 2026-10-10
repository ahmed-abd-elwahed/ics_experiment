# Retrieval benchmark report

- Workspace: `environment/results/repeats/run_02/sets_ab`
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
| Documents returned per question | 0.98 [0.96, 0.99] | 7.86 [7.76, 7.95] | 7.83 [7.70, 7.93] | 7.71 [7.58, 7.82] | 7.66 [7.52, 7.78] | 7.67 [7.54, 7.77] | -6.89 [-6.97, -6.78] | -0.04 [-0.19, +0.12] | -0.15 [-0.29, -0.02] | -0.21 [-0.36, -0.06] | -0.20 [-0.35, -0.04] |
| Questions answered from literature | 92% [90, 95] | 35% [31, 40] | 47% [42, 52] | 28% [24, 32] | 30% [26, 35] | 60% [55, 65] | +57 pts [+52, +62] | +12 pts [+7, +17] | -8 pts [-13, -2] | -5 pts [-11, +0] | +24 pts [+18, +31] |
| Questions answered with a best guess (documents gave no usable basis) | 5% [3, 7] | 63% [58, 67] | 50% [45, 55] | 70% [65, 74] | 68% [63, 72] | 38% [33, 44] | -57 pts [-62, -52] | -12 pts [-18, -7] | +7 pts [+2, +13] | +5 pts [-1, +11] | -24 pts [-30, -18] |
| Masked correctness: exact (% of set A questions) | 43% [34, 51] | 45% [37, 54] | 38% [30, 47] | 45% [36, 54] | 43% [34, 51] | 44% [36, 52] | -3 pts [-10, +5] | -7 pts [-15, +1] | -1 pts [-10, +9] | -3 pts [-10, +5] | -1 pts [-9, +6] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 85% [78, 91] | 88% [82, 93] | 87% [80, 92] | 87% [80, 92] | 88% [82, 94] | 84% [76, 89] | -3 pts [-8, +2] | -1 pts [-5, +2] | -1 pts [-7, +4] | +0 pts [-5, +6] | -4 pts [-9, +0] |
| Masked correctness: different category (% of set A questions) | 13% [8, 20] | 11% [6, 17] | 13% [7, 19] | 13% [7, 19] | 11% [6, 17] | 14% [9, 21] | +2 pts [-3, +7] | +1 pts [-2, +5] | +1 pts [-4, +7] | +0 pts [-6, +5] | +3 pts [-1, +7] |
| Masked correctness: not comparable (% of set A questions) | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 0% [0, 0] | 1% [0, 4] | +1 pts [+0, +2] | +0 pts [+0, +0] | +1 pts [+0, +2] | +0 pts [+0, +0] | +1 pts [+0, +4] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 1% [0, 2] | 1% [0, 2] | 1% [0, 2] | 0% [0, 0] | 1% [0, 2] | 1% [0, 2] | +0 pts [-2, +2] | +0 pts [-2, +2] | -1 pts [-2, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] |
| Factual consistency: consistent (% of set B questions) | 97% [95, 99] | 97% [96, 99] | 97% [94, 99] | 97% [95, 99] | 98% [96, 99] | 99% [97, 100] | -0 pts [-3, +2] | -1 pts [-4, +2] | -0 pts [-3, +2] | +0 pts [-2, +3] | +1 pts [-1, +3] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 0] | 0% [0, 0] | 0% [0, 1] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | +0 pts [+0, +0] | +0 pts [+0, +1] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 3% [1, 5] | 3% [1, 4] | 3% [1, 5] | 3% [1, 5] | 2% [1, 4] | 1% [0, 3] | +0 pts [-2, +3] | +0 pts [-2, +3] | +0 pts [-2, +2] | -0 pts [-3, +2] | -1 pts [-3, +1] |
| Retrieval cost per question (search fees, search/rerank LLM; USD) | $0.00071 | $0.00000 | $0.00000 | $0.00702 | $0.00508 | $0.00510 | +0.00071 [+0.00070, +0.00073] | +0.00000 [+0.00000, +0.00000] | +0.00702 [+0.00691, +0.00711] | +0.00508 [+0.00500, +0.00515] | +0.00510 [+0.00503, +0.00515] |
| medsim LLM cost per question (Stages A–C, USD) | $0.00132 | $0.00178 | $0.00206 | $0.00186 | $0.00200 | $0.00240 | -0.00046 [-0.00065, -0.00027] | +0.00028 [+0.00009, +0.00048] | +0.00008 [-0.00012, +0.00029] | +0.00023 [+0.00007, +0.00038] | +0.00062 [+0.00043, +0.00081] |
| Total cost per question (USD) | $0.00203 | $0.00178 | $0.00206 | $0.00888 | $0.00709 | $0.00750 | +0.00026 [+0.00007, +0.00045] | +0.00028 [+0.00009, +0.00048] | +0.00710 [+0.00686, +0.00733] | +0.00531 [+0.00512, +0.00549] | +0.00572 [+0.00552, +0.00592] |
| Wall time per question (s) | 54.5 [51.4, 57.9] | 128.4 [122.2, 135.3] | 106.5 [99.0, 114.3] | 78.2 [72.4, 84.5] | 76.1 [71.0, 81.8] | 92.2 [85.4, 99.0] | -73.88 [-81.21, -67.69] | -21.97 [-29.98, -14.34] | -50.18 [-58.05, -42.89] | -52.28 [-59.14, -45.66] | -36.26 [-44.67, -28.66] |
| Time outside medsim's LLM calls per question (≈ retrieval; s) | 2.68 [2.24, 3.22] | 60.26 [55.72, 65.24] | 28.13 [26.43, 29.72] | 5.60 [5.23, 6.01] | 6.51 [6.28, 6.74] | 6.59 [6.31, 6.89] | -57.58 [-62.62, -52.85] | -32.13 [-37.63, -27.27] | -54.66 [-59.70, -50.08] | -53.75 [-58.78, -49.13] | -53.67 [-58.73, -49.06] |

## Set A only (hidden value; masked correctness)

| Metric | gemini_knowledge | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 0.99 [0.96, 1.00] | 8.00 [8.00, 8.00] | 7.94 [7.79, 8.00] | 7.79 [7.64, 7.90] | 7.67 [7.51, 7.80] | 7.56 [7.31, 7.78] | -7.01 [-7.04, -7.00] | -0.06 [-0.21, +0.00] | -0.21 [-0.36, -0.10] | -0.33 [-0.49, -0.20] | -0.44 [-0.69, -0.22] |
| Questions answered from literature | 94% [90, 98] | 38% [30, 46] | 57% [49, 65] | 33% [25, 41] | 38% [30, 45] | 62% [54, 71] | +57 pts [+48, +65] | +20 pts [+9, +30] | -4 pts [-14, +5] | +0 pts [-11, +10] | +25 pts [+14, +36] |
| Questions answered with a best guess (documents gave no usable basis) | 4% [1, 8] | 62% [53, 70] | 42% [34, 50] | 66% [58, 74] | 61% [52, 69] | 35% [27, 43] | -57 pts [-66, -49] | -20 pts [-31, -9] | +4 pts [-5, +14] | -1 pts [-11, +10] | -26 pts [-37, -16] |
| Masked correctness: exact (% of set A questions) | 43% [34, 51] | 45% [37, 54] | 38% [30, 47] | 45% [36, 54] | 43% [34, 51] | 44% [36, 52] | -3 pts [-10, +5] | -7 pts [-15, +1] | -1 pts [-10, +9] | -3 pts [-10, +5] | -1 pts [-9, +6] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 85% [78, 91] | 88% [82, 93] | 87% [80, 92] | 87% [80, 92] | 88% [82, 94] | 84% [76, 89] | -3 pts [-8, +2] | -1 pts [-5, +2] | -1 pts [-7, +4] | +0 pts [-5, +6] | -4 pts [-9, +0] |
| Masked correctness: different category (% of set A questions) | 13% [8, 20] | 11% [6, 17] | 13% [7, 19] | 13% [7, 19] | 11% [6, 17] | 14% [9, 21] | +2 pts [-3, +7] | +1 pts [-2, +5] | +1 pts [-4, +7] | +0 pts [-6, +5] | +3 pts [-1, +7] |
| Masked correctness: not comparable (% of set A questions) | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 0% [0, 0] | 1% [0, 4] | +1 pts [+0, +2] | +0 pts [+0, +0] | +1 pts [+0, +2] | +0 pts [+0, +0] | +1 pts [+0, +4] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 1% [0, 2] | 1% [0, 2] | 1% [0, 2] | 0% [0, 0] | 1% [0, 2] | 1% [0, 2] | +0 pts [-2, +2] | +0 pts [-2, +2] | -1 pts [-2, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] |

## Set B only (value never stated; factual consistency)

| Metric | gemini_knowledge | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 0.97 [0.95, 0.99] | 7.79 [7.64, 7.91] | 7.76 [7.57, 7.91] | 7.68 [7.50, 7.82] | 7.65 [7.47, 7.80] | 7.72 [7.58, 7.83] | -6.82 [-6.95, -6.68] | -0.03 [-0.26, +0.18] | -0.12 [-0.30, +0.07] | -0.14 [-0.33, +0.06] | -0.07 [-0.24, +0.10] |
| Questions answered from literature | 91% [88, 94] | 34% [27, 41] | 42% [36, 48] | 25% [20, 30] | 26% [21, 32] | 58% [52, 65] | +57 pts [+50, +64] | +8 pts [+0, +15] | -9 pts [-17, -1] | -8 pts [-15, +0] | +24 pts [+16, +33] |
| Questions answered with a best guess (documents gave no usable basis) | 6% [3, 9] | 63% [56, 70] | 55% [49, 61] | 72% [67, 77] | 71% [65, 76] | 40% [34, 46] | -57 pts [-65, -50] | -8 pts [-16, -1] | +9 pts [+0, +17] | +8 pts [+0, +15] | -23 pts [-32, -15] |
| Factual consistency: consistent (% of set B questions) | 97% [95, 99] | 97% [96, 99] | 97% [94, 99] | 97% [95, 99] | 98% [96, 99] | 99% [97, 100] | -0 pts [-3, +2] | -1 pts [-4, +2] | -0 pts [-3, +2] | +0 pts [-2, +3] | +1 pts [-1, +3] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 0] | 0% [0, 0] | 0% [0, 1] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | +0 pts [+0, +0] | +0 pts [+0, +1] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 3% [1, 5] | 3% [1, 4] | 3% [1, 5] | 3% [1, 5] | 2% [1, 4] | 1% [0, 3] | +0 pts [-2, +3] | +0 pts [-2, +3] | +0 pts [-2, +2] | -0 pts [-3, +2] | -1 pts [-3, +1] |

## Cost

All questions that ran.

| Method | Questions | Retrieval (search fees + search model) | medsim LLM (Stages A–C) | Total | Total per question | Median wall time |
|---|---|---|---|---|---|---|
| gemini_knowledge | 413 | $0.2950 | $0.5444 | $0.8394 | $0.00203 | 45.0 s |
| current | 413 | $0.0000 | $0.7338 | $0.7338 | $0.00178 | 113.5 s |
| improved_1to4 | 413 | $0.0000 | $0.8488 | $0.8488 | $0.00206 | 88.9 s |
| openrouter_exa_instant | 413 | $2.8992 | $0.7667 | $3.6660 | $0.00888 | 57.9 s |
| openrouter_parallel_basic | 413 | $2.0990 | $0.8276 | $2.9267 | $0.00709 | 59.5 s |
| openrouter_perplexity | 413 | $2.1064 | $0.9903 | $3.0967 | $0.00750 | 73.6 s |

## By subgroup (set A)

### Variable category

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| anthropometric | 22 | 50% | 68% | 55% | 50% | 64% | 68% | 5% | 5% | 5% | 0% | 0% | 5% |
| laboratory | 77 | 32% | 30% | 26% | 34% | 25% | 31% | 13% | 9% | 10% | 14% | 13% | 17% |
| vital_sign | 42 | 57% | 62% | 52% | 62% | 64% | 55% | 19% | 19% | 21% | 17% | 14% | 14% |

### True value (judge's category)

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| high | 73 | 34% | 35% | 30% | 38% | 37% | 38% | 14% | 14% | 14% | 15% | 14% | 15% |
| low | 34 | 45% | 52% | 39% | 50% | 39% | 43% | 3% | 0% | 3% | 3% | 3% | 3% |
| normal | 43 | 55% | 58% | 50% | 50% | 55% | 54% | 21% | 17% | 19% | 17% | 13% | 22% |
| not_applicable | 2 | 100% | 100% | 100% | 100% | 100% | 100% | 0% | 0% | 0% | 0% | 0% | 0% |
| unknown | 2 | 0% | 0% | 0% | – | 0% | 0% | 0% | 0% | 0% | – | 0% | 0% |

### Variable typical of the diagnosis

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| no | 83 | 47% | 52% | 42% | 43% | 46% | 46% | 19% | 17% | 18% | 17% | 13% | 18% |
| yes | 58 | 36% | 36% | 33% | 47% | 38% | 41% | 5% | 3% | 5% | 7% | 9% | 9% |

## Diagnostics

- **gemini_knowledge:** answer paths {'literature': 381, 'best_guess': 22, 'query_builder_declined': 9, 'case_study': 1}; source article removed for 0 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **current:** answer paths {'best_guess': 259, 'literature': 146, 'synthesizer_unanswerable': 1, 'query_builder_declined': 7}; source article removed for 52 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **improved_1to4:** answer paths {'literature': 196, 'best_guess': 208, 'query_builder_declined': 8, 'off_topic': 1}; source article removed for 60 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_exa_instant:** answer paths {'literature': 115, 'best_guess': 289, 'case_study': 1, 'query_builder_declined': 8}; source article removed for 42 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_parallel_basic:** answer paths {'literature': 125, 'best_guess': 279, 'case_study': 2, 'synthesizer_unanswerable': 1, 'query_builder_declined': 6}; source article removed for 33 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_perplexity:** answer paths {'best_guess': 159, 'literature': 247, 'case_study': 2, 'query_builder_declined': 4, 'off_topic': 1}; source article removed for 38 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **Masked correctness:** 4 of 841 voted labels were "not comparable" (reported as their own label).
- **Judge errors (all attempts, all judges):** 75 judgment(s) failed; rerun the judge step to retry them.

## Judge panel agreement

| Metric | Answers | Unanimous | Majority | Tie broken by the main judge | Tie broken by the next judge | Fewer than all votes |
|---|---|---|---|---|---|---|
| masked correctness | 841 | 71% | 29% | 0% | 0% | 0 |
| factual consistency | 1591 | 100% | 0% | 0% | 0% | 0 |

- **masked correctness, `google/gemini-3.5-flash-lite` vs `qwen/qwen3.8-flash`:** 648/841 identical labels, Cohen's κ = 0.63.
- **masked correctness, `google/gemini-3.5-flash-lite` vs `openai/gpt-6-luna`:** 635/841 identical labels, Cohen's κ = 0.60.
- **masked correctness, `qwen/qwen3.8-flash` vs `openai/gpt-6-luna`:** 751/841 identical labels, Cohen's κ = 0.82.
- **factual consistency, `google/gemini-3.5-flash-lite` vs `qwen/qwen3.8-flash`:** 1588/1591 identical labels, Cohen's κ = -0.00.
- **factual consistency, `google/gemini-3.5-flash-lite` vs `openai/gpt-6-luna`:** 1588/1591 identical labels, Cohen's κ = -0.00.
- **factual consistency, `qwen/qwen3.8-flash` vs `openai/gpt-6-luna`:** 1589/1591 identical labels, Cohen's κ = 0.50.

## Benchmark spend

| Step | Cost (USD, OpenRouter usage.cost) |
|---|---|
| extract (case facts) | $0.0000 |
| redact + Stage A checks (accepted) | $0.0000 |
| redact + Stage A checks (rejected) | $0.0000 |
| run (all methods; search fees included) | $12.1114 |
| judge: masked correctness (google/gemini-3.5-flash-lite) | $0.9923 |
| judge: masked correctness (openai/gpt-6-luna) | $0.1593 |
| judge: masked correctness (qwen/qwen3.8-flash) | $0.3253 |
| judge: factual consistency (google/gemini-3.5-flash-lite) | $0.7037 |
| judge: factual consistency (openai/gpt-6-luna) | $0.1977 |
| judge: factual consistency (qwen/qwen3.8-flash) | $0.2765 |
| validation: controls (panel) | $0.0000 |
| validation: flipped truth (panel) | $0.0000 |
| **total** | **$14.7662** |

Cross-check: the OpenRouter key's usage counter, read right after each of the 6 benchmark commands, rose by $1.2832. The counter lags behind requests, so this undercounts; per-call usage.cost above is the accounting source.

