# Retrieval benchmark report

- Workspace: `environment/results/repeats/run_09/sets_ab`
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
| Documents returned per question | 0.98 [0.97, 0.99] | 7.81 [7.67, 7.92] | 7.86 [7.75, 7.96] | 7.81 [7.71, 7.89] | 7.65 [7.53, 7.76] | 7.61 [7.47, 7.72] | -6.82 [-6.94, -6.69] | +0.06 [-0.04, +0.17] | +0.00 [-0.12, +0.13] | -0.16 [-0.30, -0.02] | -0.20 [-0.35, -0.04] |
| Questions answered from literature | 90% [87, 93] | 31% [26, 35] | 49% [44, 54] | 33% [28, 39] | 35% [31, 40] | 62% [56, 67] | +60 pts [+55, +66] | +19 pts [+13, +25] | +3 pts [-3, +8] | +5 pts [-1, +11] | +31 pts [+25, +38] |
| Questions answered with a best guess (documents gave no usable basis) | 8% [5, 11] | 67% [62, 72] | 49% [44, 54] | 66% [60, 71] | 62% [58, 67] | 36% [31, 41] | -59 pts [-65, -54] | -18 pts [-24, -12] | -1 pts [-7, +5] | -5 pts [-11, +2] | -31 pts [-38, -25] |
| Masked correctness: exact (% of set A questions) | 44% [35, 53] | 46% [37, 55] | 45% [36, 54] | 48% [39, 58] | 45% [37, 54] | 43% [34, 52] | -2 pts [-10, +6] | -1 pts [-8, +7] | +1 pts [-7, +11] | -1 pts [-9, +8] | -3 pts [-11, +5] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 84% [77, 90] | 87% [81, 92] | 87% [80, 92] | 85% [79, 91] | 82% [75, 88] | 85% [79, 91] | -4 pts [-10, +2] | -1 pts [-6, +4] | -2 pts [-7, +3] | -5 pts [-10, +0] | -2 pts [-8, +4] |
| Masked correctness: different category (% of set A questions) | 16% [9, 22] | 11% [6, 16] | 13% [7, 19] | 14% [9, 21] | 17% [11, 24] | 14% [9, 20] | +5 pts [-1, +11] | +2 pts [-3, +7] | +4 pts [-1, +9] | +6 pts [+1, +12] | +4 pts [-2, +9] |
| Masked correctness: not comparable (% of set A questions) | 1% [0, 2] | 2% [0, 5] | 1% [0, 2] | 1% [0, 2] | 1% [0, 2] | 1% [0, 2] | -1 pts [-4, +0] | -1 pts [-4, +0] | -1 pts [-4, +0] | -1 pts [-4, +1] | -1 pts [-4, +1] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] |
| Factual consistency: consistent (% of set B questions) | 98% [96, 100] | 97% [95, 99] | 97% [95, 99] | 99% [97, 100] | 97% [95, 99] | 96% [94, 98] | +1 pts [-1, +3] | +0 pts [-1, +2] | +2 pts [-0, +4] | +0 pts [-3, +3] | -1 pts [-4, +2] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 0] | 0% [0, 1] | 0% [0, 1] | 0% [0, 1] | 1% [0, 2] | 1% [0, 3] | -0 pts [-1, +0] | +0 pts [+0, +0] | +0 pts [-1, +1] | +0 pts [-1, +2] | +1 pts [-1, +2] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 2% [0, 4] | 3% [1, 5] | 2% [1, 4] | 1% [0, 2] | 2% [1, 4] | 3% [1, 5] | -1 pts [-3, +1] | -0 pts [-2, +1] | -2 pts [-4, +0] | -0 pts [-3, +2] | +0 pts [-2, +3] |
| Retrieval cost per question (search fees, search/rerank LLM; USD) | $0.00072 | $0.00000 | $0.00000 | $0.00711 | $0.00507 | $0.00506 | +0.00072 [+0.00071, +0.00073] | +0.00000 [+0.00000, +0.00000] | +0.00711 [+0.00703, +0.00716] | +0.00507 [+0.00499, +0.00514] | +0.00506 [+0.00498, +0.00513] |
| medsim LLM cost per question (Stages A–C, USD) | $0.00205 | $0.00263 | $0.00289 | $0.00287 | $0.00279 | $0.00322 | -0.00058 [-0.00080, -0.00039] | +0.00026 [-0.00003, +0.00052] | +0.00024 [-0.00006, +0.00052] | +0.00016 [-0.00011, +0.00040] | +0.00059 [+0.00031, +0.00085] |
| Total cost per question (USD) | $0.00277 | $0.00263 | $0.00289 | $0.00997 | $0.00786 | $0.00828 | +0.00014 [-0.00008, +0.00032] | +0.00026 [-0.00003, +0.00052] | +0.00735 [+0.00705, +0.00764] | +0.00524 [+0.00496, +0.00548] | +0.00565 [+0.00535, +0.00592] |
| Wall time per question (s) | 77.4 [73.3, 81.6] | 128.4 [120.5, 137.4] | 109.8 [103.2, 116.8] | 105.8 [98.9, 113.3] | 92.2 [87.7, 97.1] | 100.7 [94.9, 106.9] | -50.98 [-59.77, -42.81] | -18.59 [-29.69, -8.36] | -22.52 [-33.23, -12.61] | -36.15 [-46.19, -27.22] | -27.62 [-38.20, -18.10] |
| Time outside medsim's LLM calls per question (≈ retrieval; s) | 3.15 [3.06, 3.24] | 36.66 [33.71, 39.67] | 15.99 [14.94, 17.07] | 6.95 [6.66, 7.24] | 6.94 [6.63, 7.28] | 6.49 [6.20, 6.77] | -33.51 [-36.56, -30.56] | -20.67 [-23.51, -17.89] | -29.70 [-32.69, -26.77] | -29.71 [-32.76, -26.80] | -30.16 [-33.19, -27.25] |

## Set A only (hidden value; masked correctness)

| Metric | gemini_knowledge | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 0.99 [0.96, 1.00] | 7.83 [7.63, 8.00] | 7.94 [7.82, 8.00] | 7.72 [7.54, 7.87] | 7.59 [7.39, 7.77] | 7.62 [7.42, 7.78] | -6.84 [-7.01, -6.66] | +0.11 [+0.00, +0.28] | -0.11 [-0.31, +0.09] | -0.24 [-0.43, -0.05] | -0.21 [-0.41, +0.01] |
| Questions answered from literature | 91% [86, 95] | 36% [28, 45] | 52% [43, 61] | 42% [34, 51] | 40% [33, 49] | 63% [54, 72] | +55 pts [+45, +64] | +16 pts [+5, +27] | +6 pts [-4, +16] | +4 pts [-6, +15] | +27 pts [+15, +39] |
| Questions answered with a best guess (documents gave no usable basis) | 8% [4, 13] | 62% [53, 70] | 47% [38, 57] | 57% [48, 65] | 57% [49, 65] | 35% [26, 44] | -54 pts [-63, -44] | -15 pts [-25, -5] | -5 pts [-15, +5] | -4 pts [-15, +5] | -26 pts [-38, -15] |
| Masked correctness: exact (% of set A questions) | 44% [35, 53] | 46% [37, 55] | 45% [36, 54] | 48% [39, 58] | 45% [37, 54] | 43% [34, 52] | -2 pts [-10, +6] | -1 pts [-8, +7] | +1 pts [-7, +11] | -1 pts [-9, +8] | -3 pts [-11, +5] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 84% [77, 90] | 87% [81, 92] | 87% [80, 92] | 85% [79, 91] | 82% [75, 88] | 85% [79, 91] | -4 pts [-10, +2] | -1 pts [-6, +4] | -2 pts [-7, +3] | -5 pts [-10, +0] | -2 pts [-8, +4] |
| Masked correctness: different category (% of set A questions) | 16% [9, 22] | 11% [6, 16] | 13% [7, 19] | 14% [9, 21] | 17% [11, 24] | 14% [9, 20] | +5 pts [-1, +11] | +2 pts [-3, +7] | +4 pts [-1, +9] | +6 pts [+1, +12] | +4 pts [-2, +9] |
| Masked correctness: not comparable (% of set A questions) | 1% [0, 2] | 2% [0, 5] | 1% [0, 2] | 1% [0, 2] | 1% [0, 2] | 1% [0, 2] | -1 pts [-4, +0] | -1 pts [-4, +0] | -1 pts [-4, +0] | -1 pts [-4, +1] | -1 pts [-4, +1] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] |

## Set B only (value never stated; factual consistency)

| Metric | gemini_knowledge | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 0.98 [0.96, 1.00] | 7.79 [7.63, 7.94] | 7.82 [7.67, 7.94] | 7.85 [7.75, 7.93] | 7.68 [7.52, 7.82] | 7.60 [7.43, 7.75] | -6.81 [-6.95, -6.65] | +0.03 [-0.09, +0.15] | +0.06 [-0.10, +0.23] | -0.12 [-0.29, +0.05] | -0.19 [-0.39, +0.01] |
| Questions answered from literature | 90% [86, 94] | 28% [22, 34] | 47% [41, 54] | 29% [23, 35] | 33% [27, 39] | 61% [55, 67] | +62 pts [+55, +69] | +20 pts [+12, +28] | +1 pts [-6, +9] | +5 pts [-3, +13] | +34 pts [+25, +42] |
| Questions answered with a best guess (documents gave no usable basis) | 8% [5, 12] | 70% [63, 76] | 50% [44, 57] | 70% [64, 76] | 65% [59, 71] | 36% [30, 42] | -62 pts [-69, -54] | -19 pts [-27, -11] | +0 pts [-7, +7] | -5 pts [-13, +3] | -34 pts [-42, -26] |
| Factual consistency: consistent (% of set B questions) | 98% [96, 100] | 97% [95, 99] | 97% [95, 99] | 99% [97, 100] | 97% [95, 99] | 96% [94, 98] | +1 pts [-1, +3] | +0 pts [-1, +2] | +2 pts [-0, +4] | +0 pts [-3, +3] | -1 pts [-4, +2] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 0] | 0% [0, 1] | 0% [0, 1] | 0% [0, 1] | 1% [0, 2] | 1% [0, 3] | -0 pts [-1, +0] | +0 pts [+0, +0] | +0 pts [-1, +1] | +0 pts [-1, +2] | +1 pts [-1, +2] |
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
| anthropometric | 22 | 50% | 59% | 55% | 55% | 59% | 59% | 5% | 9% | 5% | 5% | 14% | 5% |
| laboratory | 77 | 34% | 31% | 34% | 35% | 34% | 30% | 16% | 9% | 12% | 14% | 13% | 10% |
| vital_sign | 42 | 60% | 67% | 62% | 67% | 60% | 60% | 21% | 14% | 19% | 19% | 26% | 26% |

### True value (judge's category)

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| high | 73 | 36% | 35% | 36% | 40% | 37% | 34% | 17% | 11% | 17% | 16% | 16% | 18% |
| low | 34 | 42% | 50% | 48% | 50% | 48% | 48% | 9% | 6% | 6% | 9% | 9% | 3% |
| normal | 38 | 57% | 67% | 57% | 59% | 57% | 54% | 20% | 12% | 11% | 15% | 26% | 17% |
| not_applicable | 5 | 100% | 50% | 100% | 67% | 67% | 100% | 0% | 50% | 0% | 33% | 33% | 0% |

### Variable typical of the diagnosis

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| no | 83 | 47% | 51% | 48% | 48% | 47% | 45% | 22% | 16% | 18% | 18% | 24% | 20% |
| yes | 58 | 40% | 40% | 41% | 47% | 43% | 41% | 7% | 3% | 5% | 9% | 7% | 5% |

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
| masked correctness | 846 | 80% | 20% | 0% | 0% | 0 |
| factual consistency | 1598 | 99% | 1% | 0% | 0% | 0 |

- **masked correctness, `anthropic/claude-haiku-5.5` vs `z-ai/glm-5.3-flash`:** 738/846 identical labels, Cohen's κ = 0.79.
- **masked correctness, `anthropic/claude-haiku-5.5` vs `openai/gpt-6-luna`:** 725/846 identical labels, Cohen's κ = 0.77.
- **masked correctness, `z-ai/glm-5.3-flash` vs `openai/gpt-6-luna`:** 743/846 identical labels, Cohen's κ = 0.80.
- **factual consistency, `anthropic/claude-haiku-5.5` vs `z-ai/glm-5.3-flash`:** 1593/1598 identical labels, Cohen's κ = 0.76.
- **factual consistency, `anthropic/claude-haiku-5.5` vs `openai/gpt-6-luna`:** 1587/1598 identical labels, Cohen's κ = 0.15.
- **factual consistency, `z-ai/glm-5.3-flash` vs `openai/gpt-6-luna`:** 1590/1598 identical labels, Cohen's κ = 0.20.

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
| judge: masked correctness (typesafe/jev-1.13) | $0.0354 |
| judge: masked correctness (anthropic/claude-haiku-5.5) | $0.2311 |
| judge: masked correctness (z-ai/glm-5.3-flash) | $0.1314 |
| judge: factual consistency (google/gemini-3.5-flash-lite) | $0.7053 |
| judge: factual consistency (openai/gpt-6-luna) | $0.1990 |
| judge: factual consistency (qwen/qwen3.8-flash) | $0.2692 |
| judge: factual consistency (typesafe/jev-1.13) | $0.0560 |
| judge: factual consistency (anthropic/claude-haiku-5.5) | $0.3199 |
| judge: factual consistency (z-ai/glm-5.3-flash) | $0.1533 |
| validation: controls (panel) | $0.0000 |
| validation: flipped truth (panel) | $0.0000 |
| **total** | **$17.2494** |

Cross-check: the OpenRouter key's usage counter, read right after each of the 6 benchmark commands, rose by $1.9044. The counter lags behind requests, so this undercounts; per-call usage.cost above is the accounting source.

