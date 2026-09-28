# Environment benchmark

| Metric → | Masked correctness (set A) |  |  |  |  | Factual consistency (set B) |  |  | Masked correctness (set C) |  |  |  |  | Factual consistency (set C) |  |  | Environment cost and time |  |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Environment configuration ↓ / label → | exact | same category | different category | not comparable | no label* | consistent | inconsistent | no label* | exact | same category | different category | not comparable | no label* | consistent | inconsistent | no label* | Total cost (USD) | Average answer time (s) |
| 1. Current (Europe PMC + LitSense, without changes 1–4) | 37.6% | 41.8% | 12.1% | 0.0% | 8.5% | 84.2% | 0.0% | 15.8% | – | – | – | – | – | – | – | – | $0.456 | 86.9 |
| 2. Current with changes 1–4 | 34.8% | 44.7% | 14.9% | 0.0% | 5.7% | 83.8% | 0.4% | 15.8% | – | – | – | – | – | – | – | – | $0.430 | 96.4 |
| 3. OpenRouter search: Exa instant, DeepSeek v4 Flash | 35.5% | 39.0% | 10.6% | 0.0% | 14.9% | 52.6% | 0.0% | 47.4% | – | – | – | – | – | – | – | – | $3.279 | 77.6 |
| 4. OpenRouter search: Parallel basic, DeepSeek v4 Flash | 27.7% | 45.4% | 18.4% | 0.0% | 8.5% | 77.9% | 0.4% | 21.7% | – | – | – | – | – | – | – | – | $2.525 | 86.6 |
| 5. OpenRouter search: Perplexity, DeepSeek v4 Flash | 39.0% | 43.3% | 14.9% | 0.7% | 2.1% | 92.6% | 0.0% | 7.4% | – | – | – | – | – | – | – | – | $2.468 | 77.5 |
| 6. OpenRouter search: Google (native), Gemini 3.1 Flash Lite | 38.3% | 34.8% | 14.2% | 0.7% | 12.1% | 75.0% | 0.0% | 25.0% | – | – | – | – | – | – | – | – | $19.255 | 77.3 |
| 7. OpenRouter search: OpenAI (native), GPT-6-luna | 34.8% | 41.8% | 14.9% | 0.0% | 8.5% | 70.2% | 0.0% | 29.8% | – | – | – | – | – | – | – | – | $10.799 | 79.8 |
| 8. Case information only, no retrieval (DeepSeek v4 Flash 0731) | – | – | – | – | – | – | – | – | 98.5% | 0.0% | 0.0% | 0.0% | 1.5% | 98.5% | 0.0% | 1.5% | $0.026 | 7.5 |

- Questions from the 272 cases in cases/combined_272_whole_chunking.json: set A (141), a value hidden from the case; set B (272), a value the case never states; set C (272), information the case states, written by an LLM (google/gemini-3.5-flash-lite). Configurations 1-7 answered the same sets A and B; configuration 8 answered set C.
- Judge panel: google/gemini-3.5-flash-lite, qwen/qwen3.8-flash, openai/gpt-6-luna. Each answer's label is the majority vote; with no majority, the first (main) judge decides. Set C answers are graded by both metrics. Judging cost $2.55 in total, not included in the costs above.
- * No label: medsim gave no answer (it found no usable literature, or for set C the case did not answer the question), the run failed, or there was no judge verdict; it is not a judge label.
- Total cost: every environment component for all questions of the configuration (medsim Stages A–C, search fees, and the search model's tokens), from OpenRouter's usage.cost. Average answer time: mean wall time per question, all components included.
- Configurations 6 and 7 use the model provider's own (native) search. Their documents are the search model's quotations or summaries of each cited source, not page excerpts as returned by Exa, Parallel, and Perplexity.
- Configuration 8 has retrieval switched off: medsim answers from the case information, or not at all, with deepseek/deepseek-v4-flash-0731 for every stage.
- Masked correctness labels: exact (the answer matches the true value), same category (same low/normal/high category, or the same finding with a minor detail wrong), different category, not comparable.
