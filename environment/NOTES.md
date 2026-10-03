# NOTES

Assumptions, verification record, and open items for `medsim`. Verification date: 2026-09-15.

## Decisions confirmed with the project owner

| Topic | Decision |
|---|---|
| Ground-truth diagnosis | Visible to all stages; Stage A and C prompts mark it CONFIDENTIAL and forbid stating or hinting at it. Diagnosis questions return `query_scope="withheld"` → `unanswerable`. |
| Europe PMC verification | The official docs pages return HTTP 403 to automated fetches. Accepted: parameters verified by live requests whose response echoes them back (below). |
| Repeat detection / multi-part queries | Rule-based only (`medsim/rules.py`), no extra LLM call. |
| Example case | Supplied by the project owner; `cases/example_case.json` is pending. Tests use a synthetic case in `tests/fixtures/test_case.json`. |

## Known leak (by design of the output schema)

Stage B fuses the diagnosis into the literature query, and `literature_search_result.query`,
`retriever_parameters.literature_query`, and retrieved documents can therefore reveal the
diagnosis. **Show a diagnostic agent only `output_answer`**; the full `EnvironmentResponse` is for
evaluators.

## Endpoint and parameter verification

### OpenRouter

| Item | How verified | Source |
|---|---|---|
| `GET https://openrouter.ai/api/v1/models` → `{"data":[{"id", "supported_parameters", ...}]}` | Live request | — |
| Model `deepseek/deepseek-v4-flash-0731` exists; supports `response_format`, `structured_outputs`, `seed`, `temperature`, `max_tokens` | Live request (`supported_parameters`) | — |
| Model `deepseek/deepseek-v4.1-flash:batch` (the default since 2026-10-04) exists with the same parameters; `/chat/completions` rejects it (404 "cannot be used with the chat/completions endpoint"), `POST /batches` accepts it (202, `status: "validating"`) | Live requests, 2026-10-04 | — |
| `POST /api/v1/chat/completions`, `Authorization: Bearer`, `usage.prompt_tokens/completion_tokens/total_tokens`, integer `seed` | Docs | [API overview](https://openrouter.ai/docs/api-reference/overview) |
| Attribution headers: `HTTP-Referer`, `X-OpenRouter-Title` (also accepts `X-Title`) | Docs. The spec named `X-Title`; both are sent. | [API overview](https://openrouter.ai/docs/api-reference/overview) |
| `response_format: {"type":"json_schema","json_schema":{"name","strict","schema"}}`; `provider.require_parameters: true` | Docs | [Structured outputs](https://openrouter.ai/docs/features/structured-outputs) |

### LitSense 2.0

| Item | How verified | Source |
|---|---|---|
| `GET https://www.ncbi.nlm.nih.gov/research/litsense2-api/api/sentences/?query=…&rerank=true` | Paper + site tutorial + live request | [LitSense 2.0, NAR 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12230651/), [site](https://www.ncbi.nlm.nih.gov/research/litsense2/) |
| `GET …/api/passages/?query=…&rerank=true` | Same | Same |
| Response: JSON list of `{text, score, pmid, pmcid, section, annotations}`, max 100 items | Live request; "top 100 results" in site tutorial | Same |
| Usage limit: "one request per user per second" | Site API tutorial text (in the site's JS bundle) | [site](https://www.ncbi.nlm.nih.gov/research/litsense2/) |
| No match → **HTTP 404** with `{"detail": "No passages share at least 10% of words…"}` | Live request (not documented) | — |

### Europe PMC

| Item | How verified | Source |
|---|---|---|
| `GET https://www.ebi.ac.uk/europepmc/webservices/rest/search` | Live request | [RESTful Web Service](https://europepmc.org/RestfulWebService) (403 to automated fetch) |
| `query`, `resultType` (`core`), `pageSize`, `format=json`, `synonym`, `cursorMark=*`, `sort` | Live request: the response's `request` object echoes `queryString`, `resultType`, `cursorMark`, `pageSize`, `sort`, `synonym` | Same |
| `pageSize` 1–1000 (default 25); `resultType` ∈ idlist/lite/core; `cursorMark` pagination | Secondary source (rOpenSci client docs) | [epmc_search](https://docs.ropensci.org/europepmc/reference/epmc_search.html) |
| `OPEN_ACCESS:y`, `HAS_FT:y` query filters | Live request: accepted and all results had `isOpenAccess: "Y"` | — |
| `sort=CITED desc` | Live request: accepted, results ordered by `citedByCount` | — |
| Response: `hitCount`, `nextCursorMark`, `resultList.result[]` with `pmid`, `pmcid`, `doi`, `title`, `abstractText` (HTML), `isOpenAccess`, … | Live request | — |

### OpenRouter web search (server tool)

| Item | How verified | Source |
|---|---|---|
| `tools: [{"type": "openrouter:web_search", "parameters": {engine, max_results, max_uses, max_characters, allowed_domains}}]` on `/chat/completions` | Docs + live request (2026-09-21) | [Web Search server tool](https://openrouter.ai/docs/guides/features/server-tools/web-search.md) |
| The plugin (`plugins: [{id: "web"}]`) and `:online` are deprecated in favour of the server tool | Docs | Same |
| Every search result comes back as `message.annotations[].url_citation {url, title, content}` (8 of 8 for `max_results: 8`), even though the model only replied "DONE" | Live request | — |
| `usage.cost` is returned on every chat completion and includes the search fee ($0.00714 = $0.007 Exa + $0.00014 tokens); `usage.server_tool_use_details.web_search_requests` counts searches | Live request | Docs list Exa at $0.007/request up to 10 results |
| `allowed_domains` with Exa restricts results (all 8 were PMC, PubMed, Europe PMC, or NCBI Bookshelf) | Live request | Docs |
| `openai/gpt-5.6-luna` returns 404 "No endpoints found that can handle the requested parameters" with medsim's request (strict `json_schema`, `temperature`, `provider.require_parameters`) | Live request | — |

### Europe PMC (verified 2026-09-22)

| Item | How verified | Source |
|---|---|---|
| Section fields `CASE`, `RESULTS`, `TABLE`, `METHODS`, `DISCUSS`, `INTRO`, `BODY`, `FIG`, plus `PUB_TYPE`, `ORGANISM`, `HAS_FT` exist | Live `GET /fields?format=json` (143 fields) | — |
| `CASE:(albumin) AND TITLE_ABS:(biloma OR "bile leak")` returns 25 case reports; `RESULTS:` and `PUB_TYPE:"Case Reports"` combine as expected | Live requests | — |
| `NOT ORGANISM:(cat OR dog ...)` did not remove a cat case report, so animal studies are filtered after retrieval instead (MeSH `Animals` without `Humans`: 21 of 30 animal-titled cached records) | Live request + cache | — |
| `GET /{PMCID}/fullTextXML` returns JATS XML (`body/sec/p`, `table-wrap/table/tr`) for open-access articles, an error status (e.g. 500) otherwise | Live requests | — |
| **Intermittent HTTP 200 replies containing only `{"version":"6.9"}`** (no `resultList`). The original retriever cached them and raised; Europe PMC dropped out of 11 of 50 questions in the first benchmark run. Now retried with backoff, never cached, and ignored if found in an old cache | Live requests + benchmark runs | — |

### LitSense annotations
- Each item's `annotations` are `"offset|length|type|id"` strings; `type` includes `species`
  with NCBI taxonomy ids (`9606` = human, `10090` = mouse, ...). Used by the population filter:
  a passage is dropped when it is tagged with a common laboratory or veterinary animal and not
  with human (bacteria and other species do not count).

### Cost accounting
- `LLMCallRecord.cost_usd` is OpenRouter's `usage.cost` for that call; `None` when the response
  has no cost (other backends, failed calls).
- The OpenRouter key's `/key` usage counter lags a minute or more behind requests, so per-call
  `usage.cost` is the accounting source; the counter is only a cross-check.

## Could not confirm

- Europe PMC official parameter reference text, full list of sortable fields, and any rate limit
  (docs return 403). `min_interval_s` defaults to 0 and is configurable.
- Whether every OpenRouter provider for the default model strictly enforces `json_schema`
  (docs say enforcement varies). Pydantic validation plus one repair retry covers this.
- Whether `seed` is honoured by the upstream provider (it is accepted per `supported_parameters`).
- OpenRouter `reasoning` controls: not used, because not verified. `MEDSIM_LLM_EXTRA_BODY` passes
  arbitrary extra request fields if needed.
- LitSense `rerank=false` behaviour (only `rerank=true` was exercised live).
- **No live OpenRouter chat completion was executed** (no API key was used during the build). LLM
  test fixtures are hand-written in the documented response shape.

## Assumptions and extensions

### Contracts
- **Stage A JSON** adds `query_scope` (`patient|off_topic|withheld`) and `partial_facts`. These are
  needed for the §13 off-topic and partial-answer cases and for the diagnosis refusal.
- **Stage B JSON**: `clinical_variable` may be null when declining; adds `decline_reason`.
- **Stage C JSON** adds `value`, `unit`, `literature_range`, `conflict`. These feed the ledger
  tuple, the range-in-evidence rule, and the named-conflict retry.
- `LLMCallRecord` = `stage, model, prompt_tokens, completion_tokens, latency_ms, attempt, purpose
  (initial|json_repair|consistency_retry), success, error`. Failed attempts are recorded too.
- `EnvironmentResponse` field names are exactly as specified. There is no extra field for the
  "synthesized" flag: it is `answer_source == "literature"`, and the CLI prints an explicit
  SYNTHESIZED banner.

### Files beyond the §4 layout
`medsim/__main__.py` (needed for `python -m medsim`), `errors.py`, `http_utils.py` (retry,
backoff, rate limiter), `units.py`, `rules.py`, `retrieval/cache.py`.

### Orchestration
- LLM transport failures and JSON that is still invalid after repair raise `LLMError` /
  `LLMResponseError`. They are not converted to `unanswerable`, so infrastructure faults never
  look like simulated clinical answers. The CLI reports the error and continues the batch
  (exit code 1).
- The ledger is checked twice: before Stage A (normalized query text or rule-derived
  `variable@timepoint` key), and again after Stage B using its `clinical_variable`, so that
  paraphrases without known keywords are still caught before retrieval.
- Case-study answers are also stored in the ledger, so repeats skip the LLM. Unanswerable results
  are not stored.
- Ledger facts carry a `case_id` and are stored per case. Lookups, prompt injection, and
  `env.reset()` only touch the environment's own case. A ledger hit adds `ledger_case_id` to
  `retriever_parameters`. Ledger file format version 2; version-1 files (no case ids) are
  rejected rather than guessed.
- **Token budgets and cut-off replies.** `max_tokens` covers reasoning tokens. With the earlier
  defaults (Stage B 800–1200), some Stage B calls came back with `finish_reason: "length"`, all
  completion tokens counted as reasoning tokens, and content of a single space. This was
  confirmed from raw OpenRouter responses on 2026-09-15. Defaults are now 4000 (resolver,
  Stage B) and 6000 (Stage C). A reply cut off by the limit is returned by the client instead
  of raising, and `call_structured` retries it once with double the budget (`purpose:
  "length_retry"`). If that is cut off too, it raises `LLMTruncatedError`, naming the setting to
  raise. A complete, valid JSON reply is accepted even if `finish_reason` is `length`.
  `llm_calls` records `finish_reason` and `max_tokens` for every call. Worst case per stage is
  three calls: initial, length retry, JSON repair.
- A ledger hit returns `literature_search=false` (no search ran for this call), the stored
  `answer_source`, confidence, and evidence, plus `ledger:<key>`.
- Unit requests ("in Fahrenheit") on a repeat append a deterministic conversion to the verbatim
  stored answer: `"Temperature is 37.0 °C. (98.6 °F)"`.
- Multi-part: `answer_source` is `literature` if any part is synthesized, else `case_study` if
  any part came from the case, else `unanswerable`. `confidence` is the minimum across parts,
  answers are newline-joined, and evidence is prefixed with `[sub-query]`. `retriever_parameters`
  has `multi_part: true` and a `sub_queries` list.
- A synthesized answer whose cited ids are not among the retrieved documents keeps the answer but
  drops the unknown ids and sets `confidence="low"`.
- `used_llm` = distinct models from `llm_calls`. On a ledger hit (no calls) it reports the
  configured resolver model.

### Retrieval
- `per_source_counts` counts documents in the final merged list. Pre-merge counts are in
  `retriever_parameters.raw_counts`.
- LitSense `doc_id` = `PMID:<pmid>#<SECTION>-<sha1(text)[:8]>`, so several passages from one
  article survive identifier dedupe. Europe PMC `doc_id` = `PMID:` → `PMCID:` → `DOI:` →
  `EPMC:<source>:<id>`.
- Near-duplicate text: token-set Jaccard ≥ `near_duplicate_threshold` (default 0.9).
- LitSense has no page-size or filter parameters; `max_results` truncates client-side.
- Europe PMC has no relevance score in the response (`score=None`). `sort` unset means the API's
  default (relevance) order. A single page is fetched (`cursorMark=*`).
- Document URLs: PubMed → PMC → doi.org, built from identifiers.
- Cache key: `(source, query, sha256(request params))`. LitSense keys also include the endpoint,
  so sentence and passage results don't collide.

### Query formulation
- Stage B returns term lists alongside the fallback `literature_query`: `variable_terms`,
  `condition_terms`, `related_condition_terms`, `context_terms`. Code in
  `medsim/retrieval/query_formulation.py` turns them into source-specific queries, so the LLM
  never writes query syntax. Terms are stripped of quotes, brackets, wildcards, field tags, and
  boolean operators before use.
- **Europe PMC:** `TITLE_ABS:(variable synonyms) AND TITLE_ABS:(condition synonyms)`. `TITLE_ABS`
  and `HAS_ABSTRACT` appear in the live `GET /fields?format=json` listing, and both were tested
  with live searches (accepted, and restricting results as expected). On the bilirubin example
  the old keyword string put 1 of the top 10 on-topic (6 had no abstract); the title/abstract
  synonym query put 10 of 10 on-topic. Europe PMC's own `synonym=true` expansion made results
  slightly worse, so it stays off.
- **LitSense:** a short `"<variable> <condition>"` phrase. Its no-match response says passages
  must share at least 10% of the query's words, and in probes short focused queries beat long
  keyword lists and question-style queries.
- **Relaxation ladder per source**, strictest first. A source moves to the next query only while
  fewer than `relax_min_relevant` (default 3) collected documents mention a variable term;
  results from all attempts are unioned. Europe PMC: variable+condition → variable+related
  condition → the same groups in any field (with `HAS_ABSTRACT:y`) → variable + reference-range
  terms. LitSense: variable+condition → variable synonym+condition → variable+related condition →
  variable + reference range. Every attempt is recorded in
  `retriever_parameters.per_source.<source>.query_attempts`.
- **Lexical rerank** within each source before the round-robin merge: +3 variable mentioned,
  +2 condition (or +1 related condition), +2 a number near the variable (numeric questions only),
  +0.5 context term. Ties keep the source's order.
- Without term lists (older outputs, custom callers passing a plain string) every source gets the
  keyword string unchanged, with no relaxation or reranking.
- `literature_search_result.query` still holds the query actually sent. When sources were sent
  different queries it reads `europe_pmc: <query> | litsense: <query>`, showing each source's
  final attempt.

#### Evaluation (2026-09-15)
- **Setup:** 12 pairs from `cases/combined_272_whole_chunking.json`. Each pair is a randomly
  chosen case (seed 20260915) plus a common vital sign or lab value absent from its narrative,
  asked as "What is the patient's <variable>?". Four setups each returned 8 documents:
  1. *old*: old Stage B prompt, keyword string, old retrieval (Europe PMC page 10, LitSense
     passages top 10, no rerank).
  2. *new prompt + old retrieval*: the new prompt's fallback keywords through old retrieval.
  3. *new (passages)*: term lists, source-specific ladders, rerank; Europe PMC page 25, LitSense
     passages top 30.
  4. *new (sentences)*: as 3, with LitSense in sentence mode.
- **Grading:** an LLM judge (same default model) graded each document blind to the setup, in
  shuffled order. 2 = gives a value, range, or frequency of the variable in this or a closely
  related condition; 1 = relevant discussion without a usable value; 0 = no help. All 12 pairs
  completed in all setups; 72 LLM calls, none failed.

| Setup | Total grade (max 192) | Useful docs per pair | Pairs with a useful doc | Pairs with a value-giving doc | Wins/ties/losses vs old |
|---|---|---|---|---|---|
| old | 7 | 0.58 | 3 | 0 | — |
| new prompt + old retrieval | 7 | 0.58 | 4 | 0 | 3/8/1 |
| **new (passages), default** | **49** | **3.67** | **10** | **2** | **10/2/0** |
| new (sentences) | 30 | 2.50 | 8 | 0 | 7/4/1 |

- **Reading:** the gain comes from how queries are formulated and ranked, not from the prompt
  wording (row 2 matches row 1). LitSense passages beat sentences, so passages stay the default.
  Two pairs got nothing useful from any setup: oxygen saturation in Zinner syndrome, and platelet
  count in *Paecilomyces* vaginitis. Both are rare conditions where the variable is unrelated to
  the disease.
- **Caveats:** small sample; a single run; the judge is the same model family as the query
  generator. Europe PMC intermittently returned 502/503/504 during the run and failed some
  requests after retries on 4 pairs, which adds noise to those rows.

### Rules (limitations)
- Variable keywords cover common vitals and labs (`rules.VARIABLE_KEYWORDS`). Timepoints: `day N`,
  `hour N`, `week N`, `POD N`, `N hours after`, admission/presentation, discharge, baseline.
- Multi-part splitting only triggers when each conjunction-separated segment names exactly one
  known variable. "chest pain and shortness of breath" is **not** split.
- Unit conversions: °C/°F, kg/lb, cm/m/in, g/dL↔g/L, glucose and creatinine mg/dL↔SI.

### Tooling
- Built and tested on Python 3.11.15 via `uv`. Dependencies are pinned to major versions.
- Retriever fixtures are real responses recorded on 2026-09-15.
  `openrouter_models_deepseek_subset.json` is the live `/models` response **trimmed** to
  DeepSeek entries for size.
