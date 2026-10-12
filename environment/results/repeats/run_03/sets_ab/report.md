# Retrieval benchmark report

- Workspace: `environment/results/repeats/run_03/sets_ab`
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
| Documents returned per question | 0.99 [0.98, 1.00] | 7.71 [7.56, 7.84] | 7.75 [7.61, 7.87] | 7.63 [7.49, 7.77] | 7.57 [7.41, 7.71] | 7.60 [7.45, 7.73] | -6.72 [-6.85, -6.58] | +0.04 [-0.06, +0.14] | -0.08 [-0.23, +0.08] | -0.14 [-0.32, +0.03] | -0.11 [-0.27, +0.05] |
| Questions answered from literature | 92% [90, 95] | 29% [25, 34] | 44% [40, 49] | 27% [22, 32] | 33% [29, 38] | 62% [57, 67] | +63 pts [+58, +69] | +15 pts [+9, +21] | -2 pts [-8, +4] | +4 pts [-2, +11] | +33 pts [+26, +39] |
| Questions answered with a best guess (documents gave no usable basis) | 7% [4, 9] | 67% [62, 72] | 53% [48, 57] | 69% [64, 75] | 64% [59, 69] | 35% [30, 40] | -61 pts [-66, -55] | -15 pts [-20, -8] | +2 pts [-4, +8] | -3 pts [-11, +3] | -32 pts [-39, -25] |
| Masked correctness: exact (% of set A questions) | 45% [36, 54] | 42% [33, 51] | 40% [31, 49] | 48% [40, 57] | 46% [38, 55] | 45% [36, 53] | +4 pts [-6, +13] | -2 pts [-9, +5] | +6 pts [-2, +15] | +4 pts [-4, +12] | +3 pts [-6, +12] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 83% [76, 90] | 87% [81, 93] | 85% [79, 91] | 86% [79, 92] | 82% [74, 88] | 84% [77, 90] | -4 pts [-10, +1] | -2 pts [-8, +3] | -1 pts [-7, +4] | -6 pts [-11, -1] | -4 pts [-10, +3] |
| Masked correctness: different category (% of set A questions) | 16% [10, 23] | 11% [6, 18] | 13% [8, 20] | 13% [7, 19] | 16% [10, 24] | 15% [9, 21] | +5 pts [-1, +10] | +2 pts [-3, +8] | +1 pts [-3, +6] | +5 pts [+0, +10] | +4 pts [-2, +10] |
| Masked correctness: not comparable (% of set A questions) | 1% [0, 2] | 1% [0, 2] | 1% [0, 2] | 0% [0, 0] | 2% [0, 5] | 1% [0, 4] | +0 pts [-2, +2] | +0 pts [+0, +0] | -1 pts [-2, +0] | +1 pts [+0, +4] | +1 pts [-1, +3] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 0% [0, 0] | 1% [0, 2] | 1% [0, 2] | 1% [0, 4] | 0% [0, 0] | 0% [0, 0] | -1 pts [-2, +0] | +0 pts [-2, +2] | +1 pts [-2, +3] | -1 pts [-2, +0] | -1 pts [-2, +0] |
| Factual consistency: consistent (% of set B questions) | 99% [98, 100] | 96% [94, 98] | 97% [95, 99] | 96% [94, 98] | 97% [94, 99] | 97% [95, 99] | +3 pts [+1, +6] | +1 pts [+0, +3] | +0 pts [-2, +3] | +1 pts [-2, +4] | +1 pts [-1, +4] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 1] | 0% [0, 1] | 0% [0, 0] | 0% [0, 1] | 1% [0, 2] | 1% [0, 2] | +0 pts [-1, +1] | -0 pts [-1, +0] | +0 pts [+0, +0] | +0 pts [-1, +2] | +0 pts [-1, +2] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 0% [0, 1] | 4% [2, 6] | 3% [1, 5] | 3% [1, 6] | 3% [1, 5] | 2% [0, 4] | -3 pts [-6, -1] | -1 pts [-3, +0] | -0 pts [-3, +2] | -1 pts [-4, +2] | -2 pts [-4, +1] |
| Retrieval cost per question (search fees, search/rerank LLM; USD) | $0.00072 | $0.00000 | $0.00000 | $0.00695 | $0.00502 | $0.00505 | +0.00072 [+0.00071, +0.00074] | +0.00000 [+0.00000, +0.00000] | +0.00695 [+0.00683, +0.00706] | +0.00502 [+0.00492, +0.00511] | +0.00505 [+0.00495, +0.00513] |
| medsim LLM cost per question (Stages A–C, USD) | $0.00190 | $0.00256 | $0.00275 | $0.00226 | $0.00247 | $0.00295 | -0.00066 [-0.00087, -0.00046] | +0.00019 [-0.00002, +0.00042] | -0.00030 [-0.00053, -0.00007] | -0.00008 [-0.00033, +0.00015] | +0.00039 [+0.00015, +0.00064] |
| Total cost per question (USD) | $0.00262 | $0.00256 | $0.00275 | $0.00921 | $0.00750 | $0.00800 | +0.00007 [-0.00014, +0.00026] | +0.00019 [-0.00002, +0.00042] | +0.00665 [+0.00640, +0.00692] | +0.00494 [+0.00466, +0.00519] | +0.00544 [+0.00516, +0.00573] |
| Wall time per question (s) | 76.3 [71.5, 81.4] | 123.2 [115.9, 130.4] | 108.7 [102.7, 115.6] | 75.9 [71.0, 81.3] | 85.4 [80.2, 91.2] | 98.1 [91.6, 105.2] | -46.84 [-54.17, -39.58] | -14.48 [-21.37, -7.54] | -47.29 [-54.76, -39.92] | -37.74 [-45.45, -30.07] | -25.06 [-32.66, -17.06] |
| Time outside medsim's LLM calls per question (≈ retrieval; s) | 2.30 [2.09, 2.61] | 33.65 [30.86, 36.52] | 25.11 [23.82, 26.33] | 4.82 [4.59, 5.07] | 5.87 [5.56, 6.17] | 6.09 [5.79, 6.42] | -31.35 [-34.24, -28.62] | -8.54 [-11.50, -5.67] | -28.84 [-31.73, -26.06] | -27.79 [-30.65, -24.98] | -27.56 [-30.47, -24.75] |

## Set A only (hidden value; masked correctness)

| Metric | gemini_knowledge | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 0.98 [0.95, 1.00] | 7.83 [7.63, 8.00] | 7.72 [7.46, 7.94] | 7.73 [7.54, 7.88] | 7.60 [7.38, 7.77] | 7.57 [7.32, 7.77] | -6.85 [-7.02, -6.66] | -0.11 [-0.29, +0.00] | -0.10 [-0.32, +0.11] | -0.23 [-0.49, +0.01] | -0.26 [-0.52, -0.01] |
| Questions answered from literature | 94% [90, 97] | 33% [26, 41] | 50% [41, 58] | 34% [25, 43] | 36% [27, 45] | 65% [57, 74] | +60 pts [+51, +69] | +16 pts [+7, +26] | +1 pts [-9, +11] | +3 pts [-8, +14] | +32 pts [+20, +43] |
| Questions answered with a best guess (documents gave no usable basis) | 4% [1, 8] | 65% [57, 72] | 48% [40, 55] | 64% [55, 72] | 62% [53, 71] | 33% [24, 40] | -60 pts [-69, -51] | -17 pts [-27, -7] | -1 pts [-11, +10] | -3 pts [-14, +8] | -32 pts [-43, -20] |
| Masked correctness: exact (% of set A questions) | 45% [36, 54] | 42% [33, 51] | 40% [31, 49] | 48% [40, 57] | 46% [38, 55] | 45% [36, 53] | +4 pts [-6, +13] | -2 pts [-9, +5] | +6 pts [-2, +15] | +4 pts [-4, +12] | +3 pts [-6, +12] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 83% [76, 90] | 87% [81, 93] | 85% [79, 91] | 86% [79, 92] | 82% [74, 88] | 84% [77, 90] | -4 pts [-10, +1] | -2 pts [-8, +3] | -1 pts [-7, +4] | -6 pts [-11, -1] | -4 pts [-10, +3] |
| Masked correctness: different category (% of set A questions) | 16% [10, 23] | 11% [6, 18] | 13% [8, 20] | 13% [7, 19] | 16% [10, 24] | 15% [9, 21] | +5 pts [-1, +10] | +2 pts [-3, +8] | +1 pts [-3, +6] | +5 pts [+0, +10] | +4 pts [-2, +10] |
| Masked correctness: not comparable (% of set A questions) | 1% [0, 2] | 1% [0, 2] | 1% [0, 2] | 0% [0, 0] | 2% [0, 5] | 1% [0, 4] | +0 pts [-2, +2] | +0 pts [+0, +0] | -1 pts [-2, +0] | +1 pts [+0, +4] | +1 pts [-1, +3] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 0% [0, 0] | 1% [0, 2] | 1% [0, 2] | 1% [0, 4] | 0% [0, 0] | 0% [0, 0] | -1 pts [-2, +0] | +0 pts [-2, +2] | +1 pts [-2, +3] | -1 pts [-2, +0] | -1 pts [-2, +0] |

## Set B only (value never stated; factual consistency)

| Metric | gemini_knowledge | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 1.00 [0.99, 1.00] | 7.65 [7.43, 7.82] | 7.76 [7.59, 7.91] | 7.58 [7.38, 7.76] | 7.56 [7.38, 7.73] | 7.61 [7.44, 7.77] | -6.65 [-6.83, -6.44] | +0.12 [+0.00, +0.26] | -0.06 [-0.27, +0.14] | -0.09 [-0.31, +0.14] | -0.03 [-0.25, +0.18] |
| Questions answered from literature | 92% [88, 95] | 27% [21, 33] | 42% [36, 48] | 23% [18, 28] | 32% [26, 38] | 60% [54, 66] | +65 pts [+57, +71] | +15 pts [+8, +22] | -4 pts [-11, +3] | +5 pts [-3, +13] | +33 pts [+25, +41] |
| Questions answered with a best guess (documents gave no usable basis) | 8% [5, 11] | 69% [62, 75] | 56% [49, 61] | 72% [67, 78] | 65% [59, 71] | 36% [31, 42] | -61 pts [-68, -53] | -13 pts [-20, -6] | +4 pts [-3, +11] | -4 pts [-11, +4] | -32 pts [-40, -24] |
| Factual consistency: consistent (% of set B questions) | 99% [98, 100] | 96% [94, 98] | 97% [95, 99] | 96% [94, 98] | 97% [94, 99] | 97% [95, 99] | +3 pts [+1, +6] | +1 pts [+0, +3] | +0 pts [-2, +3] | +1 pts [-2, +4] | +1 pts [-1, +4] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 1] | 0% [0, 1] | 0% [0, 0] | 0% [0, 1] | 1% [0, 2] | 1% [0, 2] | +0 pts [-1, +1] | -0 pts [-1, +0] | +0 pts [+0, +0] | +0 pts [-1, +2] | +0 pts [-1, +2] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 0% [0, 1] | 4% [2, 6] | 3% [1, 5] | 3% [1, 6] | 3% [1, 5] | 2% [0, 4] | -3 pts [-6, -1] | -1 pts [-3, +0] | -0 pts [-3, +2] | -1 pts [-4, +2] | -2 pts [-4, +1] |

## Cost

All questions that ran.

| Method | Questions | Retrieval (search fees + search model) | medsim LLM (Stages A–C) | Total | Total per question | Median wall time |
|---|---|---|---|---|---|---|
| gemini_knowledge | 413 | $0.2994 | $0.7845 | $1.0839 | $0.00262 | 62.0 s |
| current | 413 | $0.0000 | $1.0568 | $1.0568 | $0.00256 | 106.3 s |
| improved_1to4 | 413 | $0.0000 | $1.1365 | $1.1365 | $0.00275 | 94.1 s |
| openrouter_exa_instant | 413 | $2.8700 | $0.9339 | $3.8038 | $0.00921 | 60.9 s |
| openrouter_parallel_basic | 413 | $2.0745 | $1.0218 | $3.0963 | $0.00750 | 72.3 s |
| openrouter_perplexity | 413 | $2.0860 | $1.2163 | $3.3024 | $0.00800 | 82.0 s |

## By subgroup (set A)

### Variable category

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| anthropometric | 22 | 55% | 55% | 50% | 55% | 55% | 59% | 9% | 9% | 5% | 9% | 5% | 9% |
| laboratory | 77 | 35% | 27% | 26% | 40% | 36% | 34% | 17% | 6% | 13% | 12% | 16% | 14% |
| vital_sign | 42 | 60% | 62% | 60% | 60% | 60% | 57% | 19% | 21% | 19% | 17% | 24% | 19% |

### True value (judge's category)

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| high | 72 | 40% | 33% | 30% | 45% | 37% | 40% | 17% | 12% | 17% | 15% | 18% | 15% |
| low | 34 | 45% | 42% | 44% | 45% | 50% | 39% | 6% | 3% | 0% | 6% | 6% | 12% |
| normal | 38 | 53% | 58% | 56% | 58% | 56% | 58% | 25% | 18% | 19% | 17% | 25% | 19% |
| not_applicable | 6 | 100% | 100% | 100% | 67% | 100% | 50% | 0% | 0% | 0% | 0% | 0% | 0% |
| unknown | 4 | – | 0% | 0% | 0% | – | – | – | 0% | 0% | 0% | – | – |

### Variable typical of the diagnosis

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| no | 83 | 48% | 48% | 47% | 47% | 49% | 46% | 24% | 17% | 19% | 17% | 23% | 19% |
| yes | 58 | 41% | 33% | 29% | 50% | 41% | 43% | 5% | 3% | 5% | 7% | 7% | 9% |

## Diagnostics

- **gemini_knowledge:** answer paths {'literature': 381, 'best_guess': 28, 'case_study': 3, 'query_builder_declined': 1}; source article removed for 0 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **current:** answer paths {'literature': 120, 'best_guess': 278, 'case_study': 4, 'query_builder_declined': 9, 'off_topic': 1, 'inconsistent_with_case': 1}; source article removed for 53 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **improved_1to4:** answer paths {'literature': 183, 'best_guess': 218, 'case_study': 4, 'query_builder_declined': 7, 'withheld': 1}; source article removed for 62 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_exa_instant:** answer paths {'literature': 111, 'best_guess': 287, 'case_study': 4, 'query_builder_declined': 9, 'synthesizer_unanswerable': 2}; source article removed for 43 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_parallel_basic:** answer paths {'literature': 138, 'best_guess': 264, 'case_study': 4, 'withheld': 1, 'query_builder_declined': 6}; source article removed for 37 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_perplexity:** answer paths {'best_guess': 145, 'literature': 256, 'case_study': 7, 'query_builder_declined': 3, 'off_topic': 1, 'synthesizer_unanswerable': 1}; source article removed for 38 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **Masked correctness:** 8 of 842 voted labels were "not comparable" (reported as their own label).
- **Judge errors (all attempts, all judges):** 89 judgment(s) failed; rerun the judge step to retry them.

## Judge panel agreement

| Metric | Answers | Unanimous | Majority | Tie broken by the main judge | Tie broken by the next judge | Fewer than all votes |
|---|---|---|---|---|---|---|
| masked correctness | 842 | 82% | 17% | 1% | 0% | 0 |
| factual consistency | 1593 | 99% | 1% | 0% | 0% | 0 |

- **masked correctness, `anthropic/claude-haiku-5.5` vs `z-ai/glm-5.3-flash`:** 738/842 identical labels, Cohen's κ = 0.80.
- **masked correctness, `anthropic/claude-haiku-5.5` vs `openai/gpt-6-luna`:** 724/842 identical labels, Cohen's κ = 0.78.
- **masked correctness, `z-ai/glm-5.3-flash` vs `openai/gpt-6-luna`:** 756/842 identical labels, Cohen's κ = 0.84.
- **factual consistency, `anthropic/claude-haiku-5.5` vs `z-ai/glm-5.3-flash`:** 1583/1593 identical labels, Cohen's κ = 0.50.
- **factual consistency, `anthropic/claude-haiku-5.5` vs `openai/gpt-6-luna`:** 1581/1593 identical labels, Cohen's κ = 0.14.
- **factual consistency, `z-ai/glm-5.3-flash` vs `openai/gpt-6-luna`:** 1587/1593 identical labels, Cohen's κ = 0.50.

## Benchmark spend

| Step | Cost (USD, OpenRouter usage.cost) |
|---|---|
| extract (case facts) | $0.0000 |
| redact + Stage A checks (accepted) | $0.0000 |
| redact + Stage A checks (rejected) | $0.0000 |
| run (all methods; search fees included) | $13.4797 |
| judge: masked correctness (google/gemini-3.5-flash-lite) | $1.5123 |
| judge: masked correctness (openai/gpt-6-luna) | $0.1590 |
| judge: masked correctness (qwen/qwen3.8-flash) | $0.3156 |
| judge: masked correctness (typesafe/jev-1.13) | $0.0353 |
| judge: masked correctness (z-ai/glm-5.3-flash) | $0.1226 |
| judge: masked correctness (anthropic/claude-haiku-5.5) | $0.2297 |
| judge: factual consistency (google/gemini-3.5-flash-lite) | $0.7032 |
| judge: factual consistency (openai/gpt-6-luna) | $0.1997 |
| judge: factual consistency (qwen/qwen3.8-flash) | $0.2704 |
| judge: factual consistency (typesafe/jev-1.13) | $0.0559 |
| judge: factual consistency (anthropic/claude-haiku-5.5) | $0.3186 |
| judge: factual consistency (z-ai/glm-5.3-flash) | $0.1592 |
| validation: controls (panel) | $0.0000 |
| validation: flipped truth (panel) | $0.0000 |
| **total** | **$17.5612** |

Cross-check: the OpenRouter key's usage counter, read right after each of the 8 benchmark commands, rose by $4.8524. The counter lags behind requests, so this undercounts; per-call usage.cost above is the accounting source.

