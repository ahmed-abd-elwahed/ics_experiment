# Retrieval benchmark report

- Workspace: `results/retrieval_benchmark`
- Judge: `google/gemini-3.5-flash-lite`
- medsim models: `deepseek/deepseek-v4-flash-0731`
- `current`: Europe PMC + LitSense passages, relaxation ladders, lexical rerank (medsim default)
- `current_fixed`: current method, unchanged except that Europe PMC replies without results are retried (they made Europe PMC drop out on 11 of 50 questions in the `current` run)
- `improved_1to4`: changes 1-4: value-first ranking in one list across sources, 50 Europe PMC candidates, animal/age filter, article-body search with excerpts, value-based broadening without the unhelpful rungs
- `improved_1to5`: changes 1-5: improved_1to4 plus natural-language LitSense queries
- `improved_1to6`: changes 1-6: improved_1to5 plus an LLM (the default model) picking the 8 documents from the best 20
- `openrouter_search`: OpenRouter web search server tool (Exa, 8 results, medical domains), lexical rerank
- `openrouter_search_improved`: OpenRouter web search with changes 1-3 applied: 10 results (same $0.007 fee), 3,000-character excerpts, value-first ranking, population filter, excerpts around the variable from Europe PMC full text of PMC hits

## Question sets

- Cases extracted: 70; measured values found: 421; eligible as hidden values: 222.
- Set A (hidden value): 35 questions accepted; rejected 2 (stage_a_answers_from_case: 2).
- Set B (value never stated): 15 questions accepted; rejected 1 (stage_a_answers_from_case: 1).
- Compared: 44 questions on which every method ran retrieval; excluded 6: `A:PMC10373170_01:c_reactive_protein` (current: literature, current_fixed: literature, improved_1to4: literature, improved_1to5: literature, improved_1to6: case_study, openrouter_search: literature, openrouter_search_improved: literature); `A:PMC3625585_01:body_mass_index` (current: case_study, current_fixed: case_study, improved_1to4: case_study, improved_1to5: literature, improved_1to6: literature, openrouter_search: case_study, openrouter_search_improved: literature); `A:PMC5477234_01:weight` (current: literature, current_fixed: case_study, improved_1to4: synthesizer_unanswerable, improved_1to5: synthesizer_unanswerable, improved_1to6: literature, openrouter_search: case_study, openrouter_search_improved: literature); `B:PMC4208417_01:white_cell_count` (current: literature, current_fixed: query_builder_declined, improved_1to4: query_builder_declined, improved_1to5: query_builder_declined, improved_1to6: query_builder_declined, openrouter_search: synthesizer_unanswerable, openrouter_search_improved: query_builder_declined); `B:PMC4333364_01:respiratory_rate` (current: literature, current_fixed: literature, improved_1to4: literature, improved_1to5: synthesizer_unanswerable, improved_1to6: synthesizer_unanswerable, openrouter_search: query_builder_declined, openrouter_search_improved: query_builder_declined); `B:PMC9095982_01:c_reactive_protein` (current: literature, current_fixed: literature, improved_1to4: off_topic, improved_1to5: literature, improved_1to6: literature, openrouter_search: literature, openrouter_search_improved: literature).

## All questions (sets A and B)

| Metric | current | current_fixed | improved_1to4 | improved_1to5 | improved_1to6 | openrouter_search | openrouter_search_improved | current − current_fixed | improved_1to4 − current_fixed | improved_1to5 − current_fixed | improved_1to6 − current_fixed | openrouter_search − current_fixed | openrouter_search_improved − current_fixed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 8.00 [8.00, 8.00] | 8.00 [8.00, 8.00] | 8.00 [8.00, 8.00] | 8.00 [8.00, 8.00] | 8.00 [8.00, 8.00] | 7.66 [7.48, 7.81] | 8.00 [8.00, 8.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | -0.34 [-0.52, -0.19] | +0.00 [+0.00, +0.00] |
| Mean relevance grade (0–3) | 1.29 [1.11, 1.47] | 1.39 [1.23, 1.53] | 1.67 [1.51, 1.83] | 1.64 [1.44, 1.82] | 1.62 [1.43, 1.80] | 1.35 [1.20, 1.50] | 1.59 [1.41, 1.76] | -0.10 [-0.20, +0.01] | +0.28 [+0.12, +0.44] | +0.25 [+0.08, +0.41] | +0.23 [+0.09, +0.38] | -0.04 [-0.17, +0.11] | +0.20 [+0.03, +0.38] |
| Relevant documents (grade ≥ 2), share | 45% [36, 53] | 50% [44, 57] | 63% [56, 71] | 62% [53, 72] | 59% [49, 68] | 35% [28, 42] | 48% [40, 56] | -6 pts [-12, +1] | +13 pts [+6, +21] | +12 pts [+4, +20] | +9 pts [+1, +17] | -15 pts [-22, -8] | -2 pts [-10, +6] |
| Questions with ≥ 1 useful document (usefulness 2) | 68% [53, 82] | 86% [76, 96] | 91% [82, 98] | 89% [79, 98] | 93% [84, 100] | 84% [73, 93] | 86% [75, 95] | -18 pts [-34, -5] | +5 pts [-7, +16] | +2 pts [-9, +14] | +7 pts [-2, +16] | -2 pts [-12, +7] | +0 pts [-11, +11] |
| Useful documents (usefulness 2), share | 21% [15, 27] | 24% [18, 31] | 39% [32, 48] | 41% [32, 49] | 43% [35, 51] | 22% [17, 26] | 33% [26, 40] | -3 pts [-7, +0] | +15 pts [+9, +22] | +16 pts [+9, +24] | +19 pts [+12, +26] | -3 pts [-10, +4] | +9 pts [+1, +16] |
| Questions with ≥ 1 document containing the true value (correctness 2) | 22% [9, 38] | 38% [22, 53] | 53% [38, 69] | 50% [34, 69] | 47% [28, 66] | 41% [25, 59] | 47% [28, 66] | -16 pts [-34, +0] | +16 pts [-3, +34] | +12 pts [-9, +38] | +9 pts [-12, +31] | +3 pts [-16, +22] | +9 pts [-9, +28] |
| Number-giving documents pointing the right way (correctness ≥ 1), share | 60% [43, 76] | 68% [54, 81] | 72% [60, 83] | 70% [58, 81] | 70% [56, 81] | 63% [49, 77] | 65% [52, 77] | -6 pts [-18, +5] | +5 pts [-10, +20] | +3 pts [-9, +15] | +3 pts [-13, +18] | -9 pts [-25, +7] | -2 pts [-21, +16] |
| Questions where most number-giving documents point the right way | 56% [38, 75] | 62% [47, 78] | 69% [50, 84] | 69% [53, 84] | 72% [56, 88] | 44% [28, 59] | 56% [41, 72] | -6 pts [-22, +6] | +6 pts [-16, +28] | +6 pts [-9, +22] | +9 pts [-9, +28] | -19 pts [-38, +0] | -6 pts [-28, +16] |
| Questions answered from literature | 86% [76, 95] | 91% [82, 98] | 91% [80, 100] | 89% [78, 98] | 93% [84, 100] | 82% [70, 93] | 91% [81, 98] | -5 pts [-18, +7] | +0 pts [-9, +9] | -2 pts [-12, +7] | +2 pts [-7, +12] | -9 pts [-23, +4] | +0 pts [-12, +11] |
| Final answer close to the true value | 44% [28, 62] | 47% [31, 66] | 59% [44, 75] | 38% [22, 53] | 47% [28, 62] | 53% [38, 72] | 56% [38, 72] | -3 pts [-16, +9] | +12 pts [-6, +31] | -9 pts [-28, +9] | +0 pts [-19, +19] | +6 pts [-9, +22] | +9 pts [-9, +28] |
| Final answer in the true value's category (low/normal/high) | 84% [72, 97] | 81% [69, 94] | 81% [69, 94] | 78% [62, 91] | 78% [62, 91] | 81% [66, 94] | 78% [62, 91] | +3 pts [-6, +12] | +0 pts [-12, +12] | -3 pts [-12, +6] | -3 pts [-12, +6] | +0 pts [-12, +12] | -3 pts [-12, +6] |
| Retrieval cost per question (search fees, search/rerank LLM; USD) | $0.00000 | $0.00000 | $0.00000 | $0.00000 | $0.00099 | $0.00712 | $0.00714 | +0.00000 [+0.00000, +0.00000] | +0.00000 [+0.00000, +0.00000] | +0.00000 [+0.00000, +0.00000] | +0.00099 [+0.00080, +0.00119] | +0.00712 [+0.00712, +0.00712] | +0.00714 [+0.00713, +0.00714] |
| medsim LLM cost per question (Stages A–C, USD) | $0.00110 | $0.00107 | $0.00076 | $0.00088 | $0.00090 | $0.00084 | $0.00066 | +0.00003 [-0.00020, +0.00029] | -0.00030 [-0.00047, -0.00014] | -0.00019 [-0.00038, -0.00001] | -0.00017 [-0.00036, +0.00002] | -0.00022 [-0.00044, +0.00001] | -0.00040 [-0.00058, -0.00025] |
| Total cost per question (USD) | $0.00110 | $0.00107 | $0.00076 | $0.00088 | $0.00189 | $0.00796 | $0.00780 | +0.00003 [-0.00020, +0.00029] | -0.00030 [-0.00047, -0.00014] | -0.00019 [-0.00038, -0.00001] | +0.00082 [+0.00055, +0.00110] | +0.00690 [+0.00668, +0.00713] | +0.00674 [+0.00655, +0.00689] |
| Wall time per question (s) | 88.1 [71.5, 107.5] | 83.8 [69.7, 97.9] | 86.1 [73.6, 99.6] | 100.2 [82.5, 120.7] | 208.6 [182.2, 236.9] | 87.3 [72.2, 104.4] | 82.1 [68.7, 97.1] | +4.34 [-17.53, +27.93] | +2.39 [-10.94, +17.21] | +16.48 [+0.27, +33.65] | +124.81 [+96.20, +153.07] | +3.50 [-14.29, +23.31] | -1.68 [-17.70, +14.95] |

## Set A only (hidden value; correctness defined)

| Metric | current | current_fixed | improved_1to4 | improved_1to5 | improved_1to6 | openrouter_search | openrouter_search_improved | current − current_fixed | improved_1to4 − current_fixed | improved_1to5 − current_fixed | improved_1to6 − current_fixed | openrouter_search − current_fixed | openrouter_search_improved − current_fixed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 8.00 [8.00, 8.00] | 8.00 [8.00, 8.00] | 8.00 [8.00, 8.00] | 8.00 [8.00, 8.00] | 8.00 [8.00, 8.00] | 7.59 [7.38, 7.78] | 8.00 [8.00, 8.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | -0.41 [-0.62, -0.22] | +0.00 [+0.00, +0.00] |
| Mean relevance grade (0–3) | 1.39 [1.20, 1.56] | 1.45 [1.27, 1.62] | 1.75 [1.56, 1.91] | 1.70 [1.50, 1.91] | 1.68 [1.48, 1.88] | 1.40 [1.23, 1.57] | 1.68 [1.49, 1.86] | -0.06 [-0.17, +0.06] | +0.30 [+0.12, +0.48] | +0.26 [+0.07, +0.45] | +0.24 [+0.06, +0.40] | -0.04 [-0.22, +0.14] | +0.23 [+0.03, +0.45] |
| Relevant documents (grade ≥ 2), share | 50% [41, 58] | 54% [45, 62] | 65% [57, 74] | 64% [54, 75] | 61% [51, 71] | 39% [31, 46] | 52% [43, 61] | -4 pts [-11, +3] | +12 pts [+4, +20] | +11 pts [+1, +20] | +7 pts [-2, +16] | -15 pts [-24, -6] | -2 pts [-12, +10] |
| Questions with ≥ 1 useful document (usefulness 2) | 75% [59, 91] | 88% [75, 97] | 94% [84, 100] | 91% [78, 100] | 94% [84, 100] | 91% [81, 100] | 91% [81, 100] | -12 pts [-28, +3] | +6 pts [-6, +19] | +3 pts [-6, +12] | +6 pts [+0, +16] | +3 pts [-6, +12] | +3 pts [-6, +12] |
| Useful documents (usefulness 2), share | 23% [16, 29] | 25% [18, 32] | 39% [31, 48] | 39% [30, 48] | 43% [34, 53] | 24% [19, 29] | 36% [27, 45] | -2 pts [-7, +3] | +14 pts [+7, +23] | +14 pts [+6, +22] | +18 pts [+12, +26] | -1 pts [-10, +7] | +11 pts [+1, +20] |
| Questions with ≥ 1 document containing the true value (correctness 2) | 22% [9, 38] | 38% [22, 53] | 53% [38, 69] | 50% [34, 69] | 47% [28, 66] | 41% [25, 59] | 47% [28, 66] | -16 pts [-34, +0] | +16 pts [-3, +34] | +12 pts [-9, +38] | +9 pts [-12, +31] | +3 pts [-16, +22] | +9 pts [-9, +28] |
| Number-giving documents pointing the right way (correctness ≥ 1), share | 60% [43, 76] | 68% [54, 81] | 72% [60, 83] | 70% [58, 81] | 70% [56, 81] | 63% [49, 77] | 65% [52, 77] | -6 pts [-18, +5] | +5 pts [-10, +20] | +3 pts [-9, +15] | +3 pts [-13, +18] | -9 pts [-25, +7] | -2 pts [-21, +16] |
| Questions where most number-giving documents point the right way | 56% [38, 75] | 62% [47, 78] | 69% [50, 84] | 69% [53, 84] | 72% [56, 88] | 44% [28, 59] | 56% [41, 72] | -6 pts [-22, +6] | +6 pts [-16, +28] | +6 pts [-9, +22] | +9 pts [-9, +28] | -19 pts [-38, +0] | -6 pts [-28, +16] |
| Questions answered from literature | 97% [91, 100] | 94% [84, 100] | 97% [91, 100] | 94% [84, 100] | 91% [78, 100] | 94% [84, 100] | 94% [84, 100] | +3 pts [-6, +12] | +3 pts [-6, +12] | +0 pts [-9, +9] | -3 pts [-16, +6] | +0 pts [-12, +12] | +0 pts [-9, +9] |
| Final answer close to the true value | 44% [28, 62] | 47% [31, 66] | 59% [44, 75] | 38% [22, 53] | 47% [28, 62] | 53% [38, 72] | 56% [38, 72] | -3 pts [-16, +9] | +12 pts [-6, +31] | -9 pts [-28, +9] | +0 pts [-19, +19] | +6 pts [-9, +22] | +9 pts [-9, +28] |
| Final answer in the true value's category (low/normal/high) | 84% [72, 97] | 81% [69, 94] | 81% [69, 94] | 78% [62, 91] | 78% [62, 91] | 81% [66, 94] | 78% [62, 91] | +3 pts [-6, +12] | +0 pts [-12, +12] | -3 pts [-12, +6] | -3 pts [-12, +6] | +0 pts [-12, +12] | -3 pts [-12, +6] |

## Set B only (value never stated)

| Metric | current | current_fixed | improved_1to4 | improved_1to5 | improved_1to6 | openrouter_search | openrouter_search_improved | current − current_fixed | improved_1to4 − current_fixed | improved_1to5 − current_fixed | improved_1to6 − current_fixed | openrouter_search − current_fixed | openrouter_search_improved − current_fixed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Documents returned per question | 8.00 [8.00, 8.00] | 8.00 [8.00, 8.00] | 8.00 [8.00, 8.00] | 8.00 [8.00, 8.00] | 8.00 [8.00, 8.00] | 7.83 [7.58, 8.00] | 8.00 [8.00, 8.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | +0.00 [+0.00, +0.00] | -0.17 [-0.42, +0.00] | +0.00 [+0.00, +0.00] |
| Mean relevance grade (0–3) | 1.04 [0.67, 1.47] | 1.24 [0.98, 1.51] | 1.47 [1.10, 1.81] | 1.46 [1.08, 1.81] | 1.46 [1.10, 1.81] | 1.22 [0.93, 1.52] | 1.36 [1.02, 1.73] | -0.20 [-0.40, +0.01] | +0.23 [-0.10, +0.59] | +0.22 [-0.04, +0.50] | +0.22 [-0.02, +0.51] | -0.02 [-0.21, +0.15] | +0.12 [-0.14, +0.35] |
| Relevant documents (grade ≥ 2), share | 31% [14, 51] | 42% [32, 51] | 58% [41, 74] | 56% [40, 71] | 54% [35, 74] | 27% [14, 43] | 38% [20, 55] | -10 pts [-22, +1] | +17 pts [+2, +32] | +15 pts [+2, +28] | +12 pts [-4, +31] | -15 pts [-24, -5] | -4 pts [-16, +7] |
| Questions with ≥ 1 useful document (usefulness 2) | 50% [17, 75] | 83% [58, 100] | 83% [58, 100] | 83% [58, 100] | 92% [75, 100] | 67% [42, 92] | 75% [50, 92] | -33 pts [-67, -8] | +0 pts [-25, +25] | +0 pts [-33, +33] | +8 pts [-25, +33] | -17 pts [-42, +0] | -8 pts [-33, +17] |
| Useful documents (usefulness 2), share | 16% [4, 30] | 22% [10, 35] | 40% [23, 55] | 45% [30, 59] | 43% [25, 61] | 16% [8, 25] | 25% [11, 40] | -6 pts [-9, -3] | +18 pts [+6, +31] | +23 pts [+8, +38] | +21 pts [+6, +39] | -6 pts [-17, +1] | +3 pts [-5, +11] |
| Questions answered from literature | 58% [33, 83] | 83% [58, 100] | 75% [50, 100] | 75% [50, 100] | 100% [100, 100] | 50% [25, 75] | 83% [58, 100] | -25 pts [-58, +8] | -8 pts [-25, +0] | -8 pts [-33, +17] | +17 pts [+0, +42] | -33 pts [-67, +0] | +0 pts [-33, +33] |

## Cost

All runs, including the excluded questions (their calls were paid for).

| Method | Questions | Retrieval (search fees + search model) | medsim LLM (Stages A–C) | Total | Total per question | Median wall time |
|---|---|---|---|---|---|---|
| current | 50 | $0.0000 | $0.0541 | $0.0541 | $0.00108 | 60.6 s |
| current_fixed | 50 | $0.0000 | $0.0499 | $0.0499 | $0.00100 | 67.6 s |
| improved_1to4 | 50 | $0.0000 | $0.0465 | $0.0465 | $0.00093 | 69.6 s |
| improved_1to5 | 50 | $0.0000 | $0.0443 | $0.0443 | $0.00089 | 83.8 s |
| improved_1to6 | 50 | $0.0457 | $0.0433 | $0.0889 | $0.00178 | 180.6 s |
| openrouter_search | 50 | $0.3346 | $0.0404 | $0.3750 | $0.00750 | 61.4 s |
| openrouter_search_improved | 50 | $0.3426 | $0.0343 | $0.3770 | $0.00754 | 72.5 s |

## By subgroup (set A)

### Variable category

| Group | n | Questions with ≥ 1 useful document (usefulness 2) — current | Questions with ≥ 1 useful document (usefulness 2) — current_fixed | Questions with ≥ 1 useful document (usefulness 2) — improved_1to4 | Questions with ≥ 1 useful document (usefulness 2) — improved_1to5 | Questions with ≥ 1 useful document (usefulness 2) — improved_1to6 | Questions with ≥ 1 useful document (usefulness 2) — openrouter_search | Questions with ≥ 1 useful document (usefulness 2) — openrouter_search_improved | Questions with ≥ 1 document containing the true value (correctness 2) — current | Questions with ≥ 1 document containing the true value (correctness 2) — current_fixed | Questions with ≥ 1 document containing the true value (correctness 2) — improved_1to4 | Questions with ≥ 1 document containing the true value (correctness 2) — improved_1to5 | Questions with ≥ 1 document containing the true value (correctness 2) — improved_1to6 | Questions with ≥ 1 document containing the true value (correctness 2) — openrouter_search | Questions with ≥ 1 document containing the true value (correctness 2) — openrouter_search_improved |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| anthropometric | 5 | 80% | 80% | 100% | 80% | 80% | 80% | 80% | 20% | 60% | 60% | 60% | 20% | 40% | 60% |
| laboratory | 13 | 85% | 85% | 92% | 92% | 100% | 92% | 92% | 23% | 31% | 54% | 46% | 69% | 54% | 46% |
| vital_sign | 14 | 64% | 93% | 93% | 93% | 93% | 93% | 93% | 21% | 36% | 50% | 50% | 36% | 29% | 43% |

### True value (judge's category)

| Group | n | Questions with ≥ 1 useful document (usefulness 2) — current | Questions with ≥ 1 useful document (usefulness 2) — current_fixed | Questions with ≥ 1 useful document (usefulness 2) — improved_1to4 | Questions with ≥ 1 useful document (usefulness 2) — improved_1to5 | Questions with ≥ 1 useful document (usefulness 2) — improved_1to6 | Questions with ≥ 1 useful document (usefulness 2) — openrouter_search | Questions with ≥ 1 useful document (usefulness 2) — openrouter_search_improved | Questions with ≥ 1 document containing the true value (correctness 2) — current | Questions with ≥ 1 document containing the true value (correctness 2) — current_fixed | Questions with ≥ 1 document containing the true value (correctness 2) — improved_1to4 | Questions with ≥ 1 document containing the true value (correctness 2) — improved_1to5 | Questions with ≥ 1 document containing the true value (correctness 2) — improved_1to6 | Questions with ≥ 1 document containing the true value (correctness 2) — openrouter_search | Questions with ≥ 1 document containing the true value (correctness 2) — openrouter_search_improved |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| high | 16 | 73% | 73% | 93% | 87% | 88% | 92% | 86% | 20% | 27% | 47% | 20% | 38% | 31% | 29% |
| low | 9 | 78% | 100% | 100% | 89% | 100% | 100% | 100% | 33% | 44% | 44% | 67% | 38% | 33% | 44% |
| normal | 8 | 75% | 100% | 88% | 100% | 100% | 100% | 100% | 12% | 50% | 75% | 88% | 75% | 75% | 88% |
| unknown | 2 | – | – | – | – | – | 0% | 0% | – | – | – | – | – | 0% | 0% |

### Variable typical of the diagnosis

| Group | n | Questions with ≥ 1 useful document (usefulness 2) — current | Questions with ≥ 1 useful document (usefulness 2) — current_fixed | Questions with ≥ 1 useful document (usefulness 2) — improved_1to4 | Questions with ≥ 1 useful document (usefulness 2) — improved_1to5 | Questions with ≥ 1 useful document (usefulness 2) — improved_1to6 | Questions with ≥ 1 useful document (usefulness 2) — openrouter_search | Questions with ≥ 1 useful document (usefulness 2) — openrouter_search_improved | Questions with ≥ 1 document containing the true value (correctness 2) — current | Questions with ≥ 1 document containing the true value (correctness 2) — current_fixed | Questions with ≥ 1 document containing the true value (correctness 2) — improved_1to4 | Questions with ≥ 1 document containing the true value (correctness 2) — improved_1to5 | Questions with ≥ 1 document containing the true value (correctness 2) — improved_1to6 | Questions with ≥ 1 document containing the true value (correctness 2) — openrouter_search | Questions with ≥ 1 document containing the true value (correctness 2) — openrouter_search_improved |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| no | 19 | 63% | 84% | 89% | 84% | 89% | 84% | 84% | 11% | 37% | 58% | 53% | 42% | 37% | 42% |
| yes | 13 | 92% | 92% | 100% | 100% | 100% | 100% | 100% | 38% | 38% | 46% | 46% | 54% | 46% | 54% |

### Documents by source

| Source | Documents judged | Mean relevance | Relevant (≥ 2) | Useful (= 2) |
|---|---|---|---|---|
| europe_pmc | 1069 | 1.63 | 63% | 41% |
| litsense | 691 | 1.35 | 45% | 22% |
| openrouter_search | 689 | 1.47 | 42% | 27% |

## Diagnostics

- **current:** answer paths {'synthesizer_unanswerable': 6, 'literature': 38}; source article removed for 7 question(s); 0 document(s) without a judgment.
- **current_fixed:** answer paths {'literature': 40, 'synthesizer_unanswerable': 4}; source article removed for 7 question(s); 0 document(s) without a judgment.
- **improved_1to4:** answer paths {'literature': 40, 'synthesizer_unanswerable': 4}; source article removed for 7 question(s); 0 document(s) without a judgment.
- **improved_1to5:** answer paths {'literature': 39, 'synthesizer_unanswerable': 5}; source article removed for 9 question(s); 0 document(s) without a judgment.
- **improved_1to6:** answer paths {'literature': 41, 'synthesizer_unanswerable': 3}; source article removed for 12 question(s); 0 document(s) without a judgment.
- **openrouter_search:** answer paths {'literature': 36, 'synthesizer_unanswerable': 8}; source article removed for 8 question(s); 0 document(s) without a judgment.
- **openrouter_search_improved:** answer paths {'literature': 40, 'synthesizer_unanswerable': 4}; source article removed for 8 question(s); 0 document(s) without a judgment.
- **Quote check:** 19 of 2029 pass-1 judgments quoted text that is not in the document (usefulness forced to 0).
- **Pass 2:** 144 of 682 verdicts were "not comparable" (excluded from correctness).
- **Judge errors (all attempts):** 0 pass-1 call(s) failed.

## Judge validation

| Control document | Expected | Passed |
|---|---|---|
| far_range | usefulness 2, correctness 0 or 1 | 10/10 |
| off_topic | relevance 0, usefulness 0 | 10/10 |
| positive | relevance 3, usefulness 2, correctness 2 | 7/10 |
| veterinary | relevance 0, usefulness 0 | 10/10 |

- **Flipped true value:** after moving the true value far away, 6 of 10 "within" verdicts changed. An unchanged verdict is not always an error: when a document reports a wide range, the moved value can still be inside it (see validate/flips.jsonl).
- **Second judge (qwen/qwen3.8-flash), 76 documents:** quadratic-weighted κ = 0.79 for relevance, 0.79 for usefulness.
- **Second judge, correctness verdicts (20 documents):** 10/20 identical, Cohen's κ = 0.33.

## Benchmark spend

| Step | Cost (USD, OpenRouter usage.cost) |
|---|---|
| extract (case facts) | $0.0940 |
| redact + Stage A checks (accepted) | $0.0506 |
| redact + Stage A checks (rejected) | $0.0027 |
| run (all methods; search fees included) | $1.0357 |
| judge pass 1 | $1.1669 |
| judge pass 2 | $0.3451 |
| judge answer check | $0.0817 |
| validation: controls | $0.0303 |
| validation: flipped truth | $0.0055 |
| validation: second judge, pass 1 | $0.0698 |
| validation: second judge, pass 2 | $0.0139 |
| **total** | **$2.8963** |

Cross-check: the OpenRouter key's usage counter, read right after each of the 25 benchmark commands, rose by $2.5927. The counter lags behind requests, so this undercounts; per-call usage.cost above is the accounting source.

