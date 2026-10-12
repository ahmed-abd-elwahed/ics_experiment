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
