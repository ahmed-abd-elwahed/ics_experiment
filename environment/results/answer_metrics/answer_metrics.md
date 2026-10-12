# Answer metrics: old and new, all configurations

Mean ± SD over the runs the whole panel judged (n = number of runs).

## Three judges

Panel: anthropic/claude-haiku-5.5, z-ai/glm-5.3-flash, openai/gpt-6-luna

| Configuration | Masked correctness: same category (incl. exact), % | Masked correctness: exact, % | Factual consistency: consistent, % | Zlog z-score: mean |z| (capped at 3) | Zlog z-score: satisfactory (|z| ≤ 2), % | Faithfulness: supported, % | Case alignment: aligned, % | Case alignment: contradicted, % |
|---|---|---|---|---|---|---|---|---|
| Gemini 3 Flash knowledge, no search | 84.4 ± 1.5% (n=10) | 45.6 ± 1.4% (n=10) | 97.3 ± 1.5% (n=10) | 1.28 ± 0.04 (n=10) | 74.6 ± 2.0% (n=10) | – | 18.6 ± 0.9% (n=9) | 3.3 ± 0.5% (n=9) |
| Europe PMC + LitSense, without changes 1–4 | 86.2 ± 1.5% (n=10) | 45.4 ± 2.5% (n=10) | 96.8 ± 1.2% (n=10) | 1.26 ± 0.05 (n=10) | 73.0 ± 1.8% (n=10) | 22.7 ± 1.3% (n=9) | 20.0 ± 1.1% (n=9) | 1.7 ± 0.6% (n=9) |
| Europe PMC + LitSense, with changes 1–4 | 84.9 ± 1.3% (n=10) | 41.6 ± 2.1% (n=10) | 96.8 ± 1.1% (n=10) | 1.29 ± 0.05 (n=10) | 73.1 ± 2.8% (n=10) | 35.1 ± 2.5% (n=9) | 20.1 ± 0.6% (n=9) | 1.5 ± 0.5% (n=9) |
| OpenRouter search: Exa instant | 85.0 ± 1.5% (n=10) | 45.9 ± 3.0% (n=10) | 97.2 ± 0.9% (n=10) | 1.25 ± 0.06 (n=10) | 75.4 ± 2.7% (n=10) | 21.0 ± 1.3% (n=9) | 20.2 ± 0.8% (n=9) | 1.4 ± 0.6% (n=9) |
| OpenRouter search: Parallel basic | 84.0 ± 2.2% (n=10) | 43.4 ± 2.6% (n=10) | 96.7 ± 1.0% (n=10) | 1.29 ± 0.06 (n=10) | 71.9 ± 2.8% (n=10) | 25.4 ± 1.8% (n=9) | 20.3 ± 1.0% (n=9) | 1.3 ± 0.7% (n=9) |
| OpenRouter search: Perplexity | 83.2 ± 2.3% (n=10) | 43.9 ± 2.7% (n=10) | 97.1 ± 0.6% (n=10) | 1.32 ± 0.04 (n=10) | 72.1 ± 2.1% (n=10) | 59.2 ± 2.4% (n=9) | 18.2 ± 0.8% (n=9) | 2.7 ± 0.7% (n=9) |
| Native Google search (one run) | 82.3% | 44.7% | 96.7% | 1.25 | 71.4% | 23.5% | 19.1% | 1.8% |
| Native OpenAI search (one run) | 84.4% | 44.0% | 95.6% | 1.28 | 72.9% | 38.3% | 19.5% | 1.1% |
| Case study only, no retrieval (set C) | 99.2 ± 0.4% (n=10) | 98.8 ± 0.4% (n=10) | 99.7 ± 0.3% (n=10) | 0.04 ± 0.02 (n=10) | 98.7 ± 0.6% (n=10) | – | 97.7 ± 0.8% (n=9) | 0.3 ± 0.3% (n=9) |

## With the Jev decision model added

Panel: anthropic/claude-haiku-5.5, z-ai/glm-5.3-flash, openai/gpt-6-luna, typesafe/jev-1.13

| Configuration | Masked correctness: same category (incl. exact), % | Masked correctness: exact, % | Factual consistency: consistent, % | Zlog z-score: mean |z| (capped at 3) | Zlog z-score: satisfactory (|z| ≤ 2), % | Faithfulness: supported, % | Case alignment: aligned, % | Case alignment: contradicted, % |
|---|---|---|---|---|---|---|---|---|
| Gemini 3 Flash knowledge, no search | 83.8 ± 1.6% (n=10) | 43.7 ± 2.1% (n=10) | 97.2 ± 1.5% (n=10) | 1.28 ± 0.04 (n=10) | 74.6 ± 2.0% (n=10) | – | 19.1 ± 1.1% (n=9) | 3.1 ± 0.7% (n=9) |
| Europe PMC + LitSense, without changes 1–4 | 86.0 ± 1.4% (n=10) | 44.2 ± 2.8% (n=10) | 96.8 ± 1.2% (n=10) | 1.26 ± 0.05 (n=10) | 73.0 ± 1.8% (n=10) | 21.9 ± 1.3% (n=9) | 20.8 ± 1.2% (n=9) | 1.4 ± 0.7% (n=9) |
| Europe PMC + LitSense, with changes 1–4 | 84.7 ± 1.5% (n=10) | 40.3 ± 2.5% (n=10) | 96.8 ± 1.1% (n=10) | 1.29 ± 0.05 (n=10) | 73.1 ± 2.8% (n=10) | 35.0 ± 1.9% (n=9) | 21.0 ± 0.6% (n=9) | 1.1 ± 0.3% (n=9) |
| OpenRouter search: Exa instant | 84.1 ± 1.8% (n=10) | 44.8 ± 3.2% (n=10) | 97.1 ± 0.9% (n=10) | 1.25 ± 0.06 (n=10) | 75.4 ± 2.7% (n=10) | 20.3 ± 1.2% (n=9) | 21.3 ± 1.0% (n=9) | 1.1 ± 0.7% (n=9) |
| OpenRouter search: Parallel basic | 84.5 ± 2.3% (n=10) | 41.9 ± 2.6% (n=10) | 96.7 ± 1.0% (n=10) | 1.29 ± 0.06 (n=10) | 71.9 ± 2.8% (n=10) | 24.1 ± 1.7% (n=9) | 21.0 ± 0.7% (n=9) | 1.2 ± 0.7% (n=9) |
| OpenRouter search: Perplexity | 82.9 ± 2.4% (n=10) | 42.8 ± 2.9% (n=10) | 97.1 ± 0.7% (n=10) | 1.32 ± 0.04 (n=10) | 72.1 ± 2.1% (n=10) | 59.5 ± 2.3% (n=9) | 19.2 ± 0.7% (n=9) | 2.4 ± 0.6% (n=9) |
| Native Google search (one run) | 82.3% | 43.3% | 96.7% | 1.25 | 71.4% | 20.6% | 20.2% | 1.8% |
| Native OpenAI search (one run) | 83.7% | 41.8% | 95.6% | 1.28 | 72.9% | 37.8% | 20.2% | 1.1% |
| Case study only, no retrieval (set C) | 99.2 ± 0.4% (n=10) | 98.8 ± 0.5% (n=10) | 99.4 ± 0.4% (n=10) | 0.04 ± 0.02 (n=10) | 98.7 ± 0.6% (n=10) | – | 97.1 ± 0.9% (n=9) | 0.7 ± 0.2% (n=9) |
