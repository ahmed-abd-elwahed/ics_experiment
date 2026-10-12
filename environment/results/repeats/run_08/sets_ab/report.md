# Retrieval benchmark report

- Workspace: `environment/results/repeats/run_08/sets_ab`
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
| Documents returned per question | 0.99 [0.97, 1.00] | 7.86 [7.76, 7.96] | 7.77 [7.63, 7.89] | 7.77 [7.66, 7.86] | 7.58 [7.43, 7.70] | 7.70 [7.59, 7.79] | -6.88 [-6.96, -6.78] | -0.10 [-0.25, +0.06] | -0.10 [-0.24, +0.03] | -0.29 [-0.44, -0.15] | -0.16 [-0.30, -0.04] |
| Questions answered from literature | 92% [90, 95] | 31% [27, 35] | 45% [40, 50] | 29% [24, 33] | 32% [27, 36] | 64% [59, 69] | +62 pts [+57, +67] | +14 pts [+8, +20] | -2 pts [-8, +3] | +1 pts [-5, +7] | +33 pts [+27, +40] |
| Questions answered with a best guess (documents gave no usable basis) | 6% [4, 8] | 67% [63, 71] | 52% [47, 57] | 69% [64, 74] | 65% [61, 70] | 34% [29, 39] | -61 pts [-66, -56] | -15 pts [-21, -9] | +2 pts [-4, +8] | -2 pts [-8, +4] | -33 pts [-39, -27] |
| Masked correctness: exact (% of set A questions) | 47% [38, 56] | 41% [32, 50] | 40% [31, 48] | 42% [33, 50] | 43% [34, 52] | 45% [37, 54] | +6 pts [-2, +14] | -1 pts [-9, +6] | +1 pts [-8, +10] | +1 pts [-7, +10] | +4 pts [-4, +13] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 84% [78, 90] | 87% [80, 92] | 83% [76, 89] | 82% [74, 88] | 84% [77, 90] | 79% [71, 86] | -2 pts [-7, +4] | -4 pts [-10, +2] | -5 pts [-12, +2] | -2 pts [-8, +4] | -8 pts [-14, -1] |
| Masked correctness: different category (% of set A questions) | 13% [8, 20] | 12% [7, 18] | 15% [9, 22] | 17% [10, 24] | 13% [8, 20] | 21% [14, 28] | +1 pts [-4, +6] | +3 pts [-3, +9] | +5 pts [-1, +11] | +1 pts [-3, +6] | +9 pts [+3, +15] |
| Masked correctness: not comparable (% of set A questions) | 2% [0, 5] | 1% [0, 2] | 1% [0, 4] | 1% [0, 2] | 1% [0, 4] | 0% [0, 0] | +1 pts [+0, +4] | +1 pts [-1, +3] | +0 pts [-2, +2] | +1 pts [-1, +3] | -1 pts [-2, +0] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 0% [0, 0] | 1% [0, 2] | 1% [0, 2] | 1% [0, 2] | 1% [0, 2] | 1% [0, 2] | -1 pts [-2, +0] | +0 pts [-2, +2] | +0 pts [+0, +0] | +0 pts [-2, +2] | +0 pts [-2, +2] |
| Factual consistency: consistent (% of set B questions) | 99% [97, 100] | 97% [95, 99] | 96% [94, 98] | 98% [96, 99] | 97% [95, 99] | 97% [95, 99] | +1 pts [-1, +3] | -1 pts [-4, +1] | +0 pts [-2, +3] | -0 pts [-3, +2] | -0 pts [-3, +2] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 0] | 0% [0, 1] | 1% [0, 3] | 0% [0, 0] | 0% [0, 1] | 1% [0, 3] | -0 pts [-1, +0] | +1 pts [+0, +2] | -0 pts [-1, +0] | +0 pts [-1, +1] | +1 pts [-1, +2] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 1% [0, 3] | 2% [1, 4] | 3% [1, 5] | 2% [1, 4] | 3% [1, 5] | 2% [0, 4] | -1 pts [-3, +1] | +0 pts [-2, +3] | +0 pts [-2, +2] | +0 pts [-2, +3] | -0 pts [-3, +2] |
| Retrieval cost per question (search fees, search/rerank LLM; USD) | $0.00072 | $0.00000 | $0.00000 | $0.00707 | $0.00506 | $0.00511 | +0.00072 [+0.00071, +0.00073] | +0.00000 [+0.00000, +0.00000] | +0.00707 [+0.00698, +0.00714] | +0.00506 [+0.00498, +0.00513] | +0.00511 [+0.00505, +0.00517] |
| medsim LLM cost per question (Stages A–C, USD) | $0.00200 | $0.00258 | $0.00267 | $0.00239 | $0.00271 | $0.00316 | -0.00058 [-0.00077, -0.00040] | +0.00009 [-0.00011, +0.00029] | -0.00019 [-0.00042, +0.00002] | +0.00012 [-0.00013, +0.00037] | +0.00058 [+0.00033, +0.00084] |
| Total cost per question (USD) | $0.00272 | $0.00258 | $0.00267 | $0.00946 | $0.00776 | $0.00828 | +0.00014 [-0.00004, +0.00033] | +0.00009 [-0.00011, +0.00029] | +0.00688 [+0.00663, +0.00710] | +0.00518 [+0.00491, +0.00545] | +0.00570 [+0.00543, +0.00597] |
| Wall time per question (s) | 77.0 [72.4, 81.9] | 130.9 [124.4, 137.9] | 105.2 [99.4, 111.2] | 78.2 [73.5, 83.2] | 91.3 [85.3, 97.4] | 109.1 [102.5, 116.6] | -53.90 [-60.83, -47.20] | -25.65 [-33.03, -18.34] | -52.66 [-60.61, -45.15] | -39.61 [-47.95, -31.54] | -21.76 [-30.78, -13.28] |
| Time outside medsim's LLM calls per question (≈ retrieval; s) | 3.02 [2.97, 3.07] | 44.45 [41.08, 48.02] | 21.34 [20.11, 22.55] | 5.67 [5.43, 5.93] | 6.62 [6.35, 6.89] | 6.45 [6.16, 6.76] | -41.43 [-44.96, -38.05] | -23.11 [-26.37, -20.05] | -38.78 [-42.27, -35.46] | -37.82 [-41.44, -34.45] | -38.00 [-41.51, -34.73] |

## Set A only (hidden value; masked correctness)

| Metric | gemini_knowledge | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 0.99 [0.96, 1.00] | 7.94 [7.82, 8.00] | 7.77 [7.54, 7.95] | 7.77 [7.63, 7.88] | 7.50 [7.27, 7.70] | 7.67 [7.53, 7.79] | -6.96 [-7.02, -6.85] | -0.17 [-0.44, +0.06] | -0.17 [-0.33, -0.01] | -0.45 [-0.69, -0.22] | -0.27 [-0.44, -0.11] |
| Questions answered from literature | 91% [86, 95] | 34% [27, 42] | 48% [41, 57] | 37% [29, 46] | 38% [30, 45] | 65% [57, 74] | +57 pts [+47, +65] | +14 pts [+5, +24] | +3 pts [-7, +13] | +4 pts [-6, +14] | +31 pts [+21, +41] |
| Questions answered with a best guess (documents gave no usable basis) | 8% [4, 13] | 65% [57, 72] | 50% [41, 58] | 62% [53, 70] | 60% [52, 68] | 34% [26, 43] | -57 pts [-65, -47] | -15 pts [-25, -5] | -3 pts [-12, +7] | -5 pts [-15, +5] | -30 pts [-41, -21] |
| Masked correctness: exact (% of set A questions) | 47% [38, 56] | 41% [32, 50] | 40% [31, 48] | 42% [33, 50] | 43% [34, 52] | 45% [37, 54] | +6 pts [-2, +14] | -1 pts [-9, +6] | +1 pts [-8, +10] | +1 pts [-7, +10] | +4 pts [-4, +13] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 84% [78, 90] | 87% [80, 92] | 83% [76, 89] | 82% [74, 88] | 84% [77, 90] | 79% [71, 86] | -2 pts [-7, +4] | -4 pts [-10, +2] | -5 pts [-12, +2] | -2 pts [-8, +4] | -8 pts [-14, -1] |
| Masked correctness: different category (% of set A questions) | 13% [8, 20] | 12% [7, 18] | 15% [9, 22] | 17% [10, 24] | 13% [8, 20] | 21% [14, 28] | +1 pts [-4, +6] | +3 pts [-3, +9] | +5 pts [-1, +11] | +1 pts [-3, +6] | +9 pts [+3, +15] |
| Masked correctness: not comparable (% of set A questions) | 2% [0, 5] | 1% [0, 2] | 1% [0, 4] | 1% [0, 2] | 1% [0, 4] | 0% [0, 0] | +1 pts [+0, +4] | +1 pts [-1, +3] | +0 pts [-2, +2] | +1 pts [-1, +3] | -1 pts [-2, +0] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 0% [0, 0] | 1% [0, 2] | 1% [0, 2] | 1% [0, 2] | 1% [0, 2] | 1% [0, 2] | -1 pts [-2, +0] | +0 pts [-2, +2] | +0 pts [+0, +0] | +0 pts [-2, +2] | +0 pts [-2, +2] |

## Set B only (value never stated; factual consistency)

| Metric | gemini_knowledge | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 0.99 [0.97, 1.00] | 7.82 [7.68, 7.94] | 7.76 [7.60, 7.91] | 7.76 [7.62, 7.88] | 7.62 [7.45, 7.77] | 7.71 [7.56, 7.84] | -6.84 [-6.96, -6.70] | -0.06 [-0.27, +0.13] | -0.06 [-0.24, +0.11] | -0.20 [-0.41, -0.01] | -0.11 [-0.29, +0.06] |
| Questions answered from literature | 93% [90, 96] | 29% [24, 35] | 43% [37, 49] | 25% [19, 30] | 29% [23, 35] | 64% [57, 69] | +64 pts [+57, +71] | +14 pts [+7, +21] | -5 pts [-12, +3] | -0 pts [-7, +7] | +34 pts [+26, +41] |
| Questions answered with a best guess (documents gave no usable basis) | 5% [3, 8] | 68% [62, 74] | 54% [48, 60] | 73% [68, 79] | 68% [63, 74] | 34% [28, 40] | -63 pts [-70, -57] | -15 pts [-22, -7] | +5 pts [-3, +12] | +0 pts [-8, +8] | -34 pts [-42, -27] |
| Factual consistency: consistent (% of set B questions) | 99% [97, 100] | 97% [95, 99] | 96% [94, 98] | 98% [96, 99] | 97% [95, 99] | 97% [95, 99] | +1 pts [-1, +3] | -1 pts [-4, +1] | +0 pts [-2, +3] | -0 pts [-3, +2] | -0 pts [-3, +2] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 0] | 0% [0, 1] | 1% [0, 3] | 0% [0, 0] | 0% [0, 1] | 1% [0, 3] | -0 pts [-1, +0] | +1 pts [+0, +2] | -0 pts [-1, +0] | +0 pts [-1, +1] | +1 pts [-1, +2] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 1% [0, 3] | 2% [1, 4] | 3% [1, 5] | 2% [1, 4] | 3% [1, 5] | 2% [0, 4] | -1 pts [-3, +1] | +0 pts [-2, +3] | +0 pts [-2, +2] | +0 pts [-2, +3] | -0 pts [-3, +2] |

## Cost

All questions that ran.

| Method | Questions | Retrieval (search fees + search model) | medsim LLM (Stages A–C) | Total | Total per question | Median wall time |
|---|---|---|---|---|---|---|
| gemini_knowledge | 413 | $0.2977 | $0.8265 | $1.1242 | $0.00272 | 67.1 s |
| current | 413 | $0.0000 | $1.0660 | $1.0660 | $0.00258 | 117.7 s |
| improved_1to4 | 413 | $0.0000 | $1.1044 | $1.1044 | $0.00267 | 92.1 s |
| openrouter_exa_instant | 413 | $2.9200 | $0.9866 | $3.9066 | $0.00946 | 67.0 s |
| openrouter_parallel_basic | 413 | $2.0894 | $1.1174 | $3.2068 | $0.00776 | 76.8 s |
| openrouter_perplexity | 413 | $2.1122 | $1.3062 | $3.4184 | $0.00828 | 92.9 s |

## By subgroup (set A)

### Variable category

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| anthropometric | 22 | 55% | 59% | 59% | 41% | 59% | 55% | 5% | 9% | 0% | 18% | 5% | 23% |
| laboratory | 77 | 34% | 25% | 26% | 34% | 31% | 34% | 16% | 12% | 14% | 12% | 13% | 17% |
| vital_sign | 42 | 67% | 62% | 55% | 57% | 55% | 62% | 14% | 14% | 24% | 26% | 19% | 26% |

### True value (judge's category)

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| high | 72 | 39% | 32% | 27% | 37% | 34% | 41% | 16% | 15% | 18% | 14% | 15% | 20% |
| low | 34 | 48% | 45% | 41% | 42% | 35% | 48% | 6% | 3% | 3% | 15% | 12% | 12% |
| normal | 40 | 58% | 51% | 64% | 50% | 63% | 47% | 17% | 16% | 19% | 25% | 14% | 32% |
| not_applicable | 3 | 100% | 100% | 100% | 100% | 100% | 100% | 0% | 0% | 0% | 0% | 0% | 0% |
| unknown | 4 | – | 0% | 0% | 0% | 0% | 0% | – | 0% | 0% | 0% | 0% | 0% |

### Variable typical of the diagnosis

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| no | 83 | 49% | 48% | 48% | 43% | 47% | 47% | 19% | 18% | 20% | 23% | 18% | 28% |
| yes | 58 | 43% | 31% | 28% | 40% | 36% | 43% | 5% | 3% | 7% | 9% | 7% | 10% |

## Diagnostics

- **gemini_knowledge:** answer paths {'literature': 382, 'best_guess': 25, 'case_study': 2, 'query_builder_declined': 3, 'withheld': 1}; source article removed for 0 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **current:** answer paths {'best_guess': 277, 'literature': 128, 'synthesizer_unanswerable': 1, 'case_study': 1, 'withheld': 2, 'query_builder_declined': 4}; source article removed for 50 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **improved_1to4:** answer paths {'best_guess': 216, 'literature': 186, 'case_study': 3, 'query_builder_declined': 8}; source article removed for 61 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_exa_instant:** answer paths {'best_guess': 286, 'literature': 119, 'case_study': 1, 'synthesizer_unanswerable': 2, 'query_builder_declined': 5}; source article removed for 44 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_parallel_basic:** answer paths {'literature': 132, 'best_guess': 270, 'case_study': 3, 'synthesizer_unanswerable': 1, 'query_builder_declined': 6, 'off_topic': 1}; source article removed for 39 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_perplexity:** answer paths {'best_guess': 141, 'literature': 265, 'query_builder_declined': 5, 'case_study': 1, 'synthesizer_unanswerable': 1}; source article removed for 39 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **Masked correctness:** 9 of 841 voted labels were "not comparable" (reported as their own label).
- **Judge errors (all attempts, all judges):** 650 judgment(s) failed; rerun the judge step to retry them.

## Judge panel agreement

| Metric | Answers | Unanimous | Majority | Tie broken by the main judge | Tie broken by the next judge | Fewer than all votes |
|---|---|---|---|---|---|---|
| masked correctness | 841 | 81% | 19% | 0% | 0% | 0 |
| factual consistency | 1597 | 99% | 1% | 0% | 0% | 0 |

- **masked correctness, `anthropic/claude-haiku-5.5` vs `z-ai/glm-5.3-flash`:** 732/841 identical labels, Cohen's κ = 0.80.
- **masked correctness, `anthropic/claude-haiku-5.5` vs `openai/gpt-6-luna`:** 730/841 identical labels, Cohen's κ = 0.79.
- **masked correctness, `z-ai/glm-5.3-flash` vs `openai/gpt-6-luna`:** 736/841 identical labels, Cohen's κ = 0.80.
- **factual consistency, `anthropic/claude-haiku-5.5` vs `z-ai/glm-5.3-flash`:** 1587/1597 identical labels, Cohen's κ = 0.61.
- **factual consistency, `anthropic/claude-haiku-5.5` vs `openai/gpt-6-luna`:** 1585/1597 identical labels, Cohen's κ = 0.25.
- **factual consistency, `z-ai/glm-5.3-flash` vs `openai/gpt-6-luna`:** 1585/1597 identical labels, Cohen's κ = 0.25.

## Benchmark spend

| Step | Cost (USD, OpenRouter usage.cost) |
|---|---|
| extract (case facts) | $0.0000 |
| redact + Stage A checks (accepted) | $0.0000 |
| redact + Stage A checks (rejected) | $0.0000 |
| run (all methods; search fees included) | $13.8265 |
| judge: masked correctness (google/gemini-3.5-flash-lite) | $0.4650 |
| judge: masked correctness (openai/gpt-6-luna) | $0.1591 |
| judge: masked correctness (qwen/qwen3.8-flash) | $0.3114 |
| judge: masked correctness (typesafe/jev-1.13) | $0.0352 |
| judge: masked correctness (z-ai/glm-5.3-flash) | $0.1176 |
| judge: masked correctness (anthropic/claude-haiku-5.5) | $0.2319 |
| judge: factual consistency (google/gemini-3.5-flash-lite) | $0.7057 |
| judge: factual consistency (openai/gpt-6-luna) | $0.2010 |
| judge: factual consistency (qwen/qwen3.8-flash) | $0.2824 |
| judge: factual consistency (typesafe/jev-1.13) | $0.0560 |
| judge: factual consistency (anthropic/claude-haiku-5.5) | $0.3203 |
| judge: factual consistency (z-ai/glm-5.3-flash) | $0.1564 |
| validation: controls (panel) | $0.0000 |
| validation: flipped truth (panel) | $0.0000 |
| **total** | **$16.8685** |

Cross-check: the OpenRouter key's usage counter, read right after each of the 7 benchmark commands, rose by $1.7354. The counter lags behind requests, so this undercounts; per-call usage.cost above is the accounting source.

