# Retrieval benchmark report

- Workspace: `environment/results/repeats/run_05/sets_ab`
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
| Documents returned per question | 0.97 [0.95, 0.98] | 7.75 [7.60, 7.88] | 7.73 [7.57, 7.87] | 7.70 [7.54, 7.82] | 6.88 [6.61, 7.12] | 7.55 [7.40, 7.68] | -6.78 [-6.91, -6.64] | -0.02 [-0.19, +0.15] | -0.05 [-0.21, +0.10] | -0.86 [-1.13, -0.63] | -0.20 [-0.36, -0.02] |
| Questions answered from literature | 91% [88, 93] | 31% [26, 36] | 46% [40, 51] | 30% [25, 34] | 28% [24, 32] | 61% [56, 66] | +60 pts [+54, +66] | +15 pts [+9, +21] | -1 pts [-8, +5] | -3 pts [-9, +3] | +30 pts [+24, +36] |
| Questions answered with a best guess (documents gave no usable basis) | 6% [4, 8] | 66% [60, 71] | 51% [46, 56] | 68% [63, 73] | 69% [65, 73] | 35% [30, 40] | -60 pts [-66, -54] | -15 pts [-21, -9] | +2 pts [-4, +9] | +3 pts [-3, +10] | -31 pts [-37, -24] |
| Masked correctness: exact (% of set A questions) | 48% [39, 57] | 46% [37, 55] | 41% [33, 50] | 44% [35, 53] | 43% [34, 51] | 48% [39, 56] | +2 pts [-5, +9] | -5 pts [-12, +3] | -2 pts [-8, +4] | -4 pts [-12, +5] | +1 pts [-7, +10] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 85% [79, 91] | 86% [79, 91] | 84% [78, 90] | 87% [81, 93] | 84% [77, 90] | 84% [77, 90] | -1 pts [-7, +6] | -1 pts [-7, +5] | +1 pts [-5, +8] | -2 pts [-8, +4] | -1 pts [-9, +6] |
| Masked correctness: different category (% of set A questions) | 11% [6, 17] | 12% [7, 18] | 14% [8, 21] | 11% [6, 17] | 14% [8, 21] | 13% [8, 20] | -1 pts [-7, +6] | +2 pts [-4, +8] | -1 pts [-7, +6] | +2 pts [-4, +8] | +1 pts [-6, +9] |
| Masked correctness: not comparable (% of set A questions) | 3% [1, 6] | 2% [0, 5] | 1% [0, 4] | 1% [0, 4] | 1% [0, 4] | 1% [0, 2] | +1 pts [-3, +4] | -1 pts [-4, +2] | -1 pts [-4, +2] | -1 pts [-4, +2] | -1 pts [-5, +1] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 1% [0, 4] | +1 pts [+0, +2] | +0 pts [+0, +0] | +0 pts [+0, +0] | +1 pts [+0, +2] | +1 pts [+0, +4] |
| Factual consistency: consistent (% of set B questions) | 97% [94, 99] | 95% [92, 98] | 96% [94, 98] | 97% [95, 99] | 96% [93, 98] | 96% [94, 98] | +1 pts [-1, +4] | +1 pts [-1, +4] | +2 pts [-1, +5] | +0 pts [-2, +3] | +1 pts [-2, +4] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 1] | 0% [0, 1] | 0% [0, 1] | 0% [0, 1] | 1% [0, 3] | 0% [0, 0] | +0 pts [-1, +1] | +0 pts [-1, +1] | +0 pts [-1, +1] | +1 pts [-1, +2] | -0 pts [-1, +0] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 3% [1, 5] | 4% [2, 7] | 3% [1, 5] | 3% [1, 5] | 3% [1, 6] | 4% [2, 6] | -1 pts [-4, +1] | -1 pts [-4, +1] | -2 pts [-4, +0] | -1 pts [-4, +1] | -1 pts [-3, +2] |
| Retrieval cost per question (search fees, search/rerank LLM; USD) | $0.00071 | $0.00000 | $0.00000 | $0.00700 | $0.00503 | $0.00501 | +0.00071 [+0.00069, +0.00072] | +0.00000 [+0.00000, +0.00000] | +0.00700 [+0.00686, +0.00710] | +0.00503 [+0.00493, +0.00511] | +0.00501 [+0.00492, +0.00509] |
| medsim LLM cost per question (Stages A–C, USD) | $0.00160 | $0.00210 | $0.00226 | $0.00194 | $0.00204 | $0.00245 | -0.00049 [-0.00066, -0.00032] | +0.00017 [-0.00003, +0.00038] | -0.00016 [-0.00032, +0.00001] | -0.00006 [-0.00027, +0.00015] | +0.00036 [+0.00012, +0.00059] |
| Total cost per question (USD) | $0.00231 | $0.00210 | $0.00226 | $0.00894 | $0.00707 | $0.00747 | +0.00022 [+0.00004, +0.00039] | +0.00017 [-0.00003, +0.00038] | +0.00684 [+0.00663, +0.00705] | +0.00497 [+0.00474, +0.00521] | +0.00537 [+0.00511, +0.00564] |
| Wall time per question (s) | 67.1 [62.8, 71.7] | 120.6 [114.6, 126.9] | 104.8 [99.2, 111.0] | 70.5 [65.9, 75.8] | 77.6 [72.3, 82.9] | 92.5 [85.8, 99.1] | -53.49 [-60.44, -46.42] | -15.74 [-23.51, -7.99] | -50.01 [-56.40, -43.31] | -42.97 [-51.13, -35.08] | -28.08 [-36.85, -19.62] |
| Time outside medsim's LLM calls per question (≈ retrieval; s) | 3.16 [2.99, 3.40] | 50.28 [46.04, 54.60] | 26.26 [24.98, 27.53] | 5.40 [5.13, 5.66] | 6.83 [6.54, 7.15] | 6.55 [6.24, 6.88] | -47.11 [-51.36, -42.95] | -24.02 [-28.30, -19.86] | -44.88 [-49.23, -40.74] | -43.45 [-47.75, -39.24] | -43.72 [-48.04, -39.56] |

## Set A only (hidden value; masked correctness)

| Metric | gemini_knowledge | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 0.96 [0.92, 0.99] | 7.89 [7.71, 8.00] | 7.89 [7.71, 8.00] | 7.78 [7.62, 7.89] | 7.28 [6.95, 7.56] | 7.50 [7.25, 7.72] | -6.93 [-7.06, -6.74] | +0.00 [-0.22, +0.24] | -0.11 [-0.31, +0.11] | -0.61 [-0.98, -0.28] | -0.38 [-0.69, -0.10] |
| Questions answered from literature | 90% [85, 94] | 35% [27, 43] | 51% [43, 59] | 37% [28, 47] | 34% [26, 43] | 63% [54, 72] | +55 pts [+46, +64] | +16 pts [+7, +26] | +2 pts [-8, +13] | -1 pts [-10, +9] | +28 pts [+17, +40] |
| Questions answered with a best guess (documents gave no usable basis) | 6% [2, 10] | 64% [55, 72] | 48% [39, 55] | 62% [53, 71] | 64% [55, 72] | 33% [24, 42] | -58 pts [-67, -49] | -16 pts [-26, -7] | -1 pts [-13, +9] | +0 pts [-11, +10] | -30 pts [-42, -19] |
| Masked correctness: exact (% of set A questions) | 48% [39, 57] | 46% [37, 55] | 41% [33, 50] | 44% [35, 53] | 43% [34, 51] | 48% [39, 56] | +2 pts [-5, +9] | -5 pts [-12, +3] | -2 pts [-8, +4] | -4 pts [-12, +5] | +1 pts [-7, +10] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 85% [79, 91] | 86% [79, 91] | 84% [78, 90] | 87% [81, 93] | 84% [77, 90] | 84% [77, 90] | -1 pts [-7, +6] | -1 pts [-7, +5] | +1 pts [-5, +8] | -2 pts [-8, +4] | -1 pts [-9, +6] |
| Masked correctness: different category (% of set A questions) | 11% [6, 17] | 12% [7, 18] | 14% [8, 21] | 11% [6, 17] | 14% [8, 21] | 13% [8, 20] | -1 pts [-7, +6] | +2 pts [-4, +8] | -1 pts [-7, +6] | +2 pts [-4, +8] | +1 pts [-6, +9] |
| Masked correctness: not comparable (% of set A questions) | 3% [1, 6] | 2% [0, 5] | 1% [0, 4] | 1% [0, 4] | 1% [0, 4] | 1% [0, 2] | +1 pts [-3, +4] | -1 pts [-4, +2] | -1 pts [-4, +2] | -1 pts [-4, +2] | -1 pts [-5, +1] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 1% [0, 4] | +1 pts [+0, +2] | +0 pts [+0, +0] | +0 pts [+0, +0] | +1 pts [+0, +2] | +1 pts [+0, +4] |

## Set B only (value never stated; factual consistency)

| Metric | gemini_knowledge | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 0.97 [0.95, 0.99] | 7.68 [7.45, 7.85] | 7.65 [7.44, 7.83] | 7.65 [7.44, 7.83] | 6.68 [6.35, 7.00] | 7.57 [7.37, 7.73] | -6.71 [-6.87, -6.49] | -0.03 [-0.24, +0.20] | -0.02 [-0.22, +0.17] | -1.00 [-1.31, -0.69] | -0.11 [-0.32, +0.11] |
| Questions answered from literature | 91% [88, 94] | 29% [24, 35] | 43% [37, 49] | 26% [20, 31] | 25% [20, 30] | 60% [54, 66] | +62 pts [+56, +69] | +14 pts [+7, +21] | -3 pts [-10, +3] | -4 pts [-12, +3] | +31 pts [+24, +38] |
| Questions answered with a best guess (documents gave no usable basis) | 6% [3, 8] | 67% [61, 72] | 53% [46, 59] | 71% [65, 77] | 72% [66, 77] | 36% [30, 42] | -61 pts [-67, -54] | -14 pts [-21, -7] | +4 pts [-3, +11] | +5 pts [-3, +13] | -31 pts [-38, -23] |
| Factual consistency: consistent (% of set B questions) | 97% [94, 99] | 95% [92, 98] | 96% [94, 98] | 97% [95, 99] | 96% [93, 98] | 96% [94, 98] | +1 pts [-1, +4] | +1 pts [-1, +4] | +2 pts [-1, +5] | +0 pts [-2, +3] | +1 pts [-2, +4] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 1] | 0% [0, 1] | 0% [0, 1] | 0% [0, 1] | 1% [0, 3] | 0% [0, 0] | +0 pts [-1, +1] | +0 pts [-1, +1] | +0 pts [-1, +1] | +1 pts [-1, +2] | -0 pts [-1, +0] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 3% [1, 5] | 4% [2, 7] | 3% [1, 5] | 3% [1, 5] | 3% [1, 6] | 4% [2, 6] | -1 pts [-4, +1] | -1 pts [-4, +1] | -2 pts [-4, +0] | -1 pts [-4, +1] | -1 pts [-3, +2] |

## Cost

All questions that ran.

| Method | Questions | Retrieval (search fees + search model) | medsim LLM (Stages A–C) | Total | Total per question | Median wall time |
|---|---|---|---|---|---|---|
| gemini_knowledge | 413 | $0.2927 | $0.6616 | $0.9543 | $0.00231 | 56.7 s |
| current | 413 | $0.0000 | $0.8654 | $0.8654 | $0.00210 | 110.8 s |
| improved_1to4 | 413 | $0.0000 | $0.9348 | $0.9348 | $0.00226 | 90.2 s |
| openrouter_exa_instant | 413 | $2.8913 | $0.8010 | $3.6923 | $0.00894 | 57.6 s |
| openrouter_parallel_basic | 413 | $2.0768 | $0.8420 | $2.9188 | $0.00707 | 62.6 s |
| openrouter_perplexity | 413 | $2.0707 | $1.0128 | $3.0835 | $0.00747 | 77.9 s |

## By subgroup (set A)

### Variable category

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| anthropometric | 22 | 55% | 55% | 64% | 55% | 59% | 50% | 0% | 5% | 0% | 5% | 5% | 14% |
| laboratory | 77 | 36% | 34% | 29% | 30% | 26% | 35% | 16% | 10% | 13% | 12% | 16% | 13% |
| vital_sign | 42 | 67% | 64% | 52% | 64% | 64% | 69% | 10% | 19% | 24% | 14% | 17% | 14% |

### True value (judge's category)

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| high | 72 | 41% | 36% | 30% | 29% | 28% | 43% | 13% | 13% | 14% | 13% | 16% | 13% |
| low | 35 | 48% | 55% | 48% | 49% | 44% | 47% | 6% | 6% | 6% | 11% | 9% | 6% |
| normal | 40 | 61% | 55% | 51% | 69% | 63% | 54% | 14% | 16% | 23% | 9% | 17% | 23% |
| not_applicable | 6 | 100% | 100% | 75% | 100% | 100% | 100% | 0% | 0% | 0% | 0% | 0% | 0% |
| unknown | 3 | 0% | – | – | – | 0% | 0% | 0% | – | – | – | 0% | 0% |

### Variable typical of the diagnosis

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| no | 83 | 52% | 46% | 45% | 47% | 49% | 51% | 16% | 18% | 20% | 14% | 20% | 17% |
| yes | 58 | 43% | 47% | 36% | 40% | 33% | 43% | 5% | 3% | 5% | 7% | 5% | 9% |

## Diagnostics

- **gemini_knowledge:** answer paths {'literature': 375, 'best_guess': 23, 'off_topic': 1, 'case_study': 6, 'query_builder_declined': 7, 'synthesizer_unanswerable': 1}; source article removed for 0 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **current:** answer paths {'best_guess': 271, 'literature': 128, 'case_study': 2, 'query_builder_declined': 10, 'off_topic': 1, 'synthesizer_unanswerable': 1}; source article removed for 51 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **improved_1to4:** answer paths {'literature': 189, 'best_guess': 210, 'case_study': 5, 'query_builder_declined': 9}; source article removed for 60 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_exa_instant:** answer paths {'literature': 122, 'best_guess': 281, 'case_study': 3, 'query_builder_declined': 7}; source article removed for 40 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_parallel_basic:** answer paths {'literature': 115, 'best_guess': 285, 'case_study': 3, 'synthesizer_unanswerable': 1, 'query_builder_declined': 9}; source article removed for 31 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_perplexity:** answer paths {'best_guess': 145, 'literature': 253, 'query_builder_declined': 8, 'case_study': 4, 'synthesizer_unanswerable': 1, 'off_topic': 2}; source article removed for 40 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **Masked correctness:** 14 of 842 voted labels were "not comparable" (reported as their own label).
- **Judge errors (all attempts, all judges):** 93 judgment(s) failed; rerun the judge step to retry them.

## Judge panel agreement

| Metric | Answers | Unanimous | Majority | Tie broken by the main judge | Tie broken by the next judge | Fewer than all votes |
|---|---|---|---|---|---|---|
| masked correctness | 842 | 83% | 17% | 0% | 0% | 0 |
| factual consistency | 1577 | 99% | 1% | 0% | 0% | 0 |

- **masked correctness, `anthropic/claude-haiku-5.5` vs `z-ai/glm-5.3-flash`:** 753/842 identical labels, Cohen's κ = 0.83.
- **masked correctness, `anthropic/claude-haiku-5.5` vs `openai/gpt-6-luna`:** 731/842 identical labels, Cohen's κ = 0.79.
- **masked correctness, `z-ai/glm-5.3-flash` vs `openai/gpt-6-luna`:** 761/842 identical labels, Cohen's κ = 0.85.
- **factual consistency, `anthropic/claude-haiku-5.5` vs `z-ai/glm-5.3-flash`:** 1566/1577 identical labels, Cohen's κ = 0.56.
- **factual consistency, `anthropic/claude-haiku-5.5` vs `openai/gpt-6-luna`:** 1566/1577 identical labels, Cohen's κ = 0.35.
- **factual consistency, `z-ai/glm-5.3-flash` vs `openai/gpt-6-luna`:** 1567/1577 identical labels, Cohen's κ = 0.37.

## Benchmark spend

| Step | Cost (USD, OpenRouter usage.cost) |
|---|---|
| extract (case facts) | $0.0000 |
| redact + Stage A checks (accepted) | $0.0000 |
| redact + Stage A checks (rejected) | $0.0000 |
| run (all methods; search fees included) | $12.4490 |
| judge: masked correctness (google/gemini-3.5-flash-lite) | $0.7384 |
| judge: masked correctness (openai/gpt-6-luna) | $0.1601 |
| judge: masked correctness (qwen/qwen3.8-flash) | $0.2970 |
| judge: masked correctness (typesafe/jev-1.13) | $0.0353 |
| judge: masked correctness (z-ai/glm-5.3-flash) | $0.1321 |
| judge: masked correctness (anthropic/claude-haiku-5.5) | $0.2300 |
| judge: factual consistency (google/gemini-3.5-flash-lite) | $0.6965 |
| judge: factual consistency (openai/gpt-6-luna) | $0.1983 |
| judge: factual consistency (qwen/qwen3.8-flash) | $0.2859 |
| judge: factual consistency (typesafe/jev-1.13) | $0.0553 |
| judge: factual consistency (anthropic/claude-haiku-5.5) | $0.3150 |
| judge: factual consistency (z-ai/glm-5.3-flash) | $0.1712 |
| validation: controls (panel) | $0.0000 |
| validation: flipped truth (panel) | $0.0000 |
| **total** | **$15.7642** |

Cross-check: the OpenRouter key's usage counter, read right after each of the 7 benchmark commands, rose by $5.8511. The counter lags behind requests, so this undercounts; per-call usage.cost above is the accounting source.

