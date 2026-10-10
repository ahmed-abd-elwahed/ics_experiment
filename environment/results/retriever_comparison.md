# Environment benchmark

| Metric → | Masked correctness (set A) |  |  |  |  | Factual consistency (set B) |  |  | Masked correctness (set C) |  |  |  |  | Factual consistency (set C) |  |  | Environment cost and time |  |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Environment configuration ↓ / label → | exact | same category (incl. exact)† | different category | not comparable | no label* | consistent | inconsistent | no label* | exact | same category (incl. exact)† | different category | not comparable | no label* | consistent | inconsistent | no label* | Total cost (USD) | Average answer time (s) |
| 1. Current (Europe PMC + LitSense, without changes 1–4) | 42.6% | 87.2% | 12.8% | 0.0% | 0.0% | 95.2% | 0.0% | 4.8% | – | – | – | – | – | – | – | – | $0.443 | 86.1 |
| 2. Current with changes 1–4 | 36.9% | 82.3% | 17.0% | 0.0% | 0.7% | 97.1% | 0.4% | 2.6% | – | – | – | – | – | – | – | – | $0.416 | 94.3 |
| 3. OpenRouter search: Exa instant, DeepSeek v4 Flash | 42.6% | 85.8% | 13.5% | 0.7% | 0.0% | 96.0% | 0.0% | 4.0% | – | – | – | – | – | – | – | – | $3.258 | 74.2 |
| 4. OpenRouter search: Parallel basic, DeepSeek v4 Flash | 33.3% | 80.9% | 19.1% | 0.0% | 0.0% | 96.3% | 0.4% | 3.3% | – | – | – | – | – | – | – | – | $2.516 | 84.2 |
| 5. OpenRouter search: Perplexity, DeepSeek v4 Flash | 39.0% | 84.4% | 14.9% | 0.7% | 0.0% | 97.4% | 0.0% | 2.6% | – | – | – | – | – | – | – | – | $2.470 | 78.8 |
| 6. OpenRouter search: Google (native), Gemini 3.1 Flash Lite | 41.1% | 83.0% | 16.3% | 0.7% | 0.0% | 96.7% | 0.0% | 3.3% | – | – | – | – | – | – | – | – | $21.086 | 82.4 |
| 7. OpenRouter search: OpenAI (native), GPT-6-luna | 41.8% | 85.1% | 14.9% | 0.0% | 0.0% | 95.6% | 0.0% | 4.4% | – | – | – | – | – | – | – | – | $10.800 | 79.9 |
| 8. Case information only, no retrieval (DeepSeek v4 Flash 0731) | – | – | – | – | – | – | – | – | 98.9% | 99.6% | 0.4% | 0.0% | 0.0% | 100.0% | 0.0% | 0.0% | $0.026 | 7.7 |
| 9. Gemini 3 Flash knowledge, no search (gemini-3-flash-preview) | 43.3% | 86.5% | 13.5% | 0.0% | 0.0% | 96.7% | 0.0% | 3.3% | – | – | – | – | – | – | – | – | $0.660 | 72.8 |

- Questions from the 272 cases in cases/combined_272_whole_chunking.json: set A (141), a value hidden from the case; set B (272), a value the case never states; set C (272), information the case states, written by an LLM (google/gemini-3.5-flash-lite). Configurations 1-7 and 9 answered the same sets A and B; configuration 8 answered set C.
- Judge panel: google/gemini-3.5-flash-lite, qwen/qwen3.8-flash, openai/gpt-6-luna. Each answer's label is the majority vote; with no majority, the first (main) judge decides. Set C answers are graded by both metrics. Judging cost $3.30 in total, not included in the costs above.
- * No label: medsim gave no answer (it found no usable literature, or for set C the case did not answer the question), the run failed, or there was no judge verdict; it is not a judge label.
- Total cost: every environment component for all questions of the configuration (medsim Stages A–C, search fees, and the search model's tokens), from OpenRouter's usage.cost. Average answer time: mean wall time per question, all components included.
- Configurations 6 and 7 use the model provider's own (native) search. Their documents are the search model's quotations or summaries of each cited source, not page excerpts as returned by Exa, Parallel, and Perplexity.
- Configuration 8 has retrieval switched off: medsim answers from the case information, or not at all, with deepseek/deepseek-v4-flash-0731 for every stage.
- Configuration 9 replaces the search with google/gemini-3-flash-preview, given the question, the case information as medsim sees it, and the diagnosis, and asked for the value that typically fits; its answer is the one document medsim's stages use.
- Since 2026-09-29, when the documents give no usable basis, medsim's synthesizer makes a best guess from the case and diagnosis instead of declining. The answers configurations 1-7 had declined were replayed with it on the same documents (no new search).
- Masked correctness labels: exact (the answer matches the true value), same category (same low/normal/high category, or the same finding with a minor detail wrong), different category, not comparable.
- † Same category (incl. exact) = exact + same category: the share of answers at least in the true value's category. Exact is a part of it: same category, different category, not comparable, and no label sum to 100%; same category alone is this column minus exact.
