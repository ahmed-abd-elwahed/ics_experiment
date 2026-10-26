#!/usr/bin/env bash
# Three repetitions of the four strategies at 4, 8 and 16 questions on dataset v2.
# Each repetition has its own config (only the environment seed differs: 7, 8, 9).
# Runs one after another (LitSense allows one request per second in total).
# Usage: scripts/run_v2_repetitions.sh [rep ...]   (default: 1 2 3)
# A finished record is skipped on a second call. A run that ends with failed case runs
# (exit 1) does not stop the others; fix it afterwards with `python -m experiment.rerun`.
set -uo pipefail
cd "$(dirname "$0")/.."
reps=("$@"); [[ ${#reps[@]} -eq 0 ]] && reps=(1 2 3)
for rep in "${reps[@]}"; do
  for it in 4 8 16; do
    out="records/strategies_272_v2_rep${rep}_${it}it.json"
    if [[ -f "$out" || -f "$out.gz" ]]; then echo "skip $out (exists)"; continue; fi
    echo "== rep $rep, $it questions -> $out"
    .venv/bin/python -m experiment --config "configs/strategies_272_v2_rep${rep}.json" \
      --max-iterations "$it" --output "$out"
    rc=$?
    if [[ $rc -eq 1 ]]; then echo "!! $out has failed case runs; continuing"
    elif [[ $rc -ne 0 ]]; then echo "!! stopped (exit $rc) at $out"; exit "$rc"; fi
  done
done
