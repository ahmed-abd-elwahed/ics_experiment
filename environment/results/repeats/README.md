# Repeated runs (2026-10-02 to 2026-10-03)

The benchmark run ten times on the same questions, to measure run-to-run spread. The result:
[repeat_summary.pdf](repeat_summary.pdf) (also [.md](repeat_summary.md), [.html](repeat_summary.html),
and [.json](repeat_summary.json) with every run's values), built by
[../scripts/make_repeat_summary.py](../scripts/make_repeat_summary.py) (no API calls).

## What was repeated

- **Configurations, sets A and B (141 + 272 questions):** `gemini_knowledge`, `current`,
  `improved_1to4`, `openrouter_exa_instant`, `openrouter_parallel_basic`,
  `openrouter_perplexity`.
- **Set C (272 questions):** `case_information`.
- Not repeated: `openrouter_google` and `openrouter_openai` (native search); the table shows their
  single run.
- **Runs:** run 1 is the original evaluation (`../retriever_comparison/`, `../set_c/`); runs 2–10
  are here. Every run answers exactly the same questions (copied from run 1's workspaces). Runs
  2–10 searched anew (no cached search results), with medsim's current behaviour: the best-guess
  fallback (also when no documents are found) and the retry of skipped native searches.

## Layout

| Path | Contents |
|---|---|
| `index.json` | which workspaces hold runs 1–10, the configurations, and the history of repeat commands |
| `run_NN/sets_ab/` | one workspace per run: questions (`items.jsonl`), runs (`runs/<config>.jsonl`), judgments (`judge/`), report (`report.md`, `report.json`), manifest, logs |
| `run_NN/set_c/` | the same for set C |
| `logs/`, `manifest.json` | the `repeat` command's own log and parameters |
| `repeat_summary.*` | the mean ± SD table |

Every run record keeps the answer, the documents, and every LLM call with its cost and latency;
every judge's verdict is stored. Failed attempts stay in the files (a later successful record
supersedes them).

## Result (mean ± SD over 10 runs)

Masked correctness (set A) and factual consistency (set B) are within about 3 points of each
other for all six repeated configurations; their run-to-run SD is 1–2.5 points, as large as most
differences between them. Same category (incl. exact) ranges from 83.3 ± 2.4% (Parallel basic)
to 86.0 ± 1.6% (current without changes 1–4); consistent from 97.0 ± 1.2% to 97.5 ± 0.7%. Set C
stays at 99.2 ± 0.4% (same category) and 99.7 ± 0.3% (consistent).

## How it ran, and cost

```bash
python -m bench --out environment/results/repeats --workers 64 repeat --runs 2-10 --configs gemini_knowledge,current,improved_1to4,openrouter_exa_instant,openrouter_parallel_basic,openrouter_perplexity --set-c-configs case_information
# per workspace (runs 2-10, sets_ab and set_c):
python -m bench --out environment/results/repeats/run_NN/sets_ab --workers 32 judge
python -m bench --out environment/results/repeats/run_NN/sets_ab report --baseline current --configs gemini_knowledge,current,improved_1to4,openrouter_exa_instant,openrouter_parallel_basic,openrouter_perplexity
python -m bench --out environment/results/repeats/run_NN/set_c judge
python -m bench --out environment/results/repeats/run_NN/set_c report --baseline case_information
PYTHONPATH=environment python environment/results/scripts/make_repeat_summary.py
```

- **Cost: $146.17** on the OpenRouter key: runs $119.33, a retry of 198 failed questions $0.82,
  judging $26.02. The estimate was about $103: OpenRouter raised
  `deepseek/deepseek-v4-flash-0731`'s output price from $0.32 to $1.28 per million tokens after
  run 1, so medsim's own LLM stages cost about 2.4 times as much per run (search fees were as
  estimated). The table's cost column therefore uses runs 2–10 only; run 1's costs are in its
  footnote.
- **First attempt:** the account was out of credit (HTTP 402); the 334 refused calls were
  recorded as errors in `run_02` and rerun once credit was added (the `repeat` step now stops
  cleanly on HTTP 402 instead).
- **Failures:** 198 of 24,750 answers failed on the first pass (DeepSeek replies cut off at their
  doubled token budget, or empty); all succeeded on the retry.
- **Judging:** `qwen/qwen3.8-flash` was heavily rate-limited (HTTP 429), so judging ran in several
  passes; 12 of 80,355 judge calls still failed, and those answers were voted on by the other
  two judges.
