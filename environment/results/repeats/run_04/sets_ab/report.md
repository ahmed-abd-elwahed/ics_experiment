# Retrieval benchmark report

- Workspace: `environment/results/repeats/run_04/sets_ab`
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
| Documents returned per question | 0.97 [0.96, 0.99] | 7.73 [7.59, 7.86] | 7.86 [7.75, 7.96] | 7.69 [7.54, 7.80] | 7.48 [7.31, 7.63] | 7.61 [7.47, 7.72] | -6.76 [-6.88, -6.61] | +0.14 [+0.00, +0.29] | -0.04 [-0.18, +0.10] | -0.25 [-0.41, -0.09] | -0.12 [-0.29, +0.04] |
| Questions answered from literature | 90% [86, 93] | 31% [26, 35] | 42% [37, 47] | 31% [26, 36] | 33% [28, 37] | 62% [57, 66] | +59 pts [+53, +65] | +11 pts [+5, +17] | +0 pts [-6, +7] | +2 pts [-4, +8] | +31 pts [+25, +37] |
| Questions answered with a best guess (documents gave no usable basis) | 8% [5, 11] | 66% [61, 70] | 56% [51, 61] | 66% [62, 71] | 63% [58, 68] | 36% [32, 41] | -58 pts [-64, -52] | -9 pts [-16, -3] | +0 pts [-6, +7] | -3 pts [-9, +3] | -30 pts [-36, -23] |
| Masked correctness: exact (% of set A questions) | 45% [36, 54] | 43% [34, 52] | 43% [34, 51] | 41% [33, 51] | 46% [37, 55] | 39% [30, 48] | +2 pts [-7, +11] | -1 pts [-8, +7] | -2 pts [-11, +7] | +3 pts [-4, +11] | -4 pts [-13, +4] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 85% [78, 91] | 85% [79, 91] | 84% [77, 90] | 84% [77, 91] | 84% [77, 90] | 84% [77, 90] | +0 pts [-6, +6] | -1 pts [-6, +5] | -1 pts [-6, +4] | -1 pts [-7, +4] | -1 pts [-6, +4] |
| Masked correctness: different category (% of set A questions) | 14% [8, 21] | 14% [9, 21] | 15% [9, 22] | 14% [8, 21] | 13% [7, 19] | 15% [9, 21] | +0 pts [-6, +6] | +1 pts [-5, +6] | +0 pts [-5, +5] | -1 pts [-6, +4] | +1 pts [-4, +6] |
| Masked correctness: not comparable (% of set A questions) | 1% [0, 2] | 1% [0, 2] | 0% [0, 0] | 1% [0, 2] | 3% [1, 6] | 1% [0, 4] | +0 pts [-2, +2] | -1 pts [-2, +0] | +0 pts [-2, +2] | +2 pts [-1, +5] | +1 pts [-2, +3] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 1% [0, 2] | 1% [0, 2] | 0% [0, 0] | +0 pts [+0, +0] | +1 pts [+0, +2] | +1 pts [+0, +2] | +1 pts [+0, +2] | +0 pts [+0, +0] |
| Factual consistency: consistent (% of set B questions) | 98% [96, 99] | 97% [94, 99] | 98% [96, 99] | 97% [95, 99] | 96% [93, 98] | 97% [95, 99] | +1 pts [-1, +4] | +1 pts [-1, +4] | +0 pts [-2, +2] | -1 pts [-3, +1] | +0 pts [-2, +3] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 0] | 0% [0, 0] | 0% [0, 1] | 0% [0, 0] | 1% [0, 2] | 1% [0, 2] | +0 pts [+0, +0] | +0 pts [+0, +1] | +0 pts [+0, +0] | +1 pts [+0, +2] | +1 pts [+0, +2] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 2% [1, 4] | 3% [1, 6] | 2% [0, 4] | 3% [1, 5] | 4% [2, 6] | 2% [1, 4] | -1 pts [-4, +1] | -1 pts [-4, +1] | -0 pts [-2, +2] | +0 pts [-2, +2] | -1 pts [-3, +1] |
| Retrieval cost per question (search fees, search/rerank LLM; USD) | $0.00071 | $0.00000 | $0.00000 | $0.00700 | $0.00496 | $0.00506 | +0.00071 [+0.00070, +0.00073] | +0.00000 [+0.00000, +0.00000] | +0.00700 [+0.00688, +0.00710] | +0.00496 [+0.00485, +0.00506] | +0.00506 [+0.00498, +0.00513] |
| medsim LLM cost per question (Stages A–C, USD) | $0.00199 | $0.00219 | $0.00176 | $0.00152 | $0.00196 | $0.00223 | -0.00020 [-0.00039, -0.00001] | -0.00043 [-0.00065, -0.00020] | -0.00067 [-0.00088, -0.00046] | -0.00023 [-0.00045, +0.00001] | +0.00004 [-0.00021, +0.00029] |
| Total cost per question (USD) | $0.00271 | $0.00219 | $0.00176 | $0.00852 | $0.00692 | $0.00729 | +0.00052 [+0.00033, +0.00070] | -0.00043 [-0.00065, -0.00020] | +0.00633 [+0.00609, +0.00656] | +0.00473 [+0.00449, +0.00499] | +0.00510 [+0.00485, +0.00537] |
| Wall time per question (s) | 69.7 [66.1, 73.5] | 126.8 [118.8, 135.3] | 108.8 [103.2, 115.5] | 65.2 [61.6, 69.4] | 87.7 [81.7, 94.0] | 93.5 [87.5, 99.6] | -57.10 [-65.19, -49.66] | -17.95 [-26.77, -9.09] | -61.63 [-70.79, -53.48] | -39.06 [-48.52, -29.57] | -33.26 [-43.35, -23.73] |
| Time outside medsim's LLM calls per question (≈ retrieval; s) | 2.36 [2.24, 2.52] | 40.69 [37.05, 44.47] | 38.27 [36.67, 39.78] | 5.25 [5.01, 5.50] | 5.96 [5.68, 6.24] | 6.71 [6.30, 7.27] | -38.33 [-42.13, -34.74] | -2.42 [-6.08, +0.95] | -35.44 [-39.23, -31.82] | -34.73 [-38.53, -31.22] | -33.98 [-37.82, -30.38] |

## Set A only (hidden value; masked correctness)

| Metric | gemini_knowledge | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 0.99 [0.98, 1.00] | 7.89 [7.71, 8.00] | 7.89 [7.72, 8.00] | 7.72 [7.55, 7.87] | 7.26 [6.95, 7.55] | 7.50 [7.26, 7.72] | -6.89 [-7.01, -6.71] | +0.00 [-0.17, +0.17] | -0.16 [-0.34, +0.01] | -0.62 [-0.94, -0.33] | -0.38 [-0.65, -0.14] |
| Questions answered from literature | 89% [84, 95] | 35% [27, 43] | 45% [36, 53] | 42% [33, 50] | 35% [27, 44] | 58% [50, 67] | +55 pts [+44, +64] | +10 pts [-1, +20] | +7 pts [-2, +16] | +1 pts [-10, +11] | +23 pts [+13, +34] |
| Questions answered with a best guess (documents gave no usable basis) | 10% [4, 16] | 64% [56, 72] | 53% [45, 62] | 56% [48, 64] | 59% [49, 68] | 39% [31, 47] | -54 pts [-63, -44] | -11 pts [-21, +0] | -8 pts [-17, +2] | -5 pts [-16, +5] | -25 pts [-36, -14] |
| Masked correctness: exact (% of set A questions) | 45% [36, 54] | 43% [34, 52] | 43% [34, 51] | 41% [33, 51] | 46% [37, 55] | 39% [30, 48] | +2 pts [-7, +11] | -1 pts [-8, +7] | -2 pts [-11, +7] | +3 pts [-4, +11] | -4 pts [-13, +4] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 85% [78, 91] | 85% [79, 91] | 84% [77, 90] | 84% [77, 91] | 84% [77, 90] | 84% [77, 90] | +0 pts [-6, +6] | -1 pts [-6, +5] | -1 pts [-6, +4] | -1 pts [-7, +4] | -1 pts [-6, +4] |
| Masked correctness: different category (% of set A questions) | 14% [8, 21] | 14% [9, 21] | 15% [9, 22] | 14% [8, 21] | 13% [7, 19] | 15% [9, 21] | +0 pts [-6, +6] | +1 pts [-5, +6] | +0 pts [-5, +5] | -1 pts [-6, +4] | +1 pts [-4, +6] |
| Masked correctness: not comparable (% of set A questions) | 1% [0, 2] | 1% [0, 2] | 0% [0, 0] | 1% [0, 2] | 3% [1, 6] | 1% [0, 4] | +0 pts [-2, +2] | -1 pts [-2, +0] | +0 pts [-2, +2] | +2 pts [-1, +5] | +1 pts [-2, +3] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 1% [0, 2] | 1% [0, 2] | 0% [0, 0] | +0 pts [+0, +0] | +1 pts [+0, +2] | +1 pts [+0, +2] | +1 pts [+0, +2] | +0 pts [+0, +0] |

## Set B only (value never stated; factual consistency)

| Metric | gemini_knowledge | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 0.96 [0.94, 0.98] | 7.65 [7.43, 7.83] | 7.85 [7.70, 7.97] | 7.67 [7.46, 7.83] | 7.60 [7.40, 7.76] | 7.66 [7.50, 7.79] | -6.68 [-6.86, -6.48] | +0.21 [+0.00, +0.42] | +0.02 [-0.17, +0.21] | -0.05 [-0.23, +0.14] | +0.01 [-0.19, +0.23] |
| Questions answered from literature | 90% [86, 93] | 29% [23, 34] | 40% [34, 46] | 25% [20, 31] | 31% [26, 37] | 63% [58, 69] | +61 pts [+54, +67] | +11 pts [+4, +19] | -3 pts [-11, +4] | +3 pts [-4, +10] | +35 pts [+27, +42] |
| Questions answered with a best guess (documents gave no usable basis) | 7% [4, 10] | 67% [61, 73] | 58% [52, 64] | 72% [66, 77] | 65% [58, 70] | 35% [29, 40] | -60 pts [-67, -54] | -9 pts [-17, -1] | +5 pts [-3, +12] | -2 pts [-10, +5] | -32 pts [-40, -25] |
| Factual consistency: consistent (% of set B questions) | 98% [96, 99] | 97% [94, 99] | 98% [96, 99] | 97% [95, 99] | 96% [93, 98] | 97% [95, 99] | +1 pts [-1, +4] | +1 pts [-1, +4] | +0 pts [-2, +2] | -1 pts [-3, +1] | +0 pts [-2, +3] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 0] | 0% [0, 0] | 0% [0, 1] | 0% [0, 0] | 1% [0, 2] | 1% [0, 2] | +0 pts [+0, +0] | +0 pts [+0, +1] | +0 pts [+0, +0] | +1 pts [+0, +2] | +1 pts [+0, +2] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 2% [1, 4] | 3% [1, 6] | 2% [0, 4] | 3% [1, 5] | 4% [2, 6] | 2% [1, 4] | -1 pts [-4, +1] | -1 pts [-4, +1] | -0 pts [-2, +2] | +0 pts [-2, +2] | -1 pts [-3, +1] |

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
| anthropometric | 22 | 55% | 59% | 45% | 50% | 55% | 59% | 5% | 9% | 14% | 14% | 5% | 9% |
| laboratory | 77 | 34% | 31% | 34% | 30% | 38% | 22% | 17% | 9% | 13% | 9% | 9% | 14% |
| vital_sign | 42 | 62% | 57% | 57% | 57% | 57% | 60% | 14% | 26% | 19% | 24% | 24% | 19% |

### True value (judge's category)

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| high | 73 | 40% | 31% | 34% | 30% | 34% | 34% | 16% | 17% | 14% | 15% | 12% | 14% |
| low | 34 | 44% | 48% | 45% | 48% | 61% | 33% | 6% | 3% | 9% | 6% | 6% | 9% |
| normal | 38 | 53% | 60% | 58% | 56% | 53% | 51% | 21% | 20% | 19% | 21% | 22% | 23% |
| not_applicable | 4 | 100% | 100% | 0% | 100% | 100% | 100% | 0% | 0% | 100% | 0% | 0% | 0% |
| unknown | 2 | – | – | 0% | 0% | 0% | – | – | – | 0% | 0% | 0% | – |

### Variable typical of the diagnosis

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| no | 83 | 48% | 48% | 49% | 40% | 46% | 47% | 20% | 19% | 20% | 20% | 20% | 18% |
| yes | 58 | 41% | 36% | 33% | 43% | 47% | 28% | 5% | 7% | 7% | 5% | 2% | 10% |

## Diagnostics

- **gemini_knowledge:** answer paths {'literature': 370, 'best_guess': 32, 'case_study': 5, 'query_builder_declined': 6}; source article removed for 0 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **current:** answer paths {'literature': 127, 'best_guess': 272, 'case_study': 5, 'query_builder_declined': 8, 'off_topic': 1}; source article removed for 51 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **improved_1to4:** answer paths {'literature': 172, 'best_guess': 233, 'case_study': 2, 'synthesizer_unanswerable': 1, 'query_builder_declined': 5}; source article removed for 60 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_exa_instant:** answer paths {'literature': 128, 'best_guess': 274, 'case_study': 2, 'synthesizer_unanswerable': 1, 'query_builder_declined': 8}; source article removed for 45 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_parallel_basic:** answer paths {'literature': 135, 'best_guess': 259, 'case_study': 8, 'off_topic': 2, 'query_builder_declined': 8, 'synthesizer_unanswerable': 1}; source article removed for 39 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_perplexity:** answer paths {'best_guess': 149, 'literature': 254, 'case_study': 4, 'query_builder_declined': 5, 'off_topic': 1}; source article removed for 41 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **Masked correctness:** 9 of 843 voted labels were "not comparable" (reported as their own label).
- **Judge errors (all attempts, all judges):** 119 judgment(s) failed; rerun the judge step to retry them.

## Judge panel agreement

| Metric | Answers | Unanimous | Majority | Tie broken by the main judge | Tie broken by the next judge | Fewer than all votes |
|---|---|---|---|---|---|---|
| masked correctness | 843 | 82% | 18% | 0% | 0% | 0 |
| factual consistency | 1588 | 99% | 1% | 0% | 0% | 0 |

- **masked correctness, `anthropic/claude-haiku-5.5` vs `z-ai/glm-5.3-flash`:** 740/843 identical labels, Cohen's κ = 0.81.
- **masked correctness, `anthropic/claude-haiku-5.5` vs `openai/gpt-6-luna`:** 728/843 identical labels, Cohen's κ = 0.78.
- **masked correctness, `z-ai/glm-5.3-flash` vs `openai/gpt-6-luna`:** 757/843 identical labels, Cohen's κ = 0.84.
- **factual consistency, `anthropic/claude-haiku-5.5` vs `z-ai/glm-5.3-flash`:** 1572/1588 identical labels, Cohen's κ = 0.33.
- **factual consistency, `anthropic/claude-haiku-5.5` vs `openai/gpt-6-luna`:** 1573/1588 identical labels, Cohen's κ = 0.12.
- **factual consistency, `z-ai/glm-5.3-flash` vs `openai/gpt-6-luna`:** 1581/1588 identical labels, Cohen's κ = 0.36.

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
| judge: masked correctness (typesafe/jev-1.13) | $0.0353 |
| judge: masked correctness (z-ai/glm-5.3-flash) | $0.1334 |
| judge: masked correctness (anthropic/claude-haiku-5.5) | $0.2333 |
| judge: factual consistency (google/gemini-3.5-flash-lite) | $0.7013 |
| judge: factual consistency (openai/gpt-6-luna) | $0.1982 |
| judge: factual consistency (qwen/qwen3.8-flash) | $0.2884 |
| judge: factual consistency (typesafe/jev-1.13) | $0.0557 |
| judge: factual consistency (anthropic/claude-haiku-5.5) | $0.3182 |
| judge: factual consistency (z-ai/glm-5.3-flash) | $0.1594 |
| validation: controls (panel) | $0.0000 |
| validation: flipped truth (panel) | $0.0000 |
| **total** | **$15.6744** |

Cross-check: the OpenRouter key's usage counter, read right after each of the 8 benchmark commands, rose by $7.9990. The counter lags behind requests, so this undercounts; per-call usage.cost above is the accounting source.

