# Retrieval benchmark report

- Workspace: `environment/results/repeats/run_06/sets_ab`
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
| Documents returned per question | 0.93 [0.90, 0.95] | 7.76 [7.62, 7.88] | 7.88 [7.78, 7.96] | 7.70 [7.57, 7.81] | 7.70 [7.59, 7.80] | 7.63 [7.51, 7.75] | -6.84 [-6.95, -6.70] | +0.12 [+0.00, +0.26] | -0.06 [-0.21, +0.08] | -0.06 [-0.21, +0.10] | -0.13 [-0.27, +0.01] |
| Questions answered from literature | 85% [82, 89] | 31% [27, 36] | 51% [46, 56] | 31% [26, 35] | 32% [28, 37] | 59% [54, 64] | +54 pts [+49, +60] | +20 pts [+14, +26] | -1 pts [-7, +5] | +1 pts [-5, +7] | +28 pts [+21, +35] |
| Questions answered with a best guess (documents gave no usable basis) | 7% [5, 10] | 65% [61, 70] | 47% [42, 52] | 67% [62, 72] | 67% [62, 71] | 39% [34, 44] | -58 pts [-64, -53] | -18 pts [-24, -12] | +2 pts [-4, +8] | +1 pts [-5, +7] | -26 pts [-33, -20] |
| Masked correctness: exact (% of set A questions) | 44% [35, 53] | 48% [38, 57] | 40% [31, 49] | 48% [39, 56] | 43% [34, 52] | 48% [38, 57] | -4 pts [-10, +4] | -8 pts [-16, +0] | +0 pts [-7, +8] | -4 pts [-12, +3] | +0 pts [-7, +7] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 82% [75, 88] | 89% [82, 94] | 87% [80, 92] | 86% [80, 92] | 85% [79, 91] | 87% [80, 92] | -7 pts [-13, -1] | -2 pts [-6, +2] | -3 pts [-8, +2] | -4 pts [-9, +2] | -2 pts [-7, +2] |
| Masked correctness: different category (% of set A questions) | 13% [7, 19] | 10% [5, 16] | 13% [8, 20] | 14% [8, 20] | 13% [8, 20] | 13% [7, 19] | +3 pts [-3, +8] | +4 pts [-1, +8] | +4 pts [-1, +9] | +4 pts [-1, +9] | +3 pts [-1, +8] |
| Masked correctness: not comparable (% of set A questions) | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 1% [0, 2] | +1 pts [+0, +2] | +0 pts [+0, +0] | +0 pts [+0, +0] | +1 pts [+0, +2] | +1 pts [+0, +2] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 5% [2, 9] | 1% [0, 4] | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 0% [0, 0] | +4 pts [-1, +8] | -1 pts [-4, +0] | -1 pts [-4, +0] | -1 pts [-3, +1] | -1 pts [-4, +0] |
| Factual consistency: consistent (% of set B questions) | 94% [91, 96] | 96% [93, 98] | 98% [96, 99] | 97% [94, 99] | 98% [97, 100] | 97% [95, 99] | -2 pts [-5, +1] | +2 pts [-0, +4] | +1 pts [-2, +3] | +2 pts [+0, +5] | +1 pts [-1, +4] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 0] | 0% [0, 1] | 1% [0, 2] | 0% [0, 1] | 1% [0, 2] | 0% [0, 1] | -0 pts [-1, +0] | +0 pts [+0, +1] | +0 pts [-1, +1] | +0 pts [-1, +2] | +0 pts [-1, +1] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 6% [4, 9] | 4% [2, 6] | 1% [0, 3] | 3% [1, 5] | 1% [0, 3] | 3% [1, 5] | +3 pts [-1, +6] | -2 pts [-5, +0] | -1 pts [-3, +2] | -3 pts [-5, -1] | -1 pts [-3, +1] |
| Retrieval cost per question (search fees, search/rerank LLM; USD) | $0.00068 | $0.00000 | $0.00000 | $0.00702 | $0.00513 | $0.00509 | +0.00068 [+0.00066, +0.00070] | +0.00000 [+0.00000, +0.00000] | +0.00702 [+0.00691, +0.00711] | +0.00513 [+0.00508, +0.00517] | +0.00509 [+0.00501, +0.00515] |
| medsim LLM cost per question (Stages A–C, USD) | $0.00180 | $0.00224 | $0.00246 | $0.00215 | $0.00228 | $0.00258 | -0.00043 [-0.00064, -0.00023] | +0.00022 [+0.00004, +0.00041] | -0.00008 [-0.00027, +0.00010] | +0.00004 [-0.00016, +0.00023] | +0.00035 [+0.00012, +0.00057] |
| Total cost per question (USD) | $0.00249 | $0.00224 | $0.00246 | $0.00917 | $0.00741 | $0.00767 | +0.00025 [+0.00004, +0.00045] | +0.00022 [+0.00004, +0.00041] | +0.00694 [+0.00671, +0.00716] | +0.00517 [+0.00497, +0.00537] | +0.00543 [+0.00520, +0.00568] |
| Wall time per question (s) | 66.2 [62.7, 70.2] | 125.3 [119.2, 131.7] | 113.0 [106.5, 120.0] | 74.6 [70.1, 79.4] | 83.1 [78.2, 87.9] | 85.2 [79.7, 91.2] | -59.05 [-65.80, -52.54] | -12.25 [-19.65, -4.46] | -50.64 [-57.43, -44.13] | -42.16 [-49.57, -34.97] | -40.08 [-48.05, -32.13] |
| Time outside medsim's LLM calls per question (≈ retrieval; s) | 5.39 [4.70, 6.19] | 48.33 [44.59, 52.32] | 20.62 [19.27, 21.94] | 5.49 [5.18, 5.80] | 6.59 [6.28, 6.92] | 6.45 [6.14, 6.78] | -42.94 [-46.77, -39.22] | -27.71 [-31.76, -23.83] | -42.84 [-46.77, -39.12] | -41.74 [-45.76, -37.99] | -41.88 [-45.87, -38.17] |

## Set A only (hidden value; masked correctness)

| Metric | gemini_knowledge | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 0.94 [0.90, 0.98] | 7.94 [7.82, 8.00] | 7.94 [7.82, 8.00] | 7.76 [7.62, 7.87] | 7.68 [7.51, 7.81] | 7.63 [7.46, 7.76] | -7.00 [-7.08, -6.88] | +0.00 [+0.00, +0.00] | -0.18 [-0.26, -0.11] | -0.26 [-0.46, -0.08] | -0.31 [-0.40, -0.22] |
| Questions answered from literature | 88% [82, 93] | 31% [23, 39] | 62% [54, 70] | 39% [31, 48] | 37% [29, 45] | 60% [51, 68] | +57 pts [+47, +66] | +31 pts [+21, +40] | +8 pts [-2, +18] | +6 pts [-4, +15] | +28 pts [+18, +39] |
| Questions answered with a best guess (documents gave no usable basis) | 6% [3, 11] | 67% [58, 74] | 37% [29, 45] | 60% [52, 68] | 62% [55, 70] | 40% [32, 48] | -60 pts [-70, -51] | -30 pts [-39, -20] | -6 pts [-16, +3] | -4 pts [-14, +6] | -27 pts [-38, -17] |
| Masked correctness: exact (% of set A questions) | 44% [35, 53] | 48% [38, 57] | 40% [31, 49] | 48% [39, 56] | 43% [34, 52] | 48% [38, 57] | -4 pts [-10, +4] | -8 pts [-16, +0] | +0 pts [-7, +8] | -4 pts [-12, +3] | +0 pts [-7, +7] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 82% [75, 88] | 89% [82, 94] | 87% [80, 92] | 86% [80, 92] | 85% [79, 91] | 87% [80, 92] | -7 pts [-13, -1] | -2 pts [-6, +2] | -3 pts [-8, +2] | -4 pts [-9, +2] | -2 pts [-7, +2] |
| Masked correctness: different category (% of set A questions) | 13% [7, 19] | 10% [5, 16] | 13% [8, 20] | 14% [8, 20] | 13% [8, 20] | 13% [7, 19] | +3 pts [-3, +8] | +4 pts [-1, +8] | +4 pts [-1, +9] | +4 pts [-1, +9] | +3 pts [-1, +8] |
| Masked correctness: not comparable (% of set A questions) | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 1% [0, 2] | +1 pts [+0, +2] | +0 pts [+0, +0] | +0 pts [+0, +0] | +1 pts [+0, +2] | +1 pts [+0, +2] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 5% [2, 9] | 1% [0, 4] | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 0% [0, 0] | +4 pts [-1, +8] | -1 pts [-4, +0] | -1 pts [-4, +0] | -1 pts [-3, +1] | -1 pts [-4, +0] |

## Set B only (value never stated; factual consistency)

| Metric | gemini_knowledge | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 0.92 [0.89, 0.95] | 7.67 [7.47, 7.84] | 7.85 [7.71, 7.97] | 7.67 [7.50, 7.82] | 7.72 [7.59, 7.83] | 7.63 [7.46, 7.77] | -6.75 [-6.92, -6.56] | +0.18 [-0.01, +0.39] | +0.00 [-0.21, +0.21] | +0.05 [-0.15, +0.25] | -0.04 [-0.23, +0.15] |
| Questions answered from literature | 84% [80, 88] | 31% [25, 37] | 46% [39, 52] | 26% [21, 32] | 30% [25, 36] | 59% [52, 65] | +53 pts [+46, +61] | +14 pts [+6, +22] | -5 pts [-13, +3] | -1 pts [-9, +6] | +28 pts [+19, +36] |
| Questions answered with a best guess (documents gave no usable basis) | 8% [5, 11] | 65% [58, 71] | 53% [46, 59] | 71% [65, 77] | 69% [63, 74] | 39% [32, 45] | -57 pts [-64, -50] | -12 pts [-20, -4] | +6 pts [-2, +14] | +4 pts [-4, +12] | -26 pts [-35, -17] |
| Factual consistency: consistent (% of set B questions) | 94% [91, 96] | 96% [93, 98] | 98% [96, 99] | 97% [94, 99] | 98% [97, 100] | 97% [95, 99] | -2 pts [-5, +1] | +2 pts [-0, +4] | +1 pts [-2, +3] | +2 pts [+0, +5] | +1 pts [-1, +4] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 0] | 0% [0, 1] | 1% [0, 2] | 0% [0, 1] | 1% [0, 2] | 0% [0, 1] | -0 pts [-1, +0] | +0 pts [+0, +1] | +0 pts [-1, +1] | +0 pts [-1, +2] | +0 pts [-1, +1] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 6% [4, 9] | 4% [2, 6] | 1% [0, 3] | 3% [1, 5] | 1% [0, 3] | 3% [1, 5] | +3 pts [-1, +6] | -2 pts [-5, +0] | -1 pts [-3, +2] | -3 pts [-5, -1] | -1 pts [-3, +1] |

## Cost

All questions that ran.

| Method | Questions | Retrieval (search fees + search model) | medsim LLM (Stages A–C) | Total | Total per question | Median wall time |
|---|---|---|---|---|---|---|
| gemini_knowledge | 413 | $0.2824 | $0.7441 | $1.0265 | $0.00249 | 58.2 s |
| current | 413 | $0.0000 | $0.9233 | $0.9233 | $0.00224 | 115.6 s |
| improved_1to4 | 413 | $0.0000 | $1.0151 | $1.0151 | $0.00246 | 99.0 s |
| openrouter_exa_instant | 413 | $2.8991 | $0.8889 | $3.7880 | $0.00917 | 62.2 s |
| openrouter_parallel_basic | 413 | $2.1206 | $0.9397 | $3.0603 | $0.00741 | 69.8 s |
| openrouter_perplexity | 413 | $2.1011 | $1.0658 | $3.1670 | $0.00767 | 68.7 s |

## By subgroup (set A)

### Variable category

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| anthropometric | 22 | 55% | 64% | 45% | 55% | 55% | 59% | 0% | 0% | 9% | 5% | 9% | 9% |
| laboratory | 77 | 29% | 31% | 32% | 36% | 27% | 34% | 17% | 12% | 12% | 16% | 12% | 13% |
| vital_sign | 42 | 67% | 69% | 50% | 64% | 67% | 67% | 12% | 12% | 19% | 17% | 19% | 14% |

### True value (judge's category)

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| high | 72 | 38% | 41% | 26% | 35% | 30% | 39% | 17% | 13% | 17% | 15% | 17% | 16% |
| low | 34 | 44% | 41% | 47% | 58% | 55% | 44% | 6% | 3% | 9% | 9% | 3% | 6% |
| normal | 37 | 59% | 66% | 57% | 60% | 57% | 66% | 15% | 11% | 11% | 17% | 17% | 14% |
| not_applicable | 4 | 100% | 100% | 100% | 100% | 100% | 100% | 0% | 0% | 0% | 0% | 0% | 0% |
| unknown | 10 | 0% | 0% | – | – | 0% | – | 0% | 0% | – | – | 0% | – |

### Variable typical of the diagnosis

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| no | 83 | 47% | 53% | 47% | 49% | 47% | 52% | 18% | 14% | 19% | 18% | 19% | 18% |
| yes | 58 | 40% | 40% | 29% | 45% | 38% | 41% | 5% | 3% | 5% | 9% | 5% | 5% |

## Diagnostics

- **gemini_knowledge:** answer paths {'literature': 353, 'best_guess': 30, 'case_study': 6, 'query_builder_declined': 5, 'all_sources_failed': 18, 'off_topic': 1}; source article removed for 0 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **current:** answer paths {'literature': 129, 'best_guess': 270, 'case_study': 2, 'synthesizer_unanswerable': 2, 'query_builder_declined': 9, 'off_topic': 1}; source article removed for 52 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **improved_1to4:** answer paths {'literature': 212, 'best_guess': 195, 'case_study': 2, 'query_builder_declined': 4}; source article removed for 53 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_exa_instant:** answer paths {'best_guess': 278, 'literature': 126, 'case_study': 1, 'query_builder_declined': 7, 'off_topic': 1}; source article removed for 46 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_parallel_basic:** answer paths {'literature': 134, 'best_guess': 275, 'query_builder_declined': 4}; source article removed for 37 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_perplexity:** answer paths {'best_guess': 161, 'literature': 244, 'case_study': 1, 'query_builder_declined': 6, 'off_topic': 1}; source article removed for 44 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **Masked correctness:** 3 of 836 voted labels were "not comparable" (reported as their own label).
- **Judge errors (all attempts, all judges):** 124 judgment(s) failed; rerun the judge step to retry them.

## Judge panel agreement

| Metric | Answers | Unanimous | Majority | Tie broken by the main judge | Tie broken by the next judge | Fewer than all votes |
|---|---|---|---|---|---|---|
| masked correctness | 836 | 82% | 18% | 0% | 0% | 0 |
| factual consistency | 1583 | 99% | 1% | 0% | 0% | 0 |

- **masked correctness, `anthropic/claude-haiku-5.5` vs `z-ai/glm-5.3-flash`:** 737/836 identical labels, Cohen's κ = 0.81.
- **masked correctness, `anthropic/claude-haiku-5.5` vs `openai/gpt-6-luna`:** 722/836 identical labels, Cohen's κ = 0.78.
- **masked correctness, `z-ai/glm-5.3-flash` vs `openai/gpt-6-luna`:** 741/836 identical labels, Cohen's κ = 0.81.
- **factual consistency, `anthropic/claude-haiku-5.5` vs `z-ai/glm-5.3-flash`:** 1568/1583 identical labels, Cohen's κ = 0.48.
- **factual consistency, `anthropic/claude-haiku-5.5` vs `openai/gpt-6-luna`:** 1564/1583 identical labels, Cohen's κ = 0.17.
- **factual consistency, `z-ai/glm-5.3-flash` vs `openai/gpt-6-luna`:** 1573/1583 identical labels, Cohen's κ = 0.28.

## Benchmark spend

| Step | Cost (USD, OpenRouter usage.cost) |
|---|---|
| extract (case facts) | $0.0000 |
| redact + Stage A checks (accepted) | $0.0000 |
| redact + Stage A checks (rejected) | $0.0000 |
| run (all methods; search fees included) | $12.9800 |
| judge: masked correctness (google/gemini-3.5-flash-lite) | $0.6861 |
| judge: masked correctness (openai/gpt-6-luna) | $0.1606 |
| judge: masked correctness (qwen/qwen3.8-flash) | $0.3289 |
| judge: masked correctness (typesafe/jev-1.13) | $0.0350 |
| judge: masked correctness (z-ai/glm-5.3-flash) | $0.1306 |
| judge: masked correctness (anthropic/claude-haiku-5.5) | $0.2298 |
| judge: factual consistency (google/gemini-3.5-flash-lite) | $0.6989 |
| judge: factual consistency (openai/gpt-6-luna) | $0.1984 |
| judge: factual consistency (qwen/qwen3.8-flash) | $0.2766 |
| judge: factual consistency (typesafe/jev-1.13) | $0.0556 |
| judge: factual consistency (anthropic/claude-haiku-5.5) | $0.3182 |
| judge: factual consistency (z-ai/glm-5.3-flash) | $0.1605 |
| validation: controls (panel) | $0.0000 |
| validation: flipped truth (panel) | $0.0000 |
| **total** | **$16.2594** |

Cross-check: the OpenRouter key's usage counter, read right after each of the 6 benchmark commands, rose by $2.5149. The counter lags behind requests, so this undercounts; per-call usage.cost above is the accounting source.

