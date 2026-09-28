# Retrieval benchmark report

- Workspace: `/private/tmp/claude-502/-Users-ahmed-ics-experiment/b408bf2e-bd80-4110-8f45-2c03ee26b20d/scratchpad/smoke`
- Judge panel: `google/gemini-3.5-flash-lite`, `qwen/qwen3.8-flash`, `openai/gpt-6-luna`. Each answer's label is the panel's majority vote; with no majority, the first (main) judge's label decides.
- medsim models: `deepseek/deepseek-v4-flash-0731`
- `current`: Europe PMC + LitSense passages, relaxation ladders, lexical rerank (the original method)
- `improved_1to4`: changes 1-4: value-first ranking in one list across sources, 50 Europe PMC candidates, animal/age filter, article-body search with excerpts, value-based broadening without the unhelpful rungs (medsim's default since they were measured)
- `openrouter_exa_instant`: openrouter_search with the Exa engine in instant mode; deepseek/deepseek-v4-flash-0731 issues the search
- `openrouter_google`: openrouter_search with the model's native search, Google Search for google/gemini-3.1-flash-lite, which issues the search
- `openrouter_openai`: openrouter_search with the model's native search, OpenAI web search for openai/gpt-6-luna, which issues the search
- `openrouter_parallel_basic`: openrouter_search with the Parallel engine in basic mode; deepseek/deepseek-v4-flash-0731 issues the search
- `openrouter_perplexity`: openrouter_search with the Perplexity engine; deepseek/deepseek-v4-flash-0731 issues the search

## Question sets

- Cases extracted: 272; measured values found: 1235; eligible as hidden values: 536.
- Set A (hidden value): 1 questions accepted; rejected 0 (none).
- Set B (value never stated): 1 questions accepted; rejected 0 (none).
- Every question is scored under every method: each label's percentage is out of all questions in its set. Questions without a successful run (counted as no label): current: 0, improved_1to4: 0, openrouter_exa_instant: 0, openrouter_google: 0, openrouter_openai: 0, openrouter_parallel_basic: 0, openrouter_perplexity: 0.

## All questions (sets A and B)

| Metric | current | improved_1to4 | openrouter_exa_instant | openrouter_google | openrouter_openai | openrouter_parallel_basic | openrouter_perplexity | improved_1to4 − current | openrouter_exa_instant − current | openrouter_google − current | openrouter_openai − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 8.00 [8.00, 8.00] | 8.00 [8.00, 8.00] | 8.00 [8.00, 8.00] | 3.50 [2.00, 5.00] | 4.50 [4.00, 5.00] | 8.00 [8.00, 8.00] | 8.00 [8.00, 8.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | -4.50 [-6.00, -3.00] | -3.50 [-4.00, -3.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] |
| Questions answered from literature | 100% [100, 100] | 100% [100, 100] | 0% [0, 0] | 100% [100, 100] | 50% [0, 100] | 100% [100, 100] | 50% [0, 100] | +0 pts [+0, +0] | -100 pts [-100, -100] | +0 pts [+0, +0] | -50 pts [-100, +0] | +0 pts [+0, +0] | -50 pts [-100, +0] |
| Masked correctness: exact (% of set A questions) | 100% | 100% | 0% | 0% | 100% | 100% | 0% | +0 pts | -100 pts | -100 pts | +0 pts | +0 pts | -100 pts |
| Masked correctness: same category (% of set A questions) | 0% | 0% | 0% | 0% | 0% | 0% | 0% | +0 pts | +0 pts | +0 pts | +0 pts | +0 pts | +0 pts |
| Masked correctness: different category (% of set A questions) | 0% | 0% | 0% | 100% | 0% | 0% | 0% | +0 pts | +0 pts | +100 pts | +0 pts | +0 pts | +0 pts |
| Masked correctness: not comparable (% of set A questions) | 0% | 0% | 0% | 0% | 0% | 0% | 0% | +0 pts | +0 pts | +0 pts | +0 pts | +0 pts | +0 pts |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 0% | 0% | 100% | 0% | 0% | 0% | 100% | +0 pts | +100 pts | +0 pts | +0 pts | +0 pts | +100 pts |
| Factual consistency: consistent (% of set B questions) | 100% | 100% | 0% | 100% | 0% | 100% | 100% | +0 pts | -100 pts | +0 pts | -100 pts | +0 pts | +0 pts |
| Factual consistency: inconsistent (% of set B questions) | 0% | 0% | 0% | 0% | 0% | 0% | 0% | +0 pts | +0 pts | +0 pts | +0 pts | +0 pts | +0 pts |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 0% | 0% | 100% | 0% | 100% | 0% | 0% | +0 pts | +100 pts | +0 pts | +100 pts | +0 pts | +0 pts |
| Retrieval cost per question (search fees, search/rerank LLM; USD) | $0.00000 | $0.00000 | $0.00710 | $0.04987 | $0.03262 | $0.00512 | $0.00511 | +0.00000 [+0.00000, +0.00000] | +0.00710 [+0.00709, +0.00710] | +0.04987 [+0.04276, +0.05698] | +0.03262 [+0.02212, +0.04312] | +0.00512 [+0.00511, +0.00513] | +0.00511 [+0.00508, +0.00513] |
| medsim LLM cost per question (Stages A–C, USD) | $0.00131 | $0.00092 | $0.00073 | $0.00076 | $0.00158 | $0.00252 | $0.00147 | -0.00039 [-0.00041, -0.00037] | -0.00058 [-0.00094, -0.00023] | -0.00055 [-0.00084, -0.00026] | +0.00027 [-0.00007, +0.00061] | +0.00121 [-0.00044, +0.00285] | +0.00016 [+0.00000, +0.00031] |
| Total cost per question (USD) | $0.00131 | $0.00092 | $0.00782 | $0.05063 | $0.03420 | $0.00764 | $0.00658 | -0.00039 [-0.00041, -0.00037] | +0.00651 [+0.00616, +0.00687] | +0.04932 [+0.04192, +0.05672] | +0.03289 [+0.02205, +0.04373] | +0.00633 [+0.00467, +0.00798] | +0.00527 [+0.00513, +0.00540] |
| Wall time per question (s) | 104.1 [43.9, 164.2] | 85.9 [60.1, 111.6] | 50.3 [27.6, 72.9] | 75.4 [64.8, 86.0] | 165.3 [102.5, 228.1] | 197.5 [37.5, 357.4] | 89.2 [53.4, 124.9] | -18.19 [-52.65, +16.28] | -53.78 [-91.31, -16.26] | -28.66 [-99.41, +42.09] | +61.25 [+58.62, +63.87] | +93.39 [-6.32, +193.10] | -14.88 [-39.33, +9.56] |
| Time outside medsim's LLM calls per question (≈ retrieval; s) | 9.19 [8.67, 9.71] | 19.52 [17.43, 21.61] | 7.14 [3.62, 10.66] | 9.65 [8.92, 10.38] | 15.03 [13.39, 16.67] | 6.99 [4.24, 9.73] | 7.85 [7.29, 8.42] | +10.33 [+7.71, +12.95] | -2.05 [-5.04, +0.95] | +0.46 [-0.80, +1.71] | +5.84 [+4.72, +6.96] | -2.20 [-4.42, +0.02] | -1.34 [-2.43, -0.25] |

## Set A only (hidden value; masked correctness)

| Metric | current | improved_1to4 | openrouter_exa_instant | openrouter_google | openrouter_openai | openrouter_parallel_basic | openrouter_perplexity | improved_1to4 − current | openrouter_exa_instant − current | openrouter_google − current | openrouter_openai − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 8.00 | 8.00 | 8.00 | 2.00 | 4.00 | 8.00 | 8.00 | +0.00 | +0.00 | -6.00 | -4.00 | +0.00 | +0.00 |
| Questions answered from literature | 100% | 100% | 0% | 100% | 100% | 100% | 0% | +0 pts | -100 pts | +0 pts | +0 pts | +0 pts | -100 pts |
| Masked correctness: exact (% of set A questions) | 100% | 100% | 0% | 0% | 100% | 100% | 0% | +0 pts | -100 pts | -100 pts | +0 pts | +0 pts | -100 pts |
| Masked correctness: same category (% of set A questions) | 0% | 0% | 0% | 0% | 0% | 0% | 0% | +0 pts | +0 pts | +0 pts | +0 pts | +0 pts | +0 pts |
| Masked correctness: different category (% of set A questions) | 0% | 0% | 0% | 100% | 0% | 0% | 0% | +0 pts | +0 pts | +100 pts | +0 pts | +0 pts | +0 pts |
| Masked correctness: not comparable (% of set A questions) | 0% | 0% | 0% | 0% | 0% | 0% | 0% | +0 pts | +0 pts | +0 pts | +0 pts | +0 pts | +0 pts |
| Masked correctness: no label — not answered, run failed, or not judged (% of set A questions) | 0% | 0% | 100% | 0% | 0% | 0% | 100% | +0 pts | +100 pts | +0 pts | +0 pts | +0 pts | +100 pts |

## Set B only (value never stated; factual consistency)

| Metric | current | improved_1to4 | openrouter_exa_instant | openrouter_google | openrouter_openai | openrouter_parallel_basic | openrouter_perplexity | improved_1to4 − current | openrouter_exa_instant − current | openrouter_google − current | openrouter_openai − current | openrouter_parallel_basic − current | openrouter_perplexity − current |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 8.00 | 8.00 | 8.00 | 5.00 | 5.00 | 8.00 | 8.00 | +0.00 | +0.00 | -3.00 | -3.00 | +0.00 | +0.00 |
| Questions answered from literature | 100% | 100% | 0% | 100% | 0% | 100% | 100% | +0 pts | -100 pts | +0 pts | -100 pts | +0 pts | +0 pts |
| Factual consistency: consistent (% of set B questions) | 100% | 100% | 0% | 100% | 0% | 100% | 100% | +0 pts | -100 pts | +0 pts | -100 pts | +0 pts | +0 pts |
| Factual consistency: inconsistent (% of set B questions) | 0% | 0% | 0% | 0% | 0% | 0% | 0% | +0 pts | +0 pts | +0 pts | +0 pts | +0 pts | +0 pts |
| Factual consistency: no label — not answered, run failed, or not judged (% of set B questions) | 0% | 0% | 100% | 0% | 100% | 0% | 0% | +0 pts | +100 pts | +0 pts | +100 pts | +0 pts | +0 pts |

## Cost

All questions that ran.

| Method | Questions | Retrieval (search fees + search model) | medsim LLM (Stages A–C) | Total | Total per question | Median wall time |
|---|---|---|---|---|---|---|
| current | 2 | $0.0000 | $0.0026 | $0.0026 | $0.00131 | 104.1 s |
| improved_1to4 | 2 | $0.0000 | $0.0018 | $0.0018 | $0.00092 | 85.9 s |
| openrouter_exa_instant | 2 | $0.0142 | $0.0015 | $0.0156 | $0.00782 | 50.3 s |
| openrouter_google | 2 | $0.0997 | $0.0015 | $0.1013 | $0.05063 | 75.4 s |
| openrouter_openai | 2 | $0.0652 | $0.0032 | $0.0684 | $0.03420 | 165.3 s |
| openrouter_parallel_basic | 2 | $0.0102 | $0.0050 | $0.0153 | $0.00764 | 197.5 s |
| openrouter_perplexity | 2 | $0.0102 | $0.0029 | $0.0132 | $0.00658 | 89.2 s |

## By subgroup (set A)

### Variable category

| Group | n | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_google | Masked correctness: exact (% of set A questions) — openrouter_openai | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_google | Masked correctness: different category (% of set A questions) — openrouter_openai | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| anthropometric | 1 | 100% | 100% | 0% | 0% | 100% | 100% | 0% | 0% | 0% | 0% | 100% | 0% | 0% | 0% |

### True value (judge's category)

| Group | n | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_google | Masked correctness: exact (% of set A questions) — openrouter_openai | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_google | Masked correctness: different category (% of set A questions) — openrouter_openai | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| high | 1 | 100% | 100% | – | 0% | 100% | 100% | – | 0% | 0% | – | 100% | 0% | 0% | – |
| unknown | 1 | – | – | 0% | – | – | – | 0% | – | – | 0% | – | – | – | 0% |

### Variable typical of the diagnosis

| Group | n | Masked correctness: exact (% of set A questions) — current | Masked correctness: exact (% of set A questions) — improved_1to4 | Masked correctness: exact (% of set A questions) — openrouter_exa_instant | Masked correctness: exact (% of set A questions) — openrouter_google | Masked correctness: exact (% of set A questions) — openrouter_openai | Masked correctness: exact (% of set A questions) — openrouter_parallel_basic | Masked correctness: exact (% of set A questions) — openrouter_perplexity | Masked correctness: different category (% of set A questions) — current | Masked correctness: different category (% of set A questions) — improved_1to4 | Masked correctness: different category (% of set A questions) — openrouter_exa_instant | Masked correctness: different category (% of set A questions) — openrouter_google | Masked correctness: different category (% of set A questions) — openrouter_openai | Masked correctness: different category (% of set A questions) — openrouter_parallel_basic | Masked correctness: different category (% of set A questions) — openrouter_perplexity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| yes | 1 | 100% | 100% | 0% | 0% | 100% | 100% | 0% | 0% | 0% | 0% | 100% | 0% | 0% | 0% |

## Diagnostics

- **current:** answer paths {'literature': 2}; source article removed for 1 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **improved_1to4:** answer paths {'literature': 2}; source article removed for 0 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_exa_instant:** answer paths {'synthesizer_unanswerable': 2}; source article removed for 0 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_google:** answer paths {'literature': 2}; source article removed for 0 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_openai:** answer paths {'literature': 1, 'synthesizer_unanswerable': 1}; source article removed for 0 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_parallel_basic:** answer paths {'literature': 2}; source article removed for 0 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **openrouter_perplexity:** answer paths {'synthesizer_unanswerable': 1, 'literature': 1}; source article removed for 0 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **Masked correctness:** 0 of 5 voted labels were "not comparable" (reported as their own label).
- **Judge errors (all attempts, all judges):** 0 judgment(s) failed; rerun the judge step to retry them.

## Judge panel agreement

| Metric | Answers | Unanimous | Majority | Tie broken by the main judge | Tie broken by the next judge | Fewer than all votes |
|---|---|---|---|---|---|---|
| masked correctness | 5 | 60% | 20% | 20% | 0% | 0 |
| factual consistency | 5 | 100% | 0% | 0% | 0% | 0 |

- **masked correctness, `google/gemini-3.5-flash-lite` vs `qwen/qwen3.8-flash`:** 3/5 identical labels, Cohen's κ = 0.17.
- **masked correctness, `google/gemini-3.5-flash-lite` vs `openai/gpt-6-luna`:** 3/5 identical labels, Cohen's κ = 0.00.
- **masked correctness, `qwen/qwen3.8-flash` vs `openai/gpt-6-luna`:** 4/5 identical labels, Cohen's κ = 0.00.
- **factual consistency, `google/gemini-3.5-flash-lite` vs `qwen/qwen3.8-flash`:** 5/5 identical labels, Cohen's κ = 1.00.
- **factual consistency, `google/gemini-3.5-flash-lite` vs `openai/gpt-6-luna`:** 5/5 identical labels, Cohen's κ = 1.00.
- **factual consistency, `qwen/qwen3.8-flash` vs `openai/gpt-6-luna`:** 5/5 identical labels, Cohen's κ = 1.00.

## Benchmark spend

| Step | Cost (USD, OpenRouter usage.cost) |
|---|---|
| extract (case facts) | $0.0000 |
| redact + Stage A checks (accepted) | $0.0000 |
| redact + Stage A checks (rejected) | $0.0000 |
| run (all methods; search fees included) | $0.2182 |
| judge: masked correctness (google/gemini-3.5-flash-lite) | $0.0028 |
| judge: masked correctness (openai/gpt-6-luna) | $0.0013 |
| judge: masked correctness (qwen/qwen3.8-flash) | $0.0052 |
| judge: factual consistency (google/gemini-3.5-flash-lite) | $0.0019 |
| judge: factual consistency (openai/gpt-6-luna) | $0.0005 |
| judge: factual consistency (qwen/qwen3.8-flash) | $0.0005 |
| validation: controls (panel) | $0.0000 |
| validation: flipped truth (panel) | $0.0000 |
| **total** | **$0.2305** |

Cross-check: the OpenRouter key's usage counter, read right after each of the 4 benchmark commands, rose by $0.2335. The counter lags behind requests, so this undercounts; per-call usage.cost above is the accounting source.

