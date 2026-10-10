# Retrieval benchmark report

- Workspace: `environment/results/repeats/run_06/sets_ab`
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
| Documents returned per question | 0.93 [0.90, 0.95] | 7.76 [7.63, 7.88] | 7.88 [7.78, 7.96] | 7.70 [7.58, 7.81] | 7.70 [7.59, 7.80] | 7.63 [7.52, 7.74] | -6.84 [-6.95, -6.70] | +0.12 [+0.00, +0.25] | -0.06 [-0.20, +0.08] | -0.06 [-0.21, +0.10] | -0.13 [-0.26, +0.00] |
| Questions answered from literature | 85% [82, 89] | 31% [27, 36] | 51% [46, 56] | 31% [25, 35] | 32% [28, 37] | 59% [54, 64] | +54 pts [+49, +60] | +20 pts [+14, +26] | -1 pts [-7, +5] | +1 pts [-5, +7] | +28 pts [+21, +35] |
| Questions answered with a best guess (documents gave no usable basis) | 7% [5, 10] | 65% [61, 70] | 47% [42, 52] | 67% [63, 72] | 67% [62, 71] | 39% [34, 44] | -58 pts [-64, -53] | -18 pts [-24, -12] | +2 pts [-4, +8] | +1 pts [-5, +7] | -26 pts [-33, -20] |
| Masked correctness: exact (% of set A questions) | 40% [31, 48] | 45% [36, 54] | 38% [29, 47] | 43% [35, 52] | 38% [30, 47] | 46% [38, 56] | -5 pts [-13, +3] | -7 pts [-16, +1] | -1 pts [-9, +7] | -6 pts [-14, +1] | +1 pts [-6, +8] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 81% [74, 87] | 87% [80, 92] | 87% [81, 93] | 85% [78, 91] | 85% [79, 91] | 88% [82, 93] | -6 pts [-13, +0] | +0 pts [-5, +5] | -2 pts [-8, +4] | -2 pts [-8, +3] | +1 pts [-5, +6] |
| Masked correctness: different category (% of set A questions) | 13% [8, 20] | 11% [6, 18] | 13% [7, 19] | 15% [9, 21] | 14% [8, 21] | 11% [6, 17] | +2 pts [-2, +7] | +1 pts [-3, +6] | +4 pts [-2, +9] | +3 pts [-2, +9] | +0 pts [-5, +5] |
| Masked correctness: not comparable (% of set A questions) | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | +1 pts [+0, +2] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +1 pts [+0, +2] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 5% [2, 9] | 1% [0, 4] | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 0% [0, 0] | +4 pts [+0, +8] | -1 pts [-4, +0] | -1 pts [-4, +0] | -1 pts [-3, +1] | -1 pts [-4, +0] |
| Factual consistency: consistent (% of set B questions) | 94% [91, 96] | 96% [94, 98] | 98% [96, 100] | 97% [94, 99] | 99% [97, 100] | 97% [95, 99] | -3 pts [-6, +1] | +2 pts [-0, +5] | +0 pts [-2, +3] | +3 pts [+1, +5] | +1 pts [-1, +3] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 0] | 0% [0, 0] | 0% [0, 1] | 0% [0, 1] | 0% [0, 0] | 0% [0, 0] | +0 pts [+0, +0] | +0 pts [+0, +1] | +0 pts [+0, +1] | +0 pts [+0, +0] | +0 pts [+0, +0] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 6% [4, 9] | 4% [2, 6] | 1% [0, 3] | 3% [1, 5] | 1% [0, 3] | 3% [1, 5] | +3 pts [-1, +6] | -2 pts [-5, -0] | -1 pts [-3, +2] | -3 pts [-5, -1] | -1 pts [-3, +1] |
| Retrieval cost per question (search fees, search/rerank LLM; USD) | $0.00068 | $0.00000 | $0.00000 | $0.00702 | $0.00513 | $0.00509 | +0.00068 [+0.00066, +0.00070] | +0.00000 [+0.00000, +0.00000] | +0.00702 [+0.00691, +0.00711] | +0.00513 [+0.00508, +0.00517] | +0.00509 [+0.00501, +0.00515] |
| medsim LLM cost per question (Stages A–C, USD) | $0.00180 | $0.00224 | $0.00246 | $0.00215 | $0.00228 | $0.00258 | -0.00043 [-0.00064, -0.00024] | +0.00022 [+0.00003, +0.00041] | -0.00008 [-0.00027, +0.00010] | +0.00004 [-0.00016, +0.00022] | +0.00035 [+0.00012, +0.00057] |
| Total cost per question (USD) | $0.00249 | $0.00224 | $0.00246 | $0.00917 | $0.00741 | $0.00767 | +0.00025 [+0.00004, +0.00044] | +0.00022 [+0.00003, +0.00041] | +0.00694 [+0.00672, +0.00716] | +0.00517 [+0.00497, +0.00537] | +0.00543 [+0.00519, +0.00567] |
| Wall time per question (s) | 66.2 [62.5, 70.2] | 125.3 [119.6, 131.7] | 113.0 [106.8, 120.1] | 74.6 [70.1, 79.5] | 83.1 [78.2, 87.8] | 85.2 [79.7, 91.0] | -59.05 [-65.97, -52.59] | -12.25 [-19.31, -4.89] | -50.64 [-57.47, -44.31] | -42.16 [-49.59, -35.33] | -40.08 [-48.12, -32.26] |
| Time outside medsim's LLM calls per question (≈ retrieval; s) | 5.39 [4.69, 6.21] | 48.33 [44.62, 52.20] | 20.62 [19.32, 21.95] | 5.49 [5.19, 5.79] | 6.59 [6.28, 6.91] | 6.45 [6.14, 6.79] | -42.94 [-46.76, -39.22] | -27.71 [-31.83, -23.87] | -42.84 [-46.70, -39.12] | -41.74 [-45.72, -38.00] | -41.88 [-45.83, -38.22] |

## Set A only (hidden value; masked correctness)

| Metric | gemini_knowledge | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 0.94 [0.90, 0.98] | 7.94 [7.82, 8.00] | 7.94 [7.82, 8.00] | 7.76 [7.62, 7.87] | 7.68 [7.51, 7.81] | 7.63 [7.45, 7.76] | -7.00 [-7.08, -6.88] | +0.00 [+0.00, +0.00] | -0.18 [-0.26, -0.11] | -0.26 [-0.46, -0.08] | -0.31 [-0.40, -0.22] |
| Questions answered from literature | 88% [82, 93] | 31% [23, 39] | 62% [54, 70] | 39% [31, 48] | 37% [29, 45] | 60% [51, 67] | +57 pts [+47, +66] | +31 pts [+22, +40] | +8 pts [-1, +18] | +6 pts [-4, +15] | +28 pts [+18, +39] |
| Questions answered with a best guess (documents gave no usable basis) | 6% [3, 11] | 67% [59, 75] | 37% [29, 45] | 60% [52, 69] | 62% [54, 70] | 40% [32, 48] | -60 pts [-70, -51] | -30 pts [-39, -21] | -6 pts [-16, +3] | -4 pts [-14, +5] | -27 pts [-37, -17] |
| Masked correctness: exact (% of set A questions) | 40% [31, 48] | 45% [36, 54] | 38% [29, 47] | 43% [35, 52] | 38% [30, 47] | 46% [38, 56] | -5 pts [-13, +3] | -7 pts [-16, +1] | -1 pts [-9, +7] | -6 pts [-14, +1] | +1 pts [-6, +8] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 81% [74, 87] | 87% [80, 92] | 87% [81, 93] | 85% [78, 91] | 85% [79, 91] | 88% [82, 93] | -6 pts [-13, +0] | +0 pts [-5, +5] | -2 pts [-8, +4] | -2 pts [-8, +3] | +1 pts [-5, +6] |
| Masked correctness: different category (% of set A questions) | 13% [8, 20] | 11% [6, 18] | 13% [7, 19] | 15% [9, 21] | 14% [8, 21] | 11% [6, 17] | +2 pts [-2, +7] | +1 pts [-3, +6] | +4 pts [-2, +9] | +3 pts [-2, +9] | +0 pts [-5, +5] |
| Masked correctness: not comparable (% of set A questions) | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | +1 pts [+0, +2] | +0 pts [+0, +0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +1 pts [+0, +2] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 5% [2, 9] | 1% [0, 4] | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 0% [0, 0] | +4 pts [+0, +8] | -1 pts [-4, +0] | -1 pts [-4, +0] | -1 pts [-3, +1] | -1 pts [-4, +0] |

## Set B only (value never stated; factual consistency)

| Metric | gemini_knowledge | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 0.92 [0.89, 0.95] | 7.67 [7.45, 7.84] | 7.85 [7.70, 7.97] | 7.67 [7.50, 7.82] | 7.72 [7.59, 7.83] | 7.63 [7.47, 7.77] | -6.75 [-6.92, -6.54] | +0.18 [+0.00, +0.40] | +0.00 [-0.21, +0.21] | +0.05 [-0.15, +0.25] | -0.04 [-0.22, +0.16] |
| Questions answered from literature | 84% [80, 88] | 31% [25, 38] | 46% [39, 52] | 26% [20, 32] | 30% [24, 36] | 59% [52, 65] | +53 pts [+45, +61] | +14 pts [+6, +22] | -5 pts [-13, +3] | -1 pts [-9, +6] | +28 pts [+19, +36] |
| Questions answered with a best guess (documents gave no usable basis) | 8% [5, 11] | 65% [58, 71] | 53% [46, 59] | 71% [65, 77] | 69% [63, 74] | 39% [32, 45] | -57 pts [-64, -50] | -12 pts [-20, -4] | +6 pts [-2, +14] | +4 pts [-3, +12] | -26 pts [-35, -17] |
| Factual consistency: consistent (% of set B questions) | 94% [91, 96] | 96% [94, 98] | 98% [96, 100] | 97% [94, 99] | 99% [97, 100] | 97% [95, 99] | -3 pts [-6, +1] | +2 pts [-0, +5] | +0 pts [-2, +3] | +3 pts [+1, +5] | +1 pts [-1, +3] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 0] | 0% [0, 0] | 0% [0, 1] | 0% [0, 1] | 0% [0, 0] | 0% [0, 0] | +0 pts [+0, +0] | +0 pts [+0, +1] | +0 pts [+0, +1] | +0 pts [+0, +0] | +0 pts [+0, +0] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 6% [4, 9] | 4% [2, 6] | 1% [0, 3] | 3% [1, 5] | 1% [0, 3] | 3% [1, 5] | +3 pts [-1, +6] | -2 pts [-5, -0] | -1 pts [-3, +2] | -3 pts [-5, -1] | -1 pts [-3, +1] |

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
| anthropometric | 22 | 45% | 64% | 50% | 50% | 55% | 64% | 0% | 5% | 0% | 5% | 9% | 5% |
| laboratory | 77 | 30% | 29% | 29% | 34% | 22% | 31% | 14% | 12% | 14% | 17% | 13% | 12% |
| vital_sign | 42 | 55% | 64% | 48% | 57% | 60% | 64% | 19% | 14% | 17% | 17% | 19% | 14% |

### True value (judge's category)

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| high | 73 | 37% | 37% | 24% | 33% | 27% | 37% | 13% | 16% | 15% | 16% | 16% | 13% |
| low | 34 | 48% | 40% | 44% | 48% | 48% | 44% | 3% | 3% | 6% | 6% | 3% | 3% |
| normal | 44 | 43% | 64% | 57% | 56% | 51% | 65% | 24% | 10% | 14% | 21% | 21% | 16% |
| not_applicable | 1 | 100% | – | 100% | 100% | – | 100% | 0% | – | 0% | 0% | – | 0% |
| unknown | 10 | 0% | 0% | – | – | 0% | – | 0% | 0% | – | – | 0% | – |

### Variable typical of the diagnosis

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| no | 83 | 40% | 52% | 48% | 46% | 42% | 52% | 19% | 17% | 17% | 18% | 20% | 17% |
| yes | 58 | 40% | 34% | 22% | 40% | 33% | 38% | 5% | 3% | 7% | 10% | 5% | 3% |

## Diagnostics

- **gemini_knowledge:** answer paths {'literature': 353, 'best_guess': 30, 'case_study': 6, 'query_builder_declined': 5, 'all_sources_failed': 18, 'off_topic': 1}; source article removed for 0 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **current:** answer paths {'literature': 129, 'best_guess': 270, 'case_study': 2, 'synthesizer_unanswerable': 2, 'query_builder_declined': 9, 'off_topic': 1}; source article removed for 52 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **improved_1to4:** answer paths {'literature': 212, 'best_guess': 195, 'case_study': 2, 'query_builder_declined': 4}; source article removed for 53 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_exa_instant:** answer paths {'best_guess': 278, 'literature': 126, 'case_study': 1, 'query_builder_declined': 7, 'off_topic': 1}; source article removed for 46 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_parallel_basic:** answer paths {'literature': 134, 'best_guess': 275, 'query_builder_declined': 4}; source article removed for 37 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_perplexity:** answer paths {'best_guess': 161, 'literature': 244, 'case_study': 1, 'query_builder_declined': 6, 'off_topic': 1}; source article removed for 44 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **Masked correctness:** 2 of 836 voted labels were "not comparable" (reported as their own label).
- **Judge errors (all attempts, all judges):** 124 judgment(s) failed; rerun the judge step to retry them.

## Judge panel agreement

| Metric | Answers | Unanimous | Majority | Tie broken by the main judge | Tie broken by the next judge | Fewer than all votes |
|---|---|---|---|---|---|---|
| masked correctness | 836 | 73% | 26% | 1% | 0% | 0 |
| factual consistency | 1583 | 99% | 1% | 0% | 0% | 0 |

- **masked correctness, `google/gemini-3.5-flash-lite` vs `qwen/qwen3.8-flash`:** 663/836 identical labels, Cohen's κ = 0.66.
- **masked correctness, `google/gemini-3.5-flash-lite` vs `openai/gpt-6-luna`:** 638/836 identical labels, Cohen's κ = 0.61.
- **masked correctness, `qwen/qwen3.8-flash` vs `openai/gpt-6-luna`:** 750/836 identical labels, Cohen's κ = 0.83.
- **factual consistency, `google/gemini-3.5-flash-lite` vs `qwen/qwen3.8-flash`:** 1573/1583 identical labels, Cohen's κ = 0.16.
- **factual consistency, `google/gemini-3.5-flash-lite` vs `openai/gpt-6-luna`:** 1577/1583 identical labels, Cohen's κ = 0.25.
- **factual consistency, `qwen/qwen3.8-flash` vs `openai/gpt-6-luna`:** 1575/1583 identical labels, Cohen's κ = 0.33.

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
| judge: factual consistency (google/gemini-3.5-flash-lite) | $0.6989 |
| judge: factual consistency (openai/gpt-6-luna) | $0.1984 |
| judge: factual consistency (qwen/qwen3.8-flash) | $0.2766 |
| validation: controls (panel) | $0.0000 |
| validation: flipped truth (panel) | $0.0000 |
| **total** | **$15.3297** |

Cross-check: the OpenRouter key's usage counter, read right after each of the 4 benchmark commands, rose by $0.8846. The counter lags behind requests, so this undercounts; per-call usage.cost above is the accounting source.

