# Retrieval benchmark report

- Workspace: `environment/results/repeats/run_07/sets_ab`
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
| Documents returned per question | 0.97 [0.96, 0.99] | 7.86 [7.76, 7.96] | 7.88 [7.78, 7.96] | 7.76 [7.65, 7.86] | 7.66 [7.52, 7.78] | 7.63 [7.51, 7.74] | -6.89 [-6.98, -6.79] | +0.01 [-0.11, +0.14] | -0.10 [-0.23, +0.02] | -0.21 [-0.36, -0.05] | -0.23 [-0.33, -0.14] |
| Questions answered from literature | 90% [87, 93] | 33% [28, 38] | 50% [45, 55] | 30% [25, 34] | 30% [25, 34] | 61% [56, 66] | +57 pts [+51, +63] | +16 pts [+11, +22] | -4 pts [-10, +3] | -4 pts [-10, +3] | +27 pts [+21, +34] |
| Questions answered with a best guess (documents gave no usable basis) | 7% [5, 10] | 65% [60, 70] | 49% [43, 54] | 69% [64, 74] | 68% [63, 72] | 37% [32, 42] | -58 pts [-63, -52] | -16 pts [-22, -10] | +4 pts [-2, +10] | +3 pts [-4, +9] | -28 pts [-35, -22] |
| Masked correctness: exact (% of set A questions) | 46% [36, 55] | 45% [37, 54] | 45% [36, 54] | 48% [39, 56] | 45% [36, 54] | 44% [35, 53] | +1 pts [-8, +9] | -1 pts [-9, +8] | +2 pts [-7, +11] | -1 pts [-8, +6] | -1 pts [-10, +7] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 84% [76, 90] | 84% [78, 90] | 84% [78, 90] | 85% [79, 91] | 82% [75, 88] | 81% [74, 87] | -1 pts [-7, +6] | +0 pts [-6, +5] | +1 pts [-6, +7] | -2 pts [-7, +3] | -4 pts [-9, +2] |
| Masked correctness: different category (% of set A questions) | 16% [9, 23] | 13% [8, 20] | 14% [9, 21] | 13% [8, 20] | 16% [10, 23] | 18% [12, 25] | +2 pts [-4, +8] | +1 pts [-4, +6] | +0 pts [-6, +6] | +3 pts [-2, +8] | +5 pts [-1, +11] |
| Masked correctness: not comparable (% of set A questions) | 1% [0, 2] | 2% [0, 5] | 1% [0, 4] | 1% [0, 2] | 1% [0, 2] | 1% [0, 2] | -1 pts [-4, +0] | -1 pts [-3, +1] | -1 pts [-4, +1] | -1 pts [-4, +0] | -1 pts [-4, +0] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 1% [0, 2] | 0% [0, 0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +1 pts [+0, +2] | +1 pts [+0, +2] | +0 pts [+0, +0] |
| Factual consistency: consistent (% of set B questions) | 97% [95, 99] | 99% [97, 100] | 98% [96, 99] | 98% [96, 100] | 96% [93, 98] | 97% [95, 99] | -1 pts [-4, +1] | -1 pts [-3, +2] | -0 pts [-2, +1] | -3 pts [-5, +0] | -1 pts [-3, +0] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 0] | 0% [0, 1] | 1% [0, 2] | 0% [0, 0] | 1% [0, 2] | 0% [0, 1] | -0 pts [-1, +0] | +0 pts [-1, +2] | -0 pts [-1, +0] | +0 pts [-1, +2] | +0 pts [-1, +1] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 3% [1, 5] | 1% [0, 3] | 1% [0, 3] | 2% [0, 4] | 3% [1, 6] | 2% [1, 4] | +2 pts [+0, +4] | +0 pts [-1, +2] | +1 pts [-1, +2] | +2 pts [+0, +5] | +1 pts [+0, +3] |
| Retrieval cost per question (search fees, search/rerank LLM; USD) | $0.00071 | $0.00000 | $0.00000 | $0.00707 | $0.00507 | $0.00507 | +0.00071 [+0.00070, +0.00073] | +0.00000 [+0.00000, +0.00000] | +0.00707 [+0.00698, +0.00714] | +0.00507 [+0.00498, +0.00515] | +0.00507 [+0.00500, +0.00514] |
| medsim LLM cost per question (Stages A–C, USD) | $0.00187 | $0.00234 | $0.00251 | $0.00215 | $0.00233 | $0.00264 | -0.00047 [-0.00064, -0.00032] | +0.00017 [-0.00003, +0.00038] | -0.00019 [-0.00036, -0.00003] | -0.00002 [-0.00022, +0.00019] | +0.00029 [+0.00009, +0.00048] |
| Total cost per question (USD) | $0.00258 | $0.00234 | $0.00251 | $0.00922 | $0.00740 | $0.00771 | +0.00024 [+0.00008, +0.00039] | +0.00017 [-0.00003, +0.00038] | +0.00688 [+0.00669, +0.00706] | +0.00505 [+0.00483, +0.00528] | +0.00537 [+0.00515, +0.00557] |
| Wall time per question (s) | 63.9 [60.6, 67.2] | 127.1 [120.8, 133.0] | 106.6 [101.9, 111.5] | 81.4 [72.5, 92.4] | 81.6 [75.5, 88.0] | 90.9 [84.3, 97.9] | -63.20 [-69.08, -57.61] | -20.50 [-26.46, -14.30] | -45.64 [-55.75, -34.08] | -45.47 [-53.23, -37.92] | -36.21 [-44.12, -28.47] |
| Time outside medsim's LLM calls per question (≈ retrieval; s) | 3.13 [3.06, 3.21] | 51.92 [47.79, 56.33] | 26.77 [25.08, 28.53] | 5.51 [5.22, 5.82] | 6.11 [5.86, 6.36] | 6.38 [5.94, 6.98] | -48.79 [-53.21, -44.68] | -25.15 [-28.98, -21.29] | -46.42 [-50.84, -42.35] | -45.81 [-50.23, -41.73] | -45.54 [-49.96, -41.42] |

## Set A only (hidden value; masked correctness)

| Metric | gemini_knowledge | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 0.99 [0.96, 1.00] | 7.83 [7.61, 8.00] | 7.89 [7.73, 8.00] | 7.78 [7.63, 7.89] | 7.65 [7.44, 7.81] | 7.62 [7.43, 7.77] | -6.84 [-7.00, -6.65] | +0.06 [-0.11, +0.28] | -0.05 [-0.28, +0.21] | -0.18 [-0.39, +0.04] | -0.21 [-0.41, -0.01] |
| Questions answered from literature | 91% [86, 95] | 40% [32, 48] | 55% [47, 63] | 35% [26, 43] | 36% [28, 45] | 62% [54, 70] | +51 pts [+42, +60] | +16 pts [+6, +25] | -5 pts [-14, +4] | -4 pts [-14, +7] | +22 pts [+12, +32] |
| Questions answered with a best guess (documents gave no usable basis) | 8% [4, 13] | 58% [50, 66] | 43% [36, 51] | 65% [56, 73] | 62% [54, 70] | 37% [29, 45] | -50 pts [-60, -41] | -15 pts [-25, -5] | +6 pts [-3, +16] | +4 pts [-6, +14] | -21 pts [-31, -12] |
| Masked correctness: exact (% of set A questions) | 46% [36, 55] | 45% [37, 54] | 45% [36, 54] | 48% [39, 56] | 45% [36, 54] | 44% [35, 53] | +1 pts [-8, +9] | -1 pts [-9, +8] | +2 pts [-7, +11] | -1 pts [-8, +6] | -1 pts [-10, +7] |
| Masked correctness: same category (incl. exact) (% of set A questions) | 84% [76, 90] | 84% [78, 90] | 84% [78, 90] | 85% [79, 91] | 82% [75, 88] | 81% [74, 87] | -1 pts [-7, +6] | +0 pts [-6, +5] | +1 pts [-6, +7] | -2 pts [-7, +3] | -4 pts [-9, +2] |
| Masked correctness: different category (% of set A questions) | 16% [9, 23] | 13% [8, 20] | 14% [9, 21] | 13% [8, 20] | 16% [10, 23] | 18% [12, 25] | +2 pts [-4, +8] | +1 pts [-4, +6] | +0 pts [-6, +6] | +3 pts [-2, +8] | +5 pts [-1, +11] |
| Masked correctness: not comparable (% of set A questions) | 1% [0, 2] | 2% [0, 5] | 1% [0, 4] | 1% [0, 2] | 1% [0, 2] | 1% [0, 2] | -1 pts [-4, +0] | -1 pts [-3, +1] | -1 pts [-4, +1] | -1 pts [-4, +0] | -1 pts [-4, +0] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 1% [0, 2] | 1% [0, 2] | 0% [0, 0] | +0 pts [+0, +0] | +0 pts [+0, +0] | +1 pts [+0, +2] | +1 pts [+0, +2] | +0 pts [+0, +0] |

## Set B only (value never stated; factual consistency)

| Metric | gemini_knowledge | current | improved_1to4 | openrouter_exa_instant | openrouter_parallel_basic | openrouter_perplexity | gemini_knowledge − current | improved_1to4 − current | openrouter_exa_instant − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 0.97 [0.94, 0.99] | 7.88 [7.76, 7.97] | 7.88 [7.75, 7.97] | 7.75 [7.61, 7.87] | 7.67 [7.46, 7.82] | 7.64 [7.47, 7.78] | -6.92 [-7.01, -6.79] | -0.01 [-0.18, +0.15] | -0.13 [-0.27, +0.01] | -0.22 [-0.43, -0.04] | -0.24 [-0.36, -0.14] |
| Questions answered from literature | 90% [86, 93] | 30% [25, 36] | 47% [40, 54] | 27% [21, 32] | 26% [21, 32] | 60% [54, 66] | +60 pts [+53, +66] | +17 pts [+10, +24] | -3 pts [-11, +4] | -4 pts [-11, +4] | +30 pts [+23, +38] |
| Questions answered with a best guess (documents gave no usable basis) | 7% [4, 10] | 68% [63, 74] | 51% [45, 58] | 71% [66, 77] | 71% [65, 76] | 37% [31, 43] | -61 pts [-68, -55] | -17 pts [-24, -10] | +3 pts [-5, +10] | +2 pts [-5, +9] | -32 pts [-39, -24] |
| Factual consistency: consistent (% of set B questions) | 97% [95, 99] | 99% [97, 100] | 98% [96, 99] | 98% [96, 100] | 96% [93, 98] | 97% [95, 99] | -1 pts [-4, +1] | -1 pts [-3, +2] | -0 pts [-2, +1] | -3 pts [-5, +0] | -1 pts [-3, +0] |
| Factual consistency: inconsistent (% of set B questions) | 0% [0, 0] | 0% [0, 1] | 1% [0, 2] | 0% [0, 0] | 1% [0, 2] | 0% [0, 1] | -0 pts [-1, +0] | +0 pts [-1, +2] | -0 pts [-1, +0] | +0 pts [-1, +2] | +0 pts [-1, +1] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 3% [1, 5] | 1% [0, 3] | 1% [0, 3] | 2% [0, 4] | 3% [1, 6] | 2% [1, 4] | +2 pts [+0, +4] | +0 pts [-1, +2] | +1 pts [-1, +2] | +2 pts [+0, +5] | +1 pts [+0, +3] |

## Cost

All questions that ran.

| Method | Questions | Retrieval (search fees + search model) | medsim LLM (Stages A–C) | Total | Total per question | Median wall time |
|---|---|---|---|---|---|---|
| gemini_knowledge | 413 | $0.2941 | $0.7721 | $1.0662 | $0.00258 | 57.5 s |
| current | 413 | $0.0000 | $0.9682 | $0.9682 | $0.00234 | 121.3 s |
| improved_1to4 | 413 | $0.0000 | $1.0364 | $1.0364 | $0.00251 | 95.1 s |
| openrouter_exa_instant | 413 | $2.9202 | $0.8883 | $3.8085 | $0.00922 | 62.0 s |
| openrouter_parallel_basic | 413 | $2.0951 | $0.9604 | $3.0555 | $0.00740 | 66.6 s |
| openrouter_perplexity | 413 | $2.0959 | $1.0900 | $3.1858 | $0.00771 | 74.1 s |

## By subgroup (set A)

### Variable category

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| anthropometric | 22 | 50% | 59% | 45% | 59% | 64% | 55% | 9% | 5% | 9% | 5% | 5% | 9% |
| laboratory | 77 | 35% | 35% | 35% | 35% | 31% | 34% | 18% | 10% | 13% | 12% | 17% | 18% |
| vital_sign | 42 | 64% | 57% | 62% | 64% | 60% | 57% | 14% | 24% | 19% | 21% | 21% | 24% |

### True value (judge's category)

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| high | 72 | 39% | 35% | 37% | 41% | 34% | 37% | 20% | 13% | 17% | 14% | 17% | 21% |
| low | 33 | 42% | 53% | 55% | 39% | 48% | 41% | 6% | 0% | 0% | 12% | 12% | 9% |
| normal | 41 | 60% | 56% | 51% | 66% | 63% | 55% | 17% | 28% | 20% | 14% | 20% | 24% |
| not_applicable | 3 | 100% | 100% | 50% | 100% | 100% | 100% | 0% | 0% | 50% | 0% | 0% | 0% |
| unknown | 1 | – | – | – | 0% | 0% | – | – | – | – | 0% | 0% | – |

### Variable typical of the diagnosis

| Group | n | Masked correctness: exact (% of set A questions) — gemini_knowledge | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — gemini_knowledge | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| no | 83 | 49% | 49% | 46% | 48% | 51% | 48% | 22% | 20% | 22% | 18% | 22% | 25% |
| yes | 58 | 41% | 40% | 43% | 47% | 36% | 38% | 7% | 3% | 3% | 7% | 9% | 9% |

## Diagnostics

- **gemini_knowledge:** answer paths {'literature': 372, 'best_guess': 30, 'case_study': 3, 'query_builder_declined': 8}; source article removed for 0 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **current:** answer paths {'literature': 138, 'best_guess': 268, 'case_study': 4, 'query_builder_declined': 3}; source article removed for 50 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **improved_1to4:** answer paths {'literature': 206, 'best_guess': 201, 'case_study': 2, 'query_builder_declined': 4}; source article removed for 53 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_exa_instant:** answer paths {'literature': 122, 'best_guess': 285, 'off_topic': 1, 'query_builder_declined': 4, 'withheld': 1}; source article removed for 45 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_parallel_basic:** answer paths {'literature': 122, 'best_guess': 280, 'off_topic': 1, 'case_study': 1, 'query_builder_declined': 7, 'synthesizer_unanswerable': 2}; source article removed for 37 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_perplexity:** answer paths {'best_guess': 152, 'literature': 251, 'case_study': 4, 'query_builder_declined': 5, 'synthesizer_unanswerable': 1}; source article removed for 39 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **Masked correctness:** 9 of 844 voted labels were "not comparable" (reported as their own label).
- **Judge errors (all attempts, all judges):** 247 judgment(s) failed; rerun the judge step to retry them.

## Judge panel agreement

| Metric | Answers | Unanimous | Majority | Tie broken by the main judge | Tie broken by the next judge | Fewer than all votes |
|---|---|---|---|---|---|---|
| masked correctness | 844 | 82% | 17% | 1% | 0% | 0 |
| factual consistency | 1597 | 99% | 1% | 0% | 0% | 0 |

- **masked correctness, `anthropic/claude-haiku-5.5` vs `z-ai/glm-5.3-flash`:** 747/844 identical labels, Cohen's κ = 0.82.
- **masked correctness, `anthropic/claude-haiku-5.5` vs `openai/gpt-6-luna`:** 725/844 identical labels, Cohen's κ = 0.78.
- **masked correctness, `z-ai/glm-5.3-flash` vs `openai/gpt-6-luna`:** 757/844 identical labels, Cohen's κ = 0.83.
- **factual consistency, `anthropic/claude-haiku-5.5` vs `z-ai/glm-5.3-flash`:** 1587/1597 identical labels, Cohen's κ = 0.54.
- **factual consistency, `anthropic/claude-haiku-5.5` vs `openai/gpt-6-luna`:** 1584/1597 identical labels, Cohen's κ = 0.13.
- **factual consistency, `z-ai/glm-5.3-flash` vs `openai/gpt-6-luna`:** 1590/1597 identical labels, Cohen's κ = 0.22.

## Benchmark spend

| Step | Cost (USD, OpenRouter usage.cost) |
|---|---|
| extract (case facts) | $0.0000 |
| redact + Stage A checks (accepted) | $0.0000 |
| redact + Stage A checks (rejected) | $0.0000 |
| run (all methods; search fees included) | $13.1207 |
| judge: masked correctness (google/gemini-3.5-flash-lite) | $0.5063 |
| judge: masked correctness (openai/gpt-6-luna) | $0.1611 |
| judge: masked correctness (qwen/qwen3.8-flash) | $0.3190 |
| judge: masked correctness (typesafe/jev-1.13) | $0.0354 |
| judge: masked correctness (z-ai/glm-5.3-flash) | $0.1347 |
| judge: masked correctness (anthropic/claude-haiku-5.5) | $0.2330 |
| judge: factual consistency (google/gemini-3.5-flash-lite) | $0.9310 |
| judge: factual consistency (openai/gpt-6-luna) | $0.1999 |
| judge: factual consistency (qwen/qwen3.8-flash) | $0.2627 |
| judge: factual consistency (typesafe/jev-1.13) | $0.0560 |
| judge: factual consistency (anthropic/claude-haiku-5.5) | $0.3192 |
| judge: factual consistency (z-ai/glm-5.3-flash) | $0.1580 |
| validation: controls (panel) | $0.0000 |
| validation: flipped truth (panel) | $0.0000 |
| **total** | **$16.4369** |

Cross-check: the OpenRouter key's usage counter, read right after each of the 6 benchmark commands, rose by $4.1543. The counter lags behind requests, so this undercounts; per-call usage.cost above is the accounting source.

