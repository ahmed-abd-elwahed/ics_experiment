# Decisions

A running log of the decisions Claude makes while working on this project: choices that were
not spelled out in the request. Newest entries go at the bottom. Each entry says what was
decided and why. Decisions specific to `medsim` that were confirmed with the project owner are
in [environment/NOTES.md](environment/NOTES.md).

## 2026-10-10

### Presentation rules and the framework overview diagram

| Decision | Why |
|---|---|
| The presentation rules live in `.claude/rules/presentation.md`. | Claude Code loads every file in `.claude/rules/` automatically when this folder is open. |
| The rules file is kept out of git through `.git/info/exclude`, not `.gitignore`. | `.gitignore` is itself pushed; the exclude file is local to this clone. |
| Where the rules and the "Presentation Design" system disagree on slide order, the rules win. | The design system opens with a hook slide; the rules fix slide 1 as the title. |
| The rules file tells Claude to build decks with "Presentation Design". | The overview image was requested in that style, so the deck should match it. |
| The overview diagram is an SVG, `.claude/rules/framework-overview.svg`, 1728 × 776. | That is the body area of a 1920 × 1080 slide with the design system's 96px margins. |
| Diagram labels are in sentence case; the strategy robot carries the one terracotta accent; lines are ink. | The design system's rules: sentence case, one accent per slide, ink outlines. |
| "Center the Simulated environment box" was read as centring its label on the box's top edge. | The label was the only off-centre part; the original image has it centred above the box. |
| Box shading: `data-grey` for the environment box, `data-peach` for the label boxes. | Both are design-system fills. This departs from its rule that labels are white chips, because shading was asked for. |
| Diagram text was raised from 28px to 34px, and the strategy robot moved 30px left. | 34px keeps every label on one line; the move keeps the widest label inside the image. |
| The "Case study" label and icon were lowered by 14, 12 and then 24px (50px in total). | "A little", "a little more", then "double" the last step. |
| When the SVG was to be pushed, the exclude rule was narrowed to `presentation.md` only. | So the SVG can be tracked while the rules file stays local. |

### Search methods deck

| Decision | Why |
|---|---|
| The deck's numbers come from `environment/results/repeats/repeat_summary.md`. | It is the mean ± SD table over the ten runs. |
| Nine slides: title, research question, overview, methods, protocol, accuracy chart, two result tables, closing. | The first three are fixed by the rules; the rest follow the design system's body-slide and closing-slide rules. |
| The results table is split into an accuracy slide and a cost-and-time slide. | Eleven columns do not fit one slide at a readable size. |
| The "not comparable" and "no label" columns are left out of the slide and summarised in a footnote. | They are small and would have forced a smaller font. |
| The accuracy chart leaves out the case-only configuration. | It answers a different question set (set C), so it is not comparable on the same axis. |
| Native Google and OpenAI search are drawn as squares and marked "one run". | They were run once and have no spread; shape as well as colour marks the difference. |
| The closing slide is titled "Search method changes cost and speed, not accuracy". | The design system forbids "Summary" and asks for a title that states the takeaway. |
| The run-to-run comparison quotes the SD range (1.6 to 2.4 points), not run 1's range. | Run 1's per-configuration values could not be confirmed from one table. |

### Design system: subtitles and descriptions

| Decision | Why |
|---|---|
| `subtitle` 40px → 52px; `slide-description` 28px → 36px. | "Bigger font", while staying below the title sizes (96px and 56px). |
| Subtitle: one line, eight words at most. Description: one line, ten words at most. | "More concise"; one line is what fits at the new sizes. |
| A subtitle whose wording is fixed by the brief is kept as given. | The fixed "Research Question" subtitle is 15 words. |
| The existing deck was not changed; the before-and-after was shown as an example only. | Only the design system and an example were asked for. |

### Commits

| Decision | Why |
|---|---|
| Each diagram change was committed on its own, without the other uncommitted work. | Only the SVG was asked to be pushed at the time. |
| The outstanding work went in as two commits: code and tests, then results. | The results are 386 MB of generated files; keeping them apart keeps the code commit reviewable. |
| Changed files were scanned for API keys before pushing. | `check_credits.command` handles an OpenRouter key; it reads it from `.env`, which stays ignored. |
| Tests were not run before those commits. | The request was to commit and push existing work as it was. |
| This log is `DECISIONS.md` at the repo root, and it starts with this session's decisions. | The only existing notes file, `environment/NOTES.md`, is specific to `medsim`. |

## 2026-10-13

### Merging the branches

| Decision | Why |
|---|---|
| `experiment-framework` was merged into `main` as a fast-forward, with no merge commit. | `main` had no commits of its own: it was the first two commits of `experiment-framework`, so moving it forward loses nothing and keeps the history linear. |
| The `experiment-framework` branch was kept, pointing at the same commit as `main`. | Only a merge was asked for; deleting a branch is a separate choice. |

### New answer metrics: the zlog z-score

| Decision | Why |
|---|---|
| The closeness metric is the zlog z-score: Hoffmann's zlog transformation with the ISO 13528 proficiency-testing z-score, the hidden true value as the assigned value. | The metric was to be based on a published method in its naming and equations; an earlier formula of my own (a tolerance from the reference range, halving per unit) was set aside for that reason. |
| The headline is the mean of \|z\| capped at 3; unanswered and not comparable answers score 3. | 3 is ISO 13528's unsatisfactory limit; the cap keeps a few wild answers from dominating the mean, and unanswered questions stay in the denominator as "no label" does. |
| Range answers use the continuous ranked probability score of a uniform forecast. | It is a proper scoring rule that equals the absolute error for a single value. |
| One-sided reference ranges take LL = 15% of UL; variables without an interval take σ = 0.15; values at or below zero use the z-score without logarithms. | zlog needs two positive limits. These three are my choices; the 15% lower limit is recalled from the literature and not confirmed (the search was rate-limited). |
| Reference limits are to be fixed once per question (median of the judges), not taken per answer. | Every method is then scored with the same σ, so a difference between methods cannot come from differing reference ranges. |
| The metric was tested without API calls: unit tests, then run 2's stored answers with numbers parsed from the stored judge text. | Testing "across multiple examples" was asked for, and no spending had been approved. |
| The arithmetic is in `bench/zlog.py`; it is not wired into `judge` or `report` yet. | The second metric and the budget are still under discussion. |
| The stored judgments are not reused for the real evaluation. | Their reference ranges and answer values are free text; a third of the ranges are not a clean two-sided interval and units are often unconverted. |
| The check's weaknesses (narrow intervals far from normal, non-numeric true values, little separation between methods) are recorded in `environment/bench/README.md` rather than fixed. | Fixing the first would mean leaving the published formula; that is a choice for the project owner. |
| Later commits go to `experiment-framework` and `main` is fast-forwarded with each push. | The two branches were merged on request; keeping them at the same commit keeps that true. |

### New answer metrics: faithfulness

| Decision | Why |
|---|---|
| The second metric is faithfulness: the share of answers whose value the retrieved documents support (after RAGAs). | The current metrics and the zlog z-score compare the answer with the case only; the stored runs suggest the methods differ in how often the documents back the answer (30% to 61% by medsim's own label), not in how close the answer is. |
| One yes/no question per answer with a verbatim quote that code checks; no claim splitting, no numeric compatibility test, no tally by kind of support. | A first design with those parts was judged over-complicated by the project owner, who confirmed this version. |
| Every answer that has documents is judged, whatever medsim's `path` says. | Some `best_guess` answers cite a literature range, so the label is not reliable. |
| `gemini_knowledge` is left out of this metric. | Its only document is the model's own statement, so support is trivial. |
| The metric is recorded in `environment/bench/README.md` but not implemented. | The budget for judging has not been approved. |

### New answer metrics: faithfulness

| Decision | Why |
|---|---|
| The second metric is faithfulness (RAGAs): whether the retrieved documents support the answer's value. | The zlog check showed closeness is similar across methods, while the share of answers taken from the documents differs by 30 points; a metric that reads the documents is the one likely to separate methods. |
| It is graded as one yes/no question with a verbatim quote that code checks, and the panel's majority decides. | The first design (claim splitting, extracting the documents' numbers, a zlog compatibility test, a tally by kind of support) was judged over-complicated by the project owner, who confirmed this simple form. |
| Every answer with documents is judged, not only those medsim labels as taken from the literature. | That label is the synthesizer's own claim, and some best-guess answers cite a literature range. |
| `gemini_knowledge` is left out of this metric. | Its one document is the model's own statement, so support would be trivial. |
| The medsim path label was used as a free preview of the metric's sensitivity. | It needs no API calls and shows whether the documents are where methods differ. |

### New answer metrics: faithfulness

| Decision | Why |
|---|---|
| The second metric is faithfulness (RAGAs): the share of answers whose value the retrieved documents support. | The current metrics never look at the documents, which is where the stored runs show the methods differing (30–61% of answers reported as taken from the documents). |
| One yes/no question per answer with a verbatim quote that code checks; no claim splitting, no number extraction, no zlog compatibility test, no tally by kind of support. | The fuller design was judged over-complicated by the project owner; the concept was kept. |
| Every answer with documents is judged, whatever path medsim reports. | Some `best_guess` answers cite a literature range, so the path label is not reliable. |
| `gemini_knowledge` is left out of this metric. | Its one "document" is the model's own statement, so support would be trivial. |
| Before proposing a set B case-alignment metric, the stored set B answers were compared between methods and between runs. | It is free, and it shows whether such a metric has anything to detect. |

### New answer metrics: case alignment and the evaluation plan

| Decision | Why |
|---|---|
| A third metric, case alignment, is added to the test: three labels for a set B answer against the rest of the case. | Requested, although the stored answers suggest it will not separate methods; the test settles it for about $1. |
| It is named "case alignment" and its labels are aligned, neutral, and contradicted. | The project owner asked for "aligned" in place of natural language inference's "entailed", in the name and the label. |
| A label without a quote that is verbatim in the case becomes neutral. | The same guard as for faithfulness: a claimed link to the case must be checkable. |
| The test uses run 2 and the main judge. | Run 2 is the first run made with medsim's current behaviour; the main judge breaks ties in the panel. |
| Sensitivity is the SD of the method means over their standard error, plus the number of method pairs whose 95% interval excludes zero, computed for the current metrics on the same data too. | "More sensitive" needs one number that can be compared between a new metric and the one it would complement. |
| Cost estimates use run 2's stored token counts and today's listed prices, not the earlier rough figures. | The earlier estimates ($8 for the zlog z-score, $45–55 for faithfulness) were guesses made before the prompts were sized. |

### Proposal: implementing the five strategies

| Decision | Why |
|---|---|
| "The presentation file" was read as `Meeting 63.pptx`; the strategies are its slides 8 to 12. | It is the only deck in the repo, and those slides are titled "Information Collection Strategies". |
| The "webapp" is a standalone page, `proposals/strategy-implementations.html`, also published as an artifact; the project's own web app was not changed. | The request was for a proposal with diagrams, and nothing is implemented yet, so a tab in the experiment app would show strategies that cannot be run. |
| The page reuses the project web app's colours (navy for the LLM, dashed green for the environment). | So the proposal reads as part of the same project. |
| Every strategy keeps the `StrategySession` interface and stops by returning `None`. | The runner already supports it (`strategy_done`). |
| A `final_diagnosis()` step and a graded diagnosis are proposed for all strategies. | Every slide ends in "Return diagnosis" and the research question is about accuracy, but the runner never asks a strategy for a diagnosis. |
| Stop rules are comparisons in code on values the LLM returns, with thresholds in `params`. | The thresholds can then be tuned and reported; an LLM asked "should I stop?" cannot be. |
| Gut feeling uses unreasoned calls and five one-word votes. | A single word carries no confidence; agreement between samples stands in for it. |
| Channel-based: after the physical exam, confidence is checked again and the diagnosis is returned either way. | The slide draws no arrow out of "Physical exam" and has no further channel. Flagged as an open question, with whether tests are a third channel. |
| Sequence-based: 3 opening questions, refinement until 2 candidates or 75% of the budget, then the final phase. | The slide gives the order of the phases but no conditions. Flagged as an open question. |
| All thresholds (0.80, 0.30, 4 of 5, 75%) are starting values of mine. | The slides give none; they need a pilot before a real run. |

### Proposal page: overview diagram in every figure

| Decision | Why |
|---|---|
| Each strategy's figure is the environment half of `framework-overview.svg`, copied unchanged, with a panel holding that strategy's flow where the strategy robot stood. | "Replace the ICS with the proposed diagram for each strategy." |
| The strategy's name sits on the panel's top edge in the overview's label style, and the Query and Answer arrows run between the environment's LLM and the steps that send and receive them. | It keeps the overview's reading: the strategy queries the LLM and gets an answer. |
| The flows were re-laid out to fit beside the environment; the separate environment box in each flow was removed. | The overview's environment now plays that part. |
| The page has one light theme with a white background and no dark variant. | A light background was asked for, and the overview diagram's colours are drawn for a light ground. |

### Judge panel and the Jev decision model

| Decision | Why |
|---|---|
| The panel is now Claude Haiku 5.5 (main judge), GLM 5.3 Flash, and GPT-6 Luna; `bench/config.py` holds it as the default. | The project owner replaced Gemini with Haiku and asked for a replacement for Qwen. Gemini's batch endpoint is refused under the account's Zero Data Retention setting and it was the dearest judge; Qwen took 9–13 s per call and was rate-limited. |
| GLM 5.3 Flash was proposed for Qwen's place. | Of four candidates re-judging the same 40 stored answers it finished every call, agreed best with the stored judges (15–17 of 20 on masked correctness), and was the cheapest; both Mistral models were rate-limited at ten parallel calls. |
| Haiku takes Gemini's roles: first in the list, so tie-breaker, and the single judge of the test. | "Replace Gemini with Haiku" was read as a like-for-like replacement. |
| The Gemini and Qwen verdicts stay in the judgment files; the earlier panel is kept as `PREVIOUS_JUDGE_MODELS`. | Nothing is deleted, and the earlier table can be rebuilt. |
| The account's privacy setting was not changed. | It is a data-retention decision for the account owner. |
| The Batch API is not used. | Two GPT batches of 20 and 300 requests had completed nothing after 25 minutes; the same calls take under a minute on the standard API. |
| "Jev" is `typesafe/jev-1.13`, called through OpenRouter's decisions endpoint, one answer per request. | The project owner named it. Its documentation and endpoint take one item of at most 32,000 tokens per request, not a dataset. |
| Jev judges the two existing metrics, faithfulness, and case alignment, but not the zlog z-score; its faithfulness and case alignment labels are not quote-checked. | It returns a typed choice with probabilities and no text, so it can neither read out a number nor quote a passage. |
| Jev's verdicts on the existing metrics are stored in the panel's judgment files with rubric `v2`, its probabilities in `rationale`. | The existing vote and report code can then count it as a fourth judge; its criteria are the rubric's own wording. |
| Jev is not in the default panel; the report shows the table with three judges and again with Jev added. | Requested. With four judges a 2–2 split is decided by the main judge, as an absent majority already is. |

### Building the new metrics

| Decision | Why |
|---|---|
| The new metrics live in `bench/answer_metrics.py`, with their own command, and write to `<workspace>/judge/<metric>.jsonl`. | The existing judge and report steps stay as they were, and each new judgment is stored the way the old ones are. |
| Each judge has its own pool of workers. | A slow or rate-limited judge then cannot hold back the others. |
| Reference limits and the reading of the true value are asked once per question, from all three judges, and combined by the median; a limit that at least half of the judges leave empty is left empty. | Every method and run is scored on the same scale; a median resists one judge's outlier. |
| An answer's zlog score is the median of the judges' scores; a judge that finds no comparable number gives 3. | Consistent with the cap for unanswered questions; the median plays the part the majority vote plays for labels. |
| For blood pressure the systolic value is scored. | One number is needed; the alternative, scoring both components, doubles the rules for 8 questions. |
| A true value given as a range or bound ("60–70", "> 1000") scores 0 for an answer inside it, otherwise the distance to its nearest end. | 32 of 141 set A true values are not a single number. |
| Questions whose true value is not numeric are left out of the zlog z-score and counted. | "3+" or "diminished" has no place on the scale. |
| The zlog z-score and case alignment also run on set C. | The case-study configuration then has values in the final table. |
| A faithfulness "yes" without a quote found in the documents counts as not supported; a case alignment label without a quote found in the case counts as neutral. | As planned: a claimed link must be checkable. |
| The run stops starting new calls when OpenRouter answers HTTP 402. | The balance is close to the estimate; a clean stop keeps what is done. |

### Implementing and evaluating the five strategies

| Decision | Why |
|---|---|
| Every strategy ends with a differential of up to 10 diagnoses with probabilities, from one shared final LLM call. | The metrics in `DDx-Experiment/evaluation.py` are hit rate at 1 to 10, nDCG@10 and MRR, which need a ranked list; the proposal's single diagnosis would only give hit rate at 1. |
| The strategies run on `anthropic/claude-haiku-5.5`; the environment on `deepseek/deepseek-v4.1-flash` without `:batch`. | "Cheap and fast": Haiku 5.5 is $0.10 / $0.50 per million tokens and answers without reasoning. The environment keeps the model family it was benchmarked with, but synchronously, because a batch per sequential step would take hours each. |
| Haiku 5.5 does not accept `temperature` on OpenRouter, so strategy calls run at the provider's default sampling. | Found when checking the config; the gut strategy's five readings therefore differ only as far as the default sampling lets them. |
| "4 iterations" is `max_iterations: 4` for all five strategies, with each strategy's own stop rule still active. | The same question budget for every strategy; a strategy that is satisfied earlier stops earlier, which is what the slides draw. |
| Channel-based: 2 questions per channel under that limit. Sequence-based: 1 opening question, 2 refining, 1 final. | The budget is divided evenly over the channels, and by shares of 25% / 50% / 25% over the phases. |
| Channel-based: no confidence check after the last channel. | Nothing can follow it, so the check would be a call whose result changes nothing. |
| Calls made while deciding to stop are saved with the diagnosis; each question saves the strategy's state. | "Record everything": a stopping decision has no question to attach its calls to. |
| The metrics are computed in `evaluation/metrics.py`, not with ranx. | With one true code per case they are three one-line formulas; ranx would add numba to the project. The definitions are the same. |
| ICD coding follows `DDx-Experiment/utils.py`: ICD-11 MMS 2024-01, flexible search, first result, a cache keyed by the normalized name. A lookup that fails after retries is not cached as "no match". | Same codes as the earlier project; caching a network failure as "no code" would silently lower scores. |
| The WHO ICD API credentials were copied from `DDx-Experiment/utils.py` into `.env`, which is ignored by git. | They are needed for the coding and must not be committed. |
| The LLM-judged appropriateness and comprehensiveness scores of `evaluation.py` are not implemented. | They are off by default in `run_experiment.py`, and the request was to compare by ICD code. |
| `basic` gives no diagnosis and is not in the run. | Only the five strategies were asked for. |
| The other uncommitted changes in the working tree (bench files, results, part of this log) were left out of the commit. | They belong to other work in progress. |

### Running the five strategies on the 272 cases

| Decision | Why |
|---|---|
| The ICD cache of `DDx-Experiment` (113,386 names) was merged into `.icd_cache/`; this project's own 208 lookups agreed with it on every shared name. | Asked for, to speed up coding. Its 188 "no match" entries are kept as they are. |
| The environment runs on `openai/gpt-6-luna`. | Asked for. It is the synchronous endpoint, $0.10 / $0.50 per million tokens. |
| A 5-case pilot ran before the full run ($0.13, 2.5 minutes). | Nothing had touched the live APIs yet; the cost was within the approved estimate. |
| The gut strategy's limit for one reading went from 50 to 300 tokens. | In the pilot one reading ran past 100 tokens and failed its case run; a normal reading is 13. |
| The pilot's record, evaluation and report are kept in `records/` under a `pilot_` name. | "Record everything about the runs." |
| The report is built by `evaluation/report.py` as HTML and printed to PDF by headless Chrome, like the benchmark reports. | Same method as the existing reports; no new dependency. |
| The report adds 95% Wilson intervals for hit rate at 1 and at 10. | One run per case and strategy; the intervals show which differences this run can support. |
| The full run's 11 failed case runs (all channel-based, the classifier's 50-token limit) were run again with the limit at 300, and the results use `strategies_272_20261012T165402Z_merged.json`. | A failed run scores zero, which would have lowered channel-based by a fault of the code, not of the strategy. The first record is kept unchanged, and the merged record lists the replaced runs under `reruns`. |
| `experiment/rerun.py` does this: it reruns a record's failed case runs with the record's own config and writes a merged record. It has no test of its own yet. | Written while the run was in progress; it was exercised on the real record. |
| The report adds an exact McNemar test for every pair of strategies, with a Bonferroni threshold. | The strategies ran on the same cases, so a paired test is the right comparison; ten pairs need a correction. |
| Both 84 MB records (first pass and merged) are committed. | "Record everything"; each is under GitHub's 100 MB file limit. |

### Test stage, revisions, and the full run

| Decision | Why |
|---|---|
| Faithfulness was kept as first designed. | On run 2 with one judge its spread between methods was 8.0 times its noise, against 0.6–0.8 for the existing metrics. |
| The zlog z-score's one revision widens σ by `max(1, |zlog(truth)| / 3.92)`. | 22% of scores sat at the cap, many for very abnormal true values answered with similarly abnormal ones. A first draft divided by 1.96; it rated an answer in the middle of the reference interval as satisfactory whatever the true value, so the divisor was doubled before any result was looked at. |
| Case alignment's one revision compares the level the case leads one to expect with the level the answer states. | The first version returned neutral for 96% of answers and contradicted for none, so it had no room to differ. |
| Both revised versions were kept. | The rule was to keep the more sensitive of the two versions; the revised ones scored higher on run 2 (0.25 against 0.23; 0.60 against 0.57). Both differences are inside the noise, and the report says so. |
| Only one revision was tried for each metric, chosen by reasoning before its result was seen. | One retry was the brief; trying formulas until one separates the methods would have produced a number that means nothing. |
| The full run was ordered so that the parts every table needs came first, and faithfulness and case alignment by the chat judges ran run by run behind a balance check. | Measured prices put the whole plan at about $63 against a balance of $48 (GLM's reasoning tokens made its faithfulness calls about five times the estimate). |
| Run 1 was judged first in that loop. | Only run 1 has the two native search configurations. |
| The run continued past the first estimate when the account balance rose by $100 during it. | I did not add the credit; the approved plan was all ten runs, and the balance check was the only brake I had set. |
| Run 10's faithfulness and case alignment by the chat judges were left unfinished. | The API key reached its total limit of $250, a limit set on the key. I did not look for a way around it. |
| A run counts for a metric and configuration only when every panel judge has judged at least 98% of its answers. | Otherwise run 10's few judged answers, or Jev's verdicts alone, would have been averaged as if they were a panel's. |
| The planned sanity check of faithfulness was not run. | The key limit was reached first; the report lists it as not done. |
| `repeat_summary.*` and the workspaces' reports were rebuilt with the new panel; the earlier table is kept as `repeat_summary_previous_panel.*`. | The old scores were to use the new judges; nothing was to be lost. |
| `make_repeat_summary.py` now counts failed judge calls in the two existing metrics' files only, and no longer names Qwen. | It had started counting run 10's unfinished new-metric calls as failures of the old metrics. |
| The report is A4 landscape, built from HTML by headless Chrome like the other result PDFs. | The scores table has nine columns; the existing tables are made the same way. |
| The presentation rules were not applied to the report. | They are for slide decks; a PDF report was asked for. |
| The cost of this work is reported from the stored judgments ($49.46, about $50 with tests), not from the key's usage that day ($56.60). | Another session ran an experiment on the same key during the run, so the key's usage and the balance both include its spend; the key limit was reached by the two together. |

### Metrics and strategies deck (2026-10-13)

| Decision | Why |
|---|---|
| The deck has 21 slides in the order given in the request; the first three are the fixed opening slides, and the last is "Thank you", not a summary. | The presentation rules fix slides 1–3 and say the rules win over the design system's order; the requested order then wins over the design system's "close by reminding" slide. The takeaways slide still follows that rule's form (a takeaway title, a visual hint per point). |
| The title slide's subtitle is "New answer metrics and five collection strategies". | The rules ask for a subtitle that summarises the deck; the design system caps it at eight words. |
| The nine configurations are named Model knowledge, Original retrieval, Improved retrieval, Exa search, Parallel search, Perplexity search, Google search, OpenAI search, and Case only. | A two-word description of each was asked for; the full names are in the table slide's speaker notes. |
| The environment table shows five of the eight metric columns (same category, consistent, mean \|z\|, supported, aligned) as means without standard deviations. | Nine rows already exceed the design system's "about six rows"; one slide was asked for, so columns were cut to keep the text at 28px. The report has the full table. |
| Both tables are built the design system's way: header row in the label style, cells in body text, horizontal rule lines only, one accent-coloured row. | Asked for during the work ("make the tables have the same design system"). |
| The strategy diagrams are the proposal page's own figures, rendered from that page at twice their size and placed as images. | The page draws them with script and styles them with its stylesheet; a slide's inline SVG cannot carry either, and an uploaded SVG loses its styles and fonts. |
| The overview image was uploaded as the SVG file itself. | The rules say to use that file as it is. |
| The Kaggle slide shows the public page of RSNA Knee Abnormality Detection, captured signed out on 2026-10-13 with the cookie banner cropped off. | It is the one live Kaggle competition about knees, and the account has entered it. |
| The old-metrics slide shows the labels' average shares over the six repeated methods (44 / 40 / 14 / 2 and 97 / 3). | The point of the slide is the small number of categories; one bar per metric shows it. |
