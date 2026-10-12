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
