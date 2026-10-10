# Retrieval benchmark report

- Workspace: `environment/results/repeats/run_04/sets_ab`
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
| Documents returned per question | 0.97 [0.96, 0.99] | 7.73 [7.58, 7.86] | 7.86 [7.75, 7.96] | 7.69 [7.54, 7.80] | 7.48 [7.31, 7.63] | 7.61 [7.47, 7.71] | -6.76 [-6.88, -6.61] | +0.14 [+0.00, +0.29] | -0.04 [-0.18, +0.10] | -0.25 [-0.41, -0.10] | -0.12 [-0.29, +0.04] |
| Questions answered from literature | 90% [87, 92] | 31% [26, 35] | 42% [37, 47] | 31% [26, 36] | 33% [28, 37] | 62% [57, 66] | +59 pts [+53, +64] | +11 pts [+5, +17] | +0 pts [-6, +7] | +2 pts [-4, +8] | +31 pts [+24, +37] |
| Questions answered with a best guess (documents gave no usable basis) | 8% [5, 11] | 66% [61, 70] | 56% [51, 61] | 66% [62, 71] | 63% [58, 68] | 36% [31, 41] | -58 pts [-64, -52] | -9 pts [-16, -3] | +0 pts [-6, +7] | -3 pts [-9, +3] | -30 pts [-36, -23] |
| Masked correctness: exact (% of set A questions) | 43% [34, 51] | 42% [33, 50] | 40% [32, 49] | 36% [28, 45] | 47% [38, 56] | 37% [28, 45] | +1 pts [-8, +9] | -1 pts [-9, +7] | -6 pts [-14, +3] | +5 pts [-3, +14] | -5 pts [-14, +4] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 86% [79, 92] | 84% [78, 90] | 84% [77, 90] | 85% [78, 91] | 83% [76, 89] | 83% [76, 89] | +1 pts [-4, +8] | -1 pts [-7, +6] | +1 pts [-5, +7] | -1 pts [-7, +4] | -1 pts [-7, +4] |
| Masked correctness: different category (% of set A questions) | 13% [7, 20] | 16% [10, 22] | 16% [10, 23] | 13% [8, 20] | 13% [8, 20] | 16% [10, 23] | -2 pts [-8, +3] | +0 pts [-7, +7] | -2 pts [-8, +4] | -2 pts [-7, +3] | +0 pts [-5, +5] |
| Masked correctness: not comparable (% of set A questions) | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 3% [1, 6] | 1% [0, 4] | +1 pts [+0, +2] | +0 pts [+0, +0] | +1 pts [+0, +2] | +3 pts [+1, +6] | +1 pts [+0, +4] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 1% [0, 2] | 1% [0, 2] | 0% [0, 0] | +0 pts [+0, +0] | +1 pts [+0, +2] | +1 pts [+0, +2] | +1 pts [+0, +2] | +0 pts [+0, +0] |
| Factual consistency: consistent (% of set B questions) | 98% [96, 99] | 97% [94, 99] | 98% [96, 99] | 97% [95, 99] | 96% [93, 98] | 98% [96, 99] | +1 pts [-1, +4] | +1 pts [-1, +4] | +0 pts [-2, +3] | -1 pts [-3, +1] | +1 pts [-1, +4] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 0] | 0% [0, 0] | 0% [0, 1] | 0% [0, 0] | 1% [0, 2] | 0% [0, 0] | +0 pts [+0, +0] | +0 pts [+0, +1] | +0 pts [+0, +0] | +1 pts [+0, +2] | +0 pts [+0, +0] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 2% [1, 4] | 3% [1, 6] | 2% [0, 4] | 3% [1, 5] | 4% [2, 6] | 2% [1, 4] | -1 pts [-4, +1] | -1 pts [-4, +1] | -0 pts [-3, +2] | +0 pts [-2, +3] | -1 pts [-4, +1] |
| Retrieval cost per question (search fees, search/rerank LLM; USD) | $0.00071 | $0.00000 | $0.00000 | $0.00700 | $0.00496 | $0.00506 | +0.00071 [+0.00070, +0.00073] | +0.00000 [+0.00000, +0.00000] | +0.00700 [+0.00688, +0.00710] | +0.00496 [+0.00485, +0.00506] | +0.00506 [+0.00497, +0.00513] |
| medsim LLM cost per question (Stages A–C, USD) | $0.00199 | $0.00219 | $0.00176 | $0.00152 | $0.00196 | $0.00223 | -0.00020 [-0.00039, -0.00001] | -0.00043 [-0.00065, -0.00022] | -0.00067 [-0.00088, -0.00046] | -0.00023 [-0.00045, -0.00000] | +0.00004 [-0.00021, +0.00028] |
| Total cost per question (USD) | $0.00271 | $0.00219 | $0.00176 | $0.00852 | $0.00692 | $0.00729 | +0.00052 [+0.00032, +0.00070] | -0.00043 [-0.00065, -0.00022] | +0.00633 [+0.00609, +0.00656] | +0.00473 [+0.00447, +0.00498] | +0.00510 [+0.00484, +0.00535] |
| Wall time per question (s) | 69.7 [66.1, 73.3] | 126.8 [118.9, 136.0] | 108.8 [103.3, 115.4] | 65.2 [61.6, 69.4] | 87.7 [81.9, 94.0] | 93.5 [87.6, 99.4] | -57.10 [-65.75, -49.95] | -17.95 [-26.85, -8.89] | -61.63 [-70.92, -53.76] | -39.06 [-48.64, -29.53] | -33.26 [-43.42, -23.76] |
| Time outside medsim's LLM calls per question (≈ retrieval; s) | 2.36 [2.23, 2.52] | 40.69 [37.14, 44.51] | 38.27 [36.64, 39.80] | 5.25 [5.00, 5.48] | 5.96 [5.67, 6.23] | 6.71 [6.30, 7.27] | -38.33 [-42.14, -34.84] | -2.42 [-6.09, +1.00] | -35.44 [-39.39, -31.87] | -34.73 [-38.58, -31.26] | -33.98 [-37.90, -30.50] |

## Set A only (hidden value; masked correctness)

| Metric | gemini_knowledge | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 0.99 [0.98, 1.00] | 7.89 [7.72, 8.00] | 7.89 [7.72, 8.00] | 7.72 [7.55, 7.86] | 7.26 [6.97, 7.55] | 7.50 [7.25, 7.71] | -6.89 [-7.01, -6.72] | +0.00 [-0.17, +0.17] | -0.16 [-0.34, +0.01] | -0.62 [-0.94, -0.33] | -0.38 [-0.65, -0.14] |
| Questions answered from literature | 89% [84, 95] | 35% [27, 43] | 45% [36, 53] | 42% [34, 51] | 35% [27, 45] | 58% [50, 66] | +55 pts [+44, +64] | +10 pts [-1, +20] | +7 pts [-3, +17] | +1 pts [-10, +11] | +23 pts [+13, +34] |
| Questions answered with a best guess (documents gave no usable basis) | 10% [4, 16] | 64% [55, 72] | 53% [45, 62] | 56% [47, 64] | 59% [49, 68] | 39% [31, 48] | -54 pts [-64, -44] | -11 pts [-21, +1] | -8 pts [-18, +3] | -5 pts [-16, +6] | -25 pts [-36, -14] |
| Masked correctness: exact (% of set A questions) | 43% [34, 51] | 42% [33, 50] | 40% [32, 49] | 36% [28, 45] | 47% [38, 56] | 37% [28, 45] | +1 pts [-8, +9] | -1 pts [-9, +7] | -6 pts [-14, +3] | +5 pts [-3, +14] | -5 pts [-14, +4] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 86% [79, 92] | 84% [78, 90] | 84% [77, 90] | 85% [78, 91] | 83% [76, 89] | 83% [76, 89] | +1 pts [-4, +8] | -1 pts [-7, +6] | +1 pts [-5, +7] | -1 pts [-7, +4] | -1 pts [-7, +4] |
| Masked correctness: different category (% of set A questions) | 13% [7, 20] | 16% [10, 22] | 16% [10, 23] | 13% [8, 20] | 13% [8, 20] | 16% [10, 23] | -2 pts [-8, +3] | +0 pts [-7, +7] | -2 pts [-8, +4] | -2 pts [-7, +3] | +0 pts [-5, +5] |
| Masked correctness: not comparable (% of set A questions) | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 3% [1, 6] | 1% [0, 4] | +1 pts [+0, +2] | +0 pts [+0, +0] | +1 pts [+0, +2] | +3 pts [+1, +6] | +1 pts [+0, +4] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 1% [0, 2] | 1% [0, 2] | 0% [0, 0] | +0 pts [+0, +0] | +1 pts [+0, +2] | +1 pts [+0, +2] | +1 pts [+0, +2] | +0 pts [+0, +0] |

## Set B only (value never stated; factual consistency)

| Metric | gemini_knowledge | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 0.96 [0.94, 0.98] | 7.65 [7.43, 7.83] | 7.85 [7.70, 7.95] | 7.67 [7.45, 7.83] | 7.60 [7.39, 7.75] | 7.66 [7.50, 7.79] | -6.68 [-6.86, -6.48] | +0.21 [+0.00, +0.42] | +0.02 [-0.16, +0.21] | -0.05 [-0.23, +0.13] | +0.01 [-0.19, +0.23] |
| Questions answered from literature | 90% [86, 93] | 29% [23, 34] | 40% [34, 46] | 25% [20, 31] | 31% [26, 38] | 63% [57, 69] | +61 pts [+54, +67] | +11 pts [+4, +19] | -3 pts [-11, +4] | +3 pts [-4, +10] | +35 pts [+27, +42] |
| Questions answered with a best guess (documents gave no usable basis) | 7% [4, 10] | 67% [61, 73] | 58% [52, 64] | 72% [66, 77] | 65% [58, 70] | 35% [29, 40] | -60 pts [-67, -54] | -9 pts [-17, -1] | +5 pts [-2, +12] | -2 pts [-10, +5] | -32 pts [-40, -25] |
| Factual consistency: consistent (% of set B questions) | 98% [96, 99] | 97% [94, 99] | 98% [96, 99] | 97% [95, 99] | 96% [93, 98] | 98% [96, 99] | +1 pts [-1, +4] | +1 pts [-1, +4] | +0 pts [-2, +3] | -1 pts [-3, +1] | +1 pts [-1, +4] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 0] | 0% [0, 0] | 0% [0, 1] | 0% [0, 0] | 1% [0, 2] | 0% [0, 0] | +0 pts [+0, +0] | +0 pts [+0, +1] | +0 pts [+0, +0] | +1 pts [+0, +2] | +0 pts [+0, +0] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 2% [1, 4] | 3% [1, 6] | 2% [0, 4] | 3% [1, 5] | 4% [2, 6] | 2% [1, 4] | -1 pts [-4, +1] | -1 pts [-4, +1] | -0 pts [-3, +2] | +0 pts [-2, +3] | -1 pts [-4, +1] |

## Cost

All questions that ran.

| Method | Questions | Retrieval (search fees + search model) | medsim LLM (Stages A–C) | Total | Total per question | Median wall time |
|---|---|---|---|---|---|---|
| gemini_knowledge | 413 | $0.2949 | $0.8228 | $1.1177 | $0.00271 | 60.5 s |
| current | 413 | $0.0000 | $0.9038 | $0.9038 | $0.00219 | 100.3 s |
| improved_1to4 | 413 | $0.0000 | $0.7268 | $0.7268 | $0.00176 | 97.0 s |
| openrouter_exa_instant | 413 | $2.8916 | $0.6266 | $3.5182 | $0.00852 | 54.9 s |
| openrouter_parallel_basic | 413 | $2.0485 | $0.8105 | $2.8590 | $0.00692 | 62.8 s |
| openrouter_perplexity | 413 | $2.0913 | $0.9199 | $3.0112 | $0.00729 | 77.4 s |

## By subgroup (set A)

### Variable category

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| anthropometric | 22 | 50% | 55% | 45% | 50% | 55% | 59% | 5% | 9% | 18% | 14% | 5% | 9% |
| laboratory | 77 | 32% | 29% | 32% | 26% | 39% | 22% | 14% | 13% | 13% | 8% | 12% | 14% |
| vital_sign | 42 | 57% | 60% | 52% | 48% | 57% | 52% | 17% | 24% | 19% | 24% | 21% | 21% |

### True value (judge's category)

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| high | 74 | 38% | 31% | 30% | 28% | 39% | 31% | 14% | 19% | 14% | 15% | 14% | 14% |
| low | 34 | 42% | 47% | 45% | 39% | 58% | 28% | 3% | 6% | 10% | 3% | 6% | 12% |
| normal | 45 | 50% | 54% | 58% | 50% | 52% | 53% | 21% | 19% | 21% | 18% | 21% | 21% |
| not_applicable | 2 | 100% | 100% | 0% | – | 100% | 100% | 0% | 0% | 100% | – | 0% | 0% |
| unknown | 2 | – | – | 0% | 0% | 0% | – | – | – | 0% | 0% | 0% | – |

### Variable typical of the diagnosis

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| no | 83 | 45% | 47% | 47% | 36% | 46% | 43% | 19% | 20% | 23% | 19% | 19% | 19% |
| yes | 58 | 40% | 34% | 31% | 36% | 48% | 28% | 5% | 9% | 5% | 5% | 5% | 10% |

## Diagnostics

- **gemini_knowledge:** answer paths {'literature': 370, 'best_guess': 32, 'case_study': 5, 'query_builder_declined': 6}; source article removed for 0 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **current:** answer paths {'literature': 127, 'best_guess': 272, 'case_study': 5, 'query_builder_declined': 8, 'off_topic': 1}; source article removed for 51 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **improved_1to4:** answer paths {'literature': 172, 'best_guess': 233, 'case_study': 2, 'synthesizer_unanswerable': 1, 'query_builder_declined': 5}; source article removed for 60 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_exa_instant:** answer paths {'literature': 128, 'best_guess': 274, 'case_study': 2, 'synthesizer_unanswerable': 1, 'query_builder_declined': 8}; source article removed for 45 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_parallel_basic:** answer paths {'literature': 135, 'best_guess': 259, 'case_study': 8, 'off_topic': 2, 'query_builder_declined': 8, 'synthesizer_unanswerable': 1}; source article removed for 39 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_perplexity:** answer paths {'best_guess': 149, 'literature': 254, 'case_study': 4, 'query_builder_declined': 5, 'off_topic': 1}; source article removed for 41 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **Masked correctness:** 8 of 843 voted labels were "not comparable" (reported as their own label).
- **Judge errors (all attempts, all judges):** 119 judgment(s) failed; rerun the judge step to retry them.

## Judge panel agreement

| Metric | Answers | Unanimous | Majority | Tie broken by the main judge | Tie broken by the next judge | Fewer than all votes |
|---|---|---|---|---|---|---|
| masked correctness | 843 | 72% | 28% | 0% | 0% | 0 |
| factual consistency | 1588 | 99% | 1% | 0% | 0% | 0 |

- **masked correctness, `google/gemini-3.5-flash-lite` vs `qwen/qwen3.8-flash`:** 663/843 identical labels, Cohen's κ = 0.66.
- **masked correctness, `google/gemini-3.5-flash-lite` vs `openai/gpt-6-luna`:** 642/843 identical labels, Cohen's κ = 0.62.
- **masked correctness, `qwen/qwen3.8-flash` vs `openai/gpt-6-luna`:** 743/843 identical labels, Cohen's κ = 0.81.
- **factual consistency, `google/gemini-3.5-flash-lite` vs `qwen/qwen3.8-flash`:** 1576/1588 identical labels, Cohen's κ = 0.14.
- **factual consistency, `google/gemini-3.5-flash-lite` vs `openai/gpt-6-luna`:** 1581/1588 identical labels, Cohen's κ = -0.00.
- **factual consistency, `qwen/qwen3.8-flash` vs `openai/gpt-6-luna`:** 1581/1588 identical labels, Cohen's κ = 0.36.

## Benchmark spend

| Step | Cost (USD, OpenRouter usage.cost) |
|---|---|
| extract (case facts) | $0.0000 |
| redact + Stage A checks (accepted) | $0.0000 |
| redact + Stage A checks (rejected) | $0.0000 |
| run (all methods; search fees included) | $12.1366 |
| judge: masked correctness (google/gemini-3.5-flash-lite) | $0.9325 |
| judge: masked correctness (openai/gpt-6-luna) | $0.1580 |
| judge: masked correctness (qwen/qwen3.8-flash) | $0.3241 |
| judge: factual consistency (google/gemini-3.5-flash-lite) | $0.7013 |
| judge: factual consistency (openai/gpt-6-luna) | $0.1982 |
| judge: factual consistency (qwen/qwen3.8-flash) | $0.2884 |
| validation: controls (panel) | $0.0000 |
| validation: flipped truth (panel) | $0.0000 |
| **total** | **$14.7390** |

Cross-check: the OpenRouter key's usage counter, read right after each of the 6 benchmark commands, rose by $3.8322. The counter lags behind requests, so this undercounts; per-call usage.cost above is the accounting source.

