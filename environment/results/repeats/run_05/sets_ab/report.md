# Retrieval benchmark report

- Workspace: `environment/results/repeats/run_05/sets_ab`
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
| Documents returned per question | 0.97 [0.95, 0.98] | 7.75 [7.61, 7.88] | 7.73 [7.57, 7.87] | 7.70 [7.54, 7.82] | 6.88 [6.61, 7.12] | 7.55 [7.40, 7.67] | -6.78 [-6.91, -6.65] | -0.02 [-0.19, +0.15] | -0.05 [-0.21, +0.10] | -0.86 [-1.13, -0.62] | -0.20 [-0.36, -0.03] |
| Questions answered from literature | 91% [88, 93] | 31% [26, 36] | 46% [41, 51] | 30% [25, 34] | 28% [23, 32] | 61% [56, 66] | +60 pts [+54, +66] | +15 pts [+9, +21] | -1 pts [-8, +5] | -3 pts [-10, +2] | +30 pts [+25, +36] |
| Questions answered with a best guess (documents gave no usable basis) | 6% [4, 8] | 66% [60, 71] | 51% [46, 56] | 68% [63, 73] | 69% [65, 73] | 35% [30, 40] | -60 pts [-66, -54] | -15 pts [-20, -9] | +2 pts [-4, +9] | +3 pts [-3, +10] | -31 pts [-37, -25] |
| Masked correctness: exact (% of set A questions) | 43% [34, 51] | 41% [33, 50] | 39% [31, 48] | 40% [32, 49] | 39% [30, 48] | 41% [32, 50] | +1 pts [-7, +9] | -2 pts [-9, +5] | -1 pts [-8, +7] | -2 pts [-10, +5] | +0 pts [-8, +7] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 82% [74, 87] | 84% [77, 90] | 84% [77, 90] | 89% [83, 94] | 83% [76, 89] | 82% [74, 88] | -3 pts [-10, +4] | -1 pts [-7, +5] | +4 pts [-2, +12] | -1 pts [-9, +5] | -3 pts [-10, +4] |
| Masked correctness: different category (% of set A questions) | 14% [8, 21] | 13% [8, 20] | 15% [9, 21] | 10% [5, 15] | 15% [9, 22] | 16% [10, 24] | +1 pts [-6, +8] | +1 pts [-4, +8] | -4 pts [-10, +3] | +1 pts [-5, +8] | +3 pts [-5, +10] |
| Masked correctness: not comparable (% of set A questions) | 4% [1, 7] | 2% [0, 5] | 1% [0, 4] | 1% [0, 4] | 1% [0, 4] | 1% [0, 2] | +1 pts [-3, +5] | -1 pts [-4, +3] | -1 pts [-4, +2] | -1 pts [-4, +3] | -1 pts [-5, +1] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 1% [0, 4] | +1 pts [+0, +2] | +0 pts [+0, +0] | +0 pts [+0, +0] | +1 pts [+0, +2] | +1 pts [+0, +4] |
| Factual consistency: consistent (% of set B questions) | 97% [94, 99] | 96% [92, 98] | 96% [93, 98] | 97% [95, 99] | 96% [93, 99] | 96% [94, 98] | +1 pts [-1, +4] | +0 pts [-3, +3] | +1 pts [-1, +4] | +1 pts [-2, +4] | +1 pts [-2, +4] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 1] | 0% [0, 0] | 1% [0, 2] | 0% [0, 1] | 0% [0, 1] | 0% [0, 0] | +0 pts [+0, +1] | +1 pts [+0, +2] | +0 pts [+0, +1] | +0 pts [+0, +1] | +0 pts [+0, +0] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 3% [1, 5] | 4% [2, 7] | 3% [1, 6] | 3% [1, 5] | 3% [1, 6] | 4% [2, 6] | -1 pts [-4, +1] | -1 pts [-4, +1] | -2 pts [-5, +0] | -1 pts [-4, +1] | -1 pts [-4, +2] |
| Retrieval cost per question (search fees, search/rerank LLM; USD) | $0.00071 | $0.00000 | $0.00000 | $0.00700 | $0.00503 | $0.00501 | +0.00071 [+0.00069, +0.00072] | +0.00000 [+0.00000, +0.00000] | +0.00700 [+0.00687, +0.00710] | +0.00503 [+0.00493, +0.00511] | +0.00501 [+0.00492, +0.00509] |
| medsim LLM cost per question (Stages A–C, USD) | $0.00160 | $0.00210 | $0.00226 | $0.00194 | $0.00204 | $0.00245 | -0.00049 [-0.00066, -0.00032] | +0.00017 [-0.00003, +0.00037] | -0.00016 [-0.00032, +0.00001] | -0.00006 [-0.00028, +0.00014] | +0.00036 [+0.00012, +0.00059] |
| Total cost per question (USD) | $0.00231 | $0.00210 | $0.00226 | $0.00894 | $0.00707 | $0.00747 | +0.00022 [+0.00004, +0.00038] | +0.00017 [-0.00003, +0.00037] | +0.00684 [+0.00664, +0.00705] | +0.00497 [+0.00473, +0.00520] | +0.00537 [+0.00511, +0.00564] |
| Wall time per question (s) | 67.1 [62.9, 71.7] | 120.6 [114.7, 127.1] | 104.8 [99.1, 111.4] | 70.5 [66.2, 75.6] | 77.6 [72.2, 83.1] | 92.5 [85.9, 99.2] | -53.49 [-60.61, -46.59] | -15.74 [-23.67, -8.38] | -50.01 [-56.40, -43.86] | -42.97 [-51.70, -35.54] | -28.08 [-37.15, -19.73] |
| Time outside medsim's LLM calls per question (≈ retrieval; s) | 3.16 [2.99, 3.39] | 50.28 [46.06, 54.64] | 26.26 [25.02, 27.54] | 5.40 [5.13, 5.66] | 6.83 [6.53, 7.16] | 6.55 [6.23, 6.89] | -47.11 [-51.40, -42.98] | -24.02 [-28.31, -19.96] | -44.88 [-49.27, -40.79] | -43.45 [-47.77, -39.40] | -43.72 [-48.08, -39.65] |

## Set A only (hidden value; masked correctness)

| Metric | gemini_knowledge | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 0.96 [0.92, 0.99] | 7.89 [7.70, 8.00] | 7.89 [7.71, 8.00] | 7.78 [7.62, 7.89] | 7.28 [6.95, 7.56] | 7.50 [7.23, 7.72] | -6.93 [-7.06, -6.74] | +0.00 [-0.23, +0.24] | -0.11 [-0.32, +0.12] | -0.61 [-0.98, -0.27] | -0.38 [-0.71, -0.08] |
| Questions answered from literature | 90% [85, 94] | 35% [27, 43] | 51% [43, 59] | 37% [28, 46] | 34% [26, 43] | 63% [54, 72] | +55 pts [+47, +64] | +16 pts [+7, +25] | +2 pts [-8, +13] | -1 pts [-10, +9] | +28 pts [+17, +40] |
| Questions answered with a best guess (documents gave no usable basis) | 6% [2, 10] | 64% [56, 72] | 48% [39, 56] | 62% [53, 72] | 64% [54, 72] | 33% [24, 42] | -58 pts [-66, -49] | -16 pts [-26, -7] | -1 pts [-12, +9] | +0 pts [-11, +11] | -30 pts [-42, -19] |
| Masked correctness: exact (% of set A questions) | 43% [34, 51] | 41% [33, 50] | 39% [31, 48] | 40% [32, 49] | 39% [30, 48] | 41% [32, 50] | +1 pts [-7, +9] | -2 pts [-9, +5] | -1 pts [-8, +7] | -2 pts [-10, +5] | +0 pts [-8, +7] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 82% [74, 87] | 84% [77, 90] | 84% [77, 90] | 89% [83, 94] | 83% [76, 89] | 82% [74, 88] | -3 pts [-10, +4] | -1 pts [-7, +5] | +4 pts [-2, +12] | -1 pts [-9, +5] | -3 pts [-10, +4] |
| Masked correctness: different category (% of set A questions) | 14% [8, 21] | 13% [8, 20] | 15% [9, 21] | 10% [5, 15] | 15% [9, 22] | 16% [10, 24] | +1 pts [-6, +8] | +1 pts [-4, +8] | -4 pts [-10, +3] | +1 pts [-5, +8] | +3 pts [-5, +10] |
| Masked correctness: not comparable (% of set A questions) | 4% [1, 7] | 2% [0, 5] | 1% [0, 4] | 1% [0, 4] | 1% [0, 4] | 1% [0, 2] | +1 pts [-3, +5] | -1 pts [-4, +3] | -1 pts [-4, +2] | -1 pts [-4, +3] | -1 pts [-5, +1] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 1% [0, 2] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 1% [0, 4] | +1 pts [+0, +2] | +0 pts [+0, +0] | +0 pts [+0, +0] | +1 pts [+0, +2] | +1 pts [+0, +4] |

## Set B only (value never stated; factual consistency)

| Metric | gemini_knowledge | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 0.97 [0.95, 0.99] | 7.68 [7.42, 7.85] | 7.65 [7.42, 7.82] | 7.65 [7.43, 7.83] | 6.68 [6.35, 6.99] | 7.57 [7.37, 7.73] | -6.71 [-6.88, -6.47] | -0.03 [-0.23, +0.20] | -0.02 [-0.22, +0.18] | -1.00 [-1.29, -0.69] | -0.11 [-0.31, +0.13] |
| Questions answered from literature | 91% [88, 95] | 29% [24, 35] | 43% [37, 50] | 26% [20, 32] | 25% [20, 30] | 60% [54, 66] | +62 pts [+56, +69] | +14 pts [+7, +21] | -3 pts [-10, +3] | -4 pts [-12, +3] | +31 pts [+24, +38] |
| Questions answered with a best guess (documents gave no usable basis) | 6% [3, 8] | 67% [61, 72] | 53% [46, 59] | 71% [65, 77] | 72% [66, 77] | 36% [30, 42] | -61 pts [-67, -54] | -14 pts [-21, -7] | +4 pts [-3, +12] | +5 pts [-3, +13] | -31 pts [-38, -23] |
| Factual consistency: consistent (% of set B questions) | 97% [94, 99] | 96% [92, 98] | 96% [93, 98] | 97% [95, 99] | 96% [93, 99] | 96% [94, 98] | +1 pts [-1, +4] | +0 pts [-3, +3] | +1 pts [-1, +4] | +1 pts [-2, +4] | +1 pts [-2, +4] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 1] | 0% [0, 0] | 1% [0, 2] | 0% [0, 1] | 0% [0, 1] | 0% [0, 0] | +0 pts [+0, +1] | +1 pts [+0, +2] | +0 pts [+0, +1] | +0 pts [+0, +1] | +0 pts [+0, +0] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 3% [1, 5] | 4% [2, 7] | 3% [1, 6] | 3% [1, 5] | 3% [1, 6] | 4% [2, 6] | -1 pts [-4, +1] | -1 pts [-4, +1] | -2 pts [-5, +0] | -1 pts [-4, +1] | -1 pts [-4, +2] |

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
| anthropometric | 22 | 50% | 55% | 64% | 41% | 55% | 36% | 0% | 14% | 0% | 9% | 5% | 23% |
| laboratory | 77 | 32% | 30% | 29% | 26% | 25% | 34% | 17% | 10% | 13% | 10% | 17% | 14% |
| vital_sign | 42 | 57% | 55% | 45% | 67% | 57% | 57% | 17% | 19% | 26% | 10% | 17% | 17% |

### True value (judge's category)

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| high | 73 | 36% | 32% | 31% | 27% | 30% | 36% | 13% | 15% | 14% | 11% | 17% | 16% |
| low | 33 | 48% | 47% | 44% | 40% | 38% | 45% | 3% | 6% | 9% | 7% | 9% | 6% |
| normal | 43 | 49% | 51% | 46% | 63% | 57% | 46% | 26% | 14% | 23% | 10% | 16% | 27% |
| not_applicable | 4 | 100% | 67% | 100% | – | 100% | 100% | 0% | 33% | 0% | – | 0% | 0% |
| unknown | 3 | 0% | – | – | – | 0% | 0% | 0% | – | – | – | 0% | 0% |

### Variable typical of the diagnosis

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| no | 83 | 45% | 41% | 41% | 46% | 46% | 41% | 20% | 19% | 22% | 13% | 22% | 19% |
| yes | 58 | 40% | 41% | 36% | 33% | 29% | 41% | 5% | 5% | 5% | 5% | 5% | 12% |

## Diagnostics

- **gemini_knowledge:** answer paths {'literature': 375, 'best_guess': 23, 'off_topic': 1, 'case_study': 6, 'query_builder_declined': 7, 'synthesizer_unanswerable': 1}; source article removed for 0 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **current:** answer paths {'best_guess': 271, 'literature': 128, 'case_study': 2, 'query_builder_declined': 10, 'off_topic': 1, 'synthesizer_unanswerable': 1}; source article removed for 51 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **improved_1to4:** answer paths {'literature': 189, 'best_guess': 210, 'case_study': 5, 'query_builder_declined': 9}; source article removed for 60 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_exa_instant:** answer paths {'literature': 122, 'best_guess': 281, 'case_study': 3, 'query_builder_declined': 7}; source article removed for 40 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_parallel_basic:** answer paths {'literature': 115, 'best_guess': 285, 'case_study': 3, 'synthesizer_unanswerable': 1, 'query_builder_declined': 9}; source article removed for 31 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_perplexity:** answer paths {'best_guess': 145, 'literature': 253, 'query_builder_declined': 8, 'case_study': 4, 'synthesizer_unanswerable': 1, 'off_topic': 2}; source article removed for 40 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **Masked correctness:** 15 of 842 voted labels were "not comparable" (reported as their own label).
- **Judge errors (all attempts, all judges):** 93 judgment(s) failed; rerun the judge step to retry them.

## Judge panel agreement

| Metric | Answers | Unanimous | Majority | Tie broken by the main judge | Tie broken by the next judge | Fewer than all votes |
|---|---|---|---|---|---|---|
| masked correctness | 842 | 73% | 26% | 1% | 0% | 0 |
| factual consistency | 1577 | 99% | 1% | 0% | 0% | 0 |

- **masked correctness, `google/gemini-3.5-flash-lite` vs `qwen/qwen3.8-flash`:** 663/842 identical labels, Cohen's κ = 0.66.
- **masked correctness, `google/gemini-3.5-flash-lite` vs `openai/gpt-6-luna`:** 644/842 identical labels, Cohen's κ = 0.63.
- **masked correctness, `qwen/qwen3.8-flash` vs `openai/gpt-6-luna`:** 755/842 identical labels, Cohen's κ = 0.83.
- **factual consistency, `google/gemini-3.5-flash-lite` vs `qwen/qwen3.8-flash`:** 1566/1577 identical labels, Cohen's κ = 0.35.
- **factual consistency, `google/gemini-3.5-flash-lite` vs `openai/gpt-6-luna`:** 1570/1577 identical labels, Cohen's κ = 0.36.
- **factual consistency, `qwen/qwen3.8-flash` vs `openai/gpt-6-luna`:** 1569/1577 identical labels, Cohen's κ = 0.43.

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
| judge: factual consistency (google/gemini-3.5-flash-lite) | $0.6965 |
| judge: factual consistency (openai/gpt-6-luna) | $0.1983 |
| judge: factual consistency (qwen/qwen3.8-flash) | $0.2859 |
| validation: controls (panel) | $0.0000 |
| validation: flipped truth (panel) | $0.0000 |
| **total** | **$14.8252** |

Cross-check: the OpenRouter key's usage counter, read right after each of the 5 benchmark commands, rose by $4.0319. The counter lags behind requests, so this undercounts; per-call usage.cost above is the accounting source.

