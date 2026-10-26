# ruff: noqa: E501, RUF001  (the prompts are DDx-Experiment's, word for word)
"""INTERMED complexity score for every case of a case dataset, on Gemini 4.

The method is DDx-Experiment's (`case_stats.ipynb`, "Generate Complexity Score"): the same
system prompt and user prompt, word for word, one call per case, seed 42, low reasoning, and the
total taken from the reply's last <score></score> tag. Changes from that notebook: the model
(`google/gemini-4-argon`, synchronous; the account refuses Google batch), at most three tries
for a reply without a readable score (the notebook retried forever), and the full reply and
usage are stored with each score.

Usage:
    python scripts/intermed_scores.py cases/combined_272_whole_chunking_v2.json
        writes cases/combined_272_whole_chunking_v2_intermed.json
Finished cases are kept in <output>.partial.jsonl, so a rerun only calls the LLM for the rest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import httpx

MODEL = "google/gemini-4-argon"
SEED = 42
REASONING_EFFORT = "low"
MAX_TRIES = 3
WORKERS = 16
URL = "https://openrouter.ai/api/v1/chat/completions"
ROOT = Path(__file__).resolve().parents[1]

SYSTEM_PROMPT = """You are an expert clinician trained in using the INTERMED Complexity Assessment Grid (INTERMED), a validated instrument for assessing biopsychosocial case complexity in medical patients. The INTERMED integrates information from biological, psychological, social, and health care domains to quantify the risk of complex care needs and poor outcomes.

The INTERMED consists of 20 variables organized in a 4 × 5 grid:

**Domains (rows):**
- Biological
- Psychological
- Social
- Health care

**Categories (columns):**
- History
- Current state
- Prognosis
- Vulnerabilities
- Care needs (or coordination/complexity of care)

Each of the 20 variables is scored on a scale of 0–3, based on specific clinical anchor points reflecting the level of health risk or care need:

- 0 = No vulnerability or need (no action required)
- 1 = Mild vulnerability or need (watchful waiting or monitoring)
- 2 = Moderate vulnerability or need (action indicated)
- 3 = Severe vulnerability or need (urgent or intensive action required)

The total INTERMED score is the sum of all 20 items (range 0–60). Interpretation:
- 0–20: Low complexity
- 21–60: High complexity (patients often benefit from integrated or case management approaches)

The specific variables in the grid are as follows (standard names based on the original INTERMED method):

**History**
- Biological: Chronicity
- Psychological: Psychiatric history/dysfunctioning
- Social: Residential/job/leisure chronic instability
- Health care: Intensity of previous treatment

**Current state**
- Biological: Severity of illness + Diagnostic dilemma/challenge
- Psychological: Severity of psychiatric symptoms + Resistance to treatment/coping deficits
- Social: Residential instability + Social support deficits
- Health care: Intensity of current treatment + Organization of care

**Prognosis**
- Biological: Complications and life threat
- Psychological: Psychiatric prognosis/mental health threat
- Social: Social vulnerability
- Health care: Expected care complexity

**Vulnerabilities**
- Biological: Restrictions in self-care/biological vulnerabilities
- Psychological: Cognitive/behavioral vulnerabilities
- Social: Social integration vulnerabilities
- Health care: Patient-provider experience vulnerabilities

**Care needs**
- Biological: Therapeutic challenge needs
- Psychological: Mental health care needs
- Social: Social support needs
- Health care: Coordination and appropriateness of care needs

Your task: Given the following case study text, carefully analyze it and apply the INTERMED method and output only the numerical final score.

Steps you must follow:
1. Read the case study thoroughly.
2. For each of the 20 variables, extract relevant information from the text (or note absence if none).
3. Assign a score (0–3) to each variable, providing a brief justification (1–2 sentences) based on the anchor points.
4. Present your scoring in a clear table or structured list, grouped by domain and category.
5. Calculate the total score.
6. At the very end of your response, output only the final total score inside <score></score> tags in this exact format: <score>42</score> (replace with the actual values; do not add any other text inside or around the tags).
"""

USER_PROMPT = """Case study text: {case_text}
    Respond only with your INTERMED score — no additional commentary outside the required structure."""


def api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key and (ROOT / ".env").exists():
        for line in (ROOT / ".env").read_text().splitlines():
            if line.startswith("OPENROUTER_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY is not set")
    return key


def parse_score(text: str) -> int | None:
    """The notebook's rule: the text after the last <score>, without </score>, as a number."""
    if "<score>" not in text:
        return None
    raw = text.split("<score>")[-1].replace("</score>", "").strip()
    return int(raw) if re.fullmatch(r"\d+", raw) and 0 <= int(raw) <= 60 else None


def score_case(client: httpx.Client, key: str, case: dict) -> dict:
    body = {
        "model": MODEL,
        "seed": SEED,
        "reasoning": {"effort": REASONING_EFFORT},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT.format(case_text=case["case_information"])},
        ],
        "usage": {"include": True},
    }
    tries, cost, last = [], 0.0, ""
    for attempt in range(1, MAX_TRIES + 1):
        for http_try in range(5):
            try:
                r = client.post(URL, json=body, headers={"Authorization": f"Bearer {key}"}, timeout=300)
            except httpx.HTTPError as e:
                last = f"{type(e).__name__}: {e}"
                time.sleep(5 * 2 ** http_try)
                continue
            if r.status_code in (429, 500, 502, 503, 504):
                last = f"HTTP {r.status_code}: {r.text[:200]}"
                time.sleep(5 * 2 ** http_try)
                continue
            break
        else:
            tries.append({"attempt": attempt, "error": last})
            continue
        if r.status_code >= 400:
            raise RuntimeError(f"{case['case_id']}: HTTP {r.status_code}: {r.text[:300]}")
        data = r.json()
        usage = data.get("usage") or {}
        cost += usage.get("cost") or 0.0
        text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        score = parse_score(text)
        if score is not None:
            return {"case_id": case["case_id"], "intermed_score": score, "attempts": attempt,
                    "cost": cost, "usage": usage, "response": text}
        tries.append({"attempt": attempt, "error": "no readable <score>", "response": text[-500:]})
    return {"case_id": case["case_id"], "intermed_score": None, "attempts": MAX_TRIES,
            "cost": cost, "failed_tries": tries}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cases_file", type=Path)
    parser.add_argument("--limit", type=int, help="score only the first N cases (a pilot)")
    args = parser.parse_args()
    cases = json.loads(args.cases_file.read_text())[: args.limit]
    out_path = args.cases_file.with_name(args.cases_file.stem + "_intermed.json")
    partial = out_path.with_suffix(".partial.jsonl")

    done = {}
    if partial.exists():
        for line in partial.read_text().splitlines():
            rec = json.loads(line)
            if rec["intermed_score"] is not None:
                done[rec["case_id"]] = rec
    todo = [c for c in cases if c["case_id"] not in done]
    print(f"{len(done)} cases already scored, {len(todo)} to score with {MODEL}")

    key, lock = api_key(), threading.Lock()
    with httpx.Client() as client, ThreadPoolExecutor(WORKERS) as ex, partial.open("a") as f:
        for i, rec in enumerate(ex.map(lambda c: score_case(client, key, c), todo), 1):
            with lock:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()
            if rec["intermed_score"] is not None:
                done[rec["case_id"]] = rec
            if i % 20 == 0 or i == len(todo):
                print(f"  {i}/{len(todo)} done")

    failed = [c["case_id"] for c in cases if c["case_id"] not in done]
    records = [done[c["case_id"]] for c in cases if c["case_id"] in done]
    scores = [r["intermed_score"] for r in records]
    result = {
        "metadata": {
            "cases_file": str(args.cases_file),
            "cases_file_sha256": hashlib.sha256(args.cases_file.read_bytes()).hexdigest(),
            "created_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "method": "INTERMED Complexity Assessment Grid, scored by an LLM; prompts from "
                      "DDx-Experiment/case_stats.ipynb",
            "model": MODEL, "seed": SEED, "reasoning_effort": REASONING_EFFORT,
            "max_tries": MAX_TRIES,
            "system_prompt": SYSTEM_PROMPT, "user_prompt": USER_PROMPT,
            "n_cases": len(cases), "n_scored": len(records), "failed_case_ids": failed,
            "score_mean": round(sum(scores) / len(scores), 2) if scores else None,
            "n_high_complexity_21_plus": sum(s >= 21 for s in scores),
            "total_cost_usd": round(sum(r["cost"] for r in records), 4),
        },
        "scores": [{"case_id": r["case_id"], "intermed_score": r["intermed_score"]} for r in records],
        "responses": records,
    }
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(f"Saved {out_path}: {len(records)}/{len(cases)} scored, mean {result['metadata']['score_mean']}, "
          f"cost ${result['metadata']['total_cost_usd']}" + (f"; FAILED {failed}" if failed else ""))


if __name__ == "__main__":
    main()
