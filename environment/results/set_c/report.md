# Retrieval benchmark report

- Workspace: `environment/results/set_c`
- Judge panel: `google/gemini-3.5-flash-lite`, `qwen/qwen3.8-flash`, `openai/gpt-6-luna`. Each answer's label is the panel's majority vote; with no majority, the first (main) judge's label decides.
- medsim models: `deepseek/deepseek-v4-flash-0731`
- `case_information`: no retrieval: medsim (deepseek/deepseek-v4-flash-0731 for every stage) answers from the case information, or does not answer (set C)

## Question sets

- Cases extracted: 0; measured values found: 0; eligible as hidden values: 0.
- Set A (hidden value): 0 questions accepted; rejected 0 (none).
- Set B (value never stated): 0 questions accepted; rejected 0 (none).
- Set C (information the case states): 272 questions accepted; rejected 0 (none).
- Every question is scored under every method: each label's percentage is out of all questions in its set. Questions without a successful run (counted as no label): case_information: 0.

## All questions (sets C)

| Metric | case_information |
|---|---|
| Documents returned per question | 0.00 [0.00, 0.00] |
| Questions answered from literature | 0% [0, 0] |
| Masked correctness: exact (% of set C questions) | 99% [97, 100] |
| Masked correctness: same category (% of set C questions) | 0% [0, 0] |
| Masked correctness: different category (% of set C questions) | 0% [0, 0] |
| Masked correctness: not comparable (% of set C questions) | 0% [0, 0] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set C questions) | 1% [0, 3] |
| Factual consistency: consistent (% of set C questions) | 99% [97, 100] |
| Factual consistency: inconsistent (% of set C questions) | 0% [0, 0] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set C questions) | 1% [0, 3] |
| Retrieval cost per question (search fees, search/rerank LLM; USD) | $0.00000 |
| medsim LLM cost per question (Stages A–C, USD) | $0.00009 |
| Total cost per question (USD) | $0.00009 |
| Wall time per question (s) | 7.5 [6.8, 8.4] |
| Time outside medsim's LLM calls per question (≈ retrieval; s) | 0.00 [0.00, 0.00] |

## Set C only (information the case states; both metrics)

| Metric | case_information |
|---|---|
| Documents returned per question | 0.00 [0.00, 0.00] |
| Questions answered from literature | 0% [0, 0] |
| Masked correctness: exact (% of set C questions) | 99% [97, 100] |
| Masked correctness: same category (% of set C questions) | 0% [0, 0] |
| Masked correctness: different category (% of set C questions) | 0% [0, 0] |
| Masked correctness: not comparable (% of set C questions) | 0% [0, 0] |
| Masked correctness: no label — not answered, run failed, or not judged (% of set C questions) | 1% [0, 3] |
| Factual consistency: consistent (% of set C questions) | 99% [97, 100] |
| Factual consistency: inconsistent (% of set C questions) | 0% [0, 0] |
| Factual consistency: no label — not answered, run failed, or not judged (% of set C questions) | 1% [0, 3] |

## Cost

All questions that ran.

| Method | Questions | Retrieval (search fees + search model) | medsim LLM (Stages A–C) | Total | Total per question | Median wall time |
|---|---|---|---|---|---|---|
| case_information | 272 | $0.0000 | $0.0257 | $0.0257 | $0.00009 | 5.6 s |

## By subgroup (set A)

### Variable category

| Group | n | Masked correctness: exact (% of set A questions) — case_information | Masked correctness: different category (% of set A questions) — case_information |
|---|---|---|---|

### True value (judge's category)

| Group | n | Masked correctness: exact (% of set A questions) — case_information | Masked correctness: different category (% of set A questions) — case_information |
|---|---|---|---|

### Variable typical of the diagnosis

| Group | n | Masked correctness: exact (% of set A questions) — case_information | Masked correctness: different category (% of set A questions) — case_information |
|---|---|---|---|

## Diagnostics

- **case_information:** answer paths {'case_study': 268, 'no_documents': 4}; source article removed for 0 question(s); 0 answer(s) without any judge's verdict; 0 answer(s) voted on by fewer than all 3 judges.
- **Masked correctness:** 0 of 0 voted labels were "not comparable" (reported as their own label).
- **Judge errors (all attempts, all judges):** 0 judgment(s) failed; rerun the judge step to retry them.

## Judge panel agreement

| Metric | Answers | Unanimous | Majority | Tie broken by the main judge | Tie broken by the next judge | Fewer than all votes |
|---|---|---|---|---|---|---|
| masked correctness | 268 | 100% | 0% | 0% | 0% | 0 |
| factual consistency | 268 | 100% | 0% | 0% | 0% | 0 |

- **masked correctness, `google/gemini-3.5-flash-lite` vs `qwen/qwen3.8-flash`:** 268/268 identical labels, Cohen's κ = 1.00.
- **masked correctness, `google/gemini-3.5-flash-lite` vs `openai/gpt-6-luna`:** 268/268 identical labels, Cohen's κ = 1.00.
- **masked correctness, `qwen/qwen3.8-flash` vs `openai/gpt-6-luna`:** 268/268 identical labels, Cohen's κ = 1.00.
- **factual consistency, `google/gemini-3.5-flash-lite` vs `qwen/qwen3.8-flash`:** 268/268 identical labels, Cohen's κ = 1.00.
- **factual consistency, `google/gemini-3.5-flash-lite` vs `openai/gpt-6-luna`:** 268/268 identical labels, Cohen's κ = 1.00.
- **factual consistency, `qwen/qwen3.8-flash` vs `openai/gpt-6-luna`:** 268/268 identical labels, Cohen's κ = 1.00.

## Benchmark spend

| Step | Cost (USD, OpenRouter usage.cost) |
|---|---|
| extract (case facts) | $0.0000 |
| redact + Stage A checks (accepted) | $0.1383 |
| redact + Stage A checks (rejected) | $0.0000 |
| run (all methods; search fees included) | $0.0257 |
| judge: masked correctness (google/gemini-3.5-flash-lite) | $0.1300 |
| judge: masked correctness (openai/gpt-6-luna) | $0.0398 |
| judge: masked correctness (qwen/qwen3.8-flash) | $0.0697 |
| judge: factual consistency (openai/gpt-6-luna) | $0.0295 |
| judge: factual consistency (google/gemini-3.5-flash-lite) | $0.1071 |
| judge: factual consistency (qwen/qwen3.8-flash) | $0.0424 |
| validation: controls (panel) | $0.0000 |
| validation: flipped truth (panel) | $0.0000 |
| **total** | **$0.5823** |

Cross-check: the OpenRouter key's usage counter, read right after each of the 3 benchmark commands, rose by $2.0996. The counter lags behind requests, so this undercounts; per-call usage.cost above is the accounting source.

