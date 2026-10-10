# Environment benchmark (summary)

| Metric → | Masked correctness |  |  |  | Factual consistency |  |  | Environment cost and time |  |
|---|---|---|---|---|---|---|---|---|---|
| Environment configuration ↓ / label → | same category (incl. exact)† | different category | not comparable | no label* | consistent | inconsistent | no label* | Total cost (USD) | Average answer time (s) |
| 1. Gemini 3 Flash knowledge, no search (gemini-3-flash-preview) | 86.5% | 13.5% | 0.0% | 0.0% | 96.7% | 0.0% | 3.3% | $0.660 | 72.8 |
| 2. Current with changes 1–4 (Europe PMC + LitSense) | 82.3% | 17.0% | 0.0% | 0.7% | 97.1% | 0.4% | 2.6% | $0.416 | 94.3 |
| 3. OpenRouter search: Exa instant, DeepSeek v4 Flash | 85.8% | 13.5% | 0.7% | 0.0% | 96.0% | 0.0% | 4.0% | $3.258 | 74.2 |
| 4. OpenRouter search: Parallel basic, DeepSeek v4 Flash | 80.9% | 19.1% | 0.0% | 0.0% | 96.3% | 0.4% | 3.3% | $2.516 | 84.2 |
| 5. OpenRouter search: Perplexity, DeepSeek v4 Flash | 84.4% | 14.9% | 0.7% | 0.0% | 97.4% | 0.0% | 2.6% | $2.470 | 78.8 |
| 6. OpenRouter search: Google (native), Gemini 3.1 Flash Lite | 83.0% | 16.3% | 0.7% | 0.0% | 96.7% | 0.0% | 3.3% | $21.086 | 82.4 |
| 7. OpenRouter search: OpenAI (native), GPT-6-luna | 85.1% | 14.9% | 0.0% | 0.0% | 95.6% | 0.0% | 4.4% | $10.800 | 79.9 |
| 8. Case information only, no retrieval (DeepSeek v4 Flash 0731) | 99.6% | 0.4% | 0.0% | 0.0% | 100.0% | 0.0% | 0.0% | $0.026 | 7.7 |

- Judge panel: google/gemini-3.5-flash-lite, qwen/qwen3.8-flash, openai/gpt-6-luna; each answer's label is the majority vote (with no majority, the first judge decides). Judging cost $3.30 in total, not included in the costs above.
- † Same category (incl. exact): answers at least in the true value's category (exact + same category). With different category, not comparable, and no label it sums to 100%.
- * No label: medsim gave no answer (almost all are questions its query builder refuses), or the run failed; it is not a judge label.
- Total cost: every environment component for all questions of the configuration (medsim Stages A–C, search fees, the search or knowledge model's tokens), from OpenRouter's usage.cost. Average answer time: mean wall time per question, all components included.
- When the documents give no usable basis, or there are none, medsim's synthesizer makes a best guess from the case and diagnosis.
- Configuration 1 has no search: google/gemini-3-flash-preview gets the question, the case information as medsim sees it, and the diagnosis, and gives the value that typically fits. Configurations 6 and 7 use the model provider's own search; their documents are the search model's quotations of the sources it cites. Configuration 8 has retrieval switched off.
