# Environment benchmark: repeated runs

| Metric → |  | Masked correctness |  |  |  | Factual consistency |  |  | Environment cost and time |  |
|---|---|---|---|---|---|---|---|---|---|---|
| Environment configuration ↓ / label → | Runs | same category (incl. exact)† | different category | not comparable | no label* | consistent | inconsistent | no label* | Total cost per run (USD)‡ | Average answer time (s) |
| 1. Gemini 3 Flash knowledge, no search (gemini-3-flash-preview) | 10 | 84.4 ± 1.9% | 13.8 ± 1.1% | 1.1 ± 1.0% | 0.7 ± 1.5% | 97.3 ± 1.5% | 0.1 ± 0.2% | 2.6 ± 1.5% | $1.067 ± 0.117 | 70.3 ± 7.6 |
| 2. Current without changes 1–4 (Europe PMC + LitSense) | 10 | 86.0 ± 1.6% | 12.8 ± 1.6% | 0.9 ± 0.9% | 0.4 ± 0.5% | 97.0 ± 1.2% | 0.0 ± 0.1% | 3.0 ± 1.2% | $0.973 ± 0.131 | 122.7 ± 13.3 |
| 3. Current with changes 1–4 (Europe PMC + LitSense) | 10 | 85.0 ± 1.6% | 14.0 ± 1.5% | 0.7 ± 0.7% | 0.4 ± 0.4% | 97.1 ± 1.0% | 0.4 ± 0.3% | 2.5 ± 0.8% | $1.032 ± 0.176 | 106.8 ± 5.1 |
| 4. OpenRouter search: Exa instant, DeepSeek v4 Flash | 10 | 85.8 ± 2.0% | 13.2 ± 2.1% | 0.6 ± 0.4% | 0.4 ± 0.5% | 97.2 ± 0.9% | 0.1 ± 0.3% | 2.6 ± 0.9% | $3.802 ± 0.172 | 78.9 ± 10.9 |
| 5. OpenRouter search: Parallel basic, DeepSeek v4 Flash | 10 | 83.3 ± 2.4% | 15.2 ± 2.5% | 1.1 ± 1.0% | 0.4 ± 0.4% | 97.2 ± 1.0% | 0.2 ± 0.3% | 2.6 ± 0.8% | $3.062 ± 0.138 | 83.8 ± 5.5 |
| 6. OpenRouter search: Perplexity, DeepSeek v4 Flash | 10 | 83.5 ± 2.2% | 15.5 ± 2.3% | 0.8 ± 0.5% | 0.3 ± 0.5% | 97.5 ± 0.7% | 0.1 ± 0.2% | 2.4 ± 0.7% | $3.220 ± 0.147 | 93.4 ± 8.3 |
| 7. OpenRouter search: Google (native), Gemini 3.1 Flash Lite | 1 | 83.0% | 16.3% | 0.7% | 0.0% | 96.7% | 0.0% | 3.3% | $21.086 | 82.4 |
| 8. OpenRouter search: OpenAI (native), GPT-6-luna | 1 | 85.1% | 14.9% | 0.0% | 0.0% | 95.6% | 0.0% | 4.4% | $10.800 | 79.9 |
| 9. Case information only, no retrieval (DeepSeek v4 Flash 0731) | 10 | 99.2 ± 0.4% | 0.4 ± 0.2% | 0.3 ± 0.3% | 0.1 ± 0.2% | 99.7 ± 0.3% | 0.3 ± 0.2% | 0.1 ± 0.2% | $0.053 ± 0.005 | 7.8 ± 0.8 |

- Every run answers the same questions; runs 2 and later search anew (no cached search results). The standard deviation is the sample standard deviation (n − 1) across runs.
- Configurations 7 and 8 (native Google and OpenAI search) were run once, so they have no standard deviation, and their cost is run 1's, at the earlier (lower) DeepSeek price.
- Judge panel: google/gemini-3.5-flash-lite, qwen/qwen3.8-flash, openai/gpt-6-luna; each answer's label is the majority vote (with no majority, the first judge decides).
- † Same category (incl. exact): answers at least in the true value's category (exact + same category). With different category, not comparable, and no label it sums to 100%.
- * No label: medsim gave no answer (almost all are questions its query builder refuses), or the run failed; it is not a judge label.
- Total cost per run: every environment component for all questions of the configuration (medsim Stages A–C, search fees, the search or knowledge model's tokens), from OpenRouter's usage.cost; judging is not included. Average answer time: mean wall time per question.
- ‡ Cost is the mean ± SD over runs 2 and later only: after run 1 (2026-09-29) OpenRouter raised deepseek/deepseek-v4-flash-0731's output price from $0.32 to $1.28 per million tokens, so run 1's cost is at another price level. Run 1 cost: 1: $0.66; 2: $0.44; 3: $0.42; 4: $3.26; 5: $2.52; 6: $2.47; 9: $0.03 (by row number). Percentages and time use every run.
- Run 1 reached the best-guess fallback through a replay of its declined answers on the same documents; in runs 2 and later it is built into medsim.
- 12 of the judge calls in runs 2 and later failed on every attempt (qwen/qwen3.8-flash rate limits); those answers were voted on by the other two judges.
