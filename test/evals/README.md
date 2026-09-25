# Skill evals

Realistic prompts for the skill, graded programmatically (`grade.py`), run once with the skill and once
without it (baseline) by independent agents. Not part of `pytest`; they need an agent to execute the prompts.

| file | what |
|---|---|
| `evals.json` | the five prompts (`{INPUT}` = folder holding the CSV files) |
| `api_latency.csv`, `market_share.csv` | input data; the second one is deliberately dirty (`$4,820,000`, `n/a`, empty cells) |
| `grade.py` | `python grade.py <run_dir> <eval_name>` reads `outputs/reply.md`, writes `grading.json` |
| `trigger_eval.json` | 20 queries (10 should trigger the skill, 10 near-misses) for description optimisation |

Prompts: top-8 slowest endpoints from a CSV for a PR; a 12-month trend for a README; a font-safe two-year
comparison for a plain-text email; stacked inflows with refunds hanging below zero for a commit message; a pie
chart from the dirty CSV for Slack.

## Hand-drawn evals (no script)

The skill's main path is drawing a chart **by hand** from `references/drawing.md`, so this second set
forbids running anything: each prompt in `hand_evals.json` is followed at run time by *"You cannot run
any code, scripts or tools for this; write the chart yourself. Save your final reply … to {OUT}/reply.md."*

| file | what |
|---|---|
| `hand_evals.json` | eleven prompts with the data inline, tagged with their hand-drawability tier (A: hbar ranking, grouped hbar, sparkline, vbar, diverging hbar; B: line, 14 ranked bars in a requested frame, stacked bars with negatives, CJK labels in a frame; C: pie, a 14-point line 12 rows tall) |
| `hand_grade.py` | `python hand_grade.py <run_dir> <eval_name>` → `grading.json`, same format as `grade.py` |

What it checks — the ways hand-drawn charts go wrong: bar lengths and column heights within one cell of
`round(v / max × longest)`; a framed chart rectangular **in display columns**; only font-safe glyphs
(ASCII, Latin-1, WGL4 box drawing, shades, half blocks, markers); series that can be told apart; the
diverging bars sharing one zero line (in stacked bars: every month's zero in the same column, and the
two income segments in two glyphs); sparkline ticks in value order with the extremes at `▁` and `█`;
the line chart's axis from the maximum to the minimum; correct percentages, and a pie (or its 100% stacked
bar substitute) in proportion. `test/test_hand_grader.py` checks the grader itself: the renderer's own
chart for each prompt passes everything, and each typical mistake fails the check meant to catch it.

### Hand-drawn results (2026-09-24, one run per configuration, the same model for both)

| eval | tier | with skill | without skill |
|---|---|---|---|
| hand-hbar-ranking | A | 6/6 | 6/6 |
| hand-hbar-grouped | A | 7/7 | 7/7 |
| hand-sparkline | A | 3/3 | 3/3 |
| hand-vbar | A | 5/5 | 5/5 |
| hand-diverging | A | 6/6 | 6/6 |
| hand-line | B | 5/5 | 5/5 |
| hand-pie | C | 5/5 | 5/5 |
| **total** | | **37/37** | **37/37** |

What this run showed:

- **A strong model draws small charts correctly without the skill.** Every baseline chart was right; on
  correctness the skill made no difference at this size. The skill is not what makes simple hand-drawn
  charts correct for a capable model — its measurable effects are elsewhere:
  - **smaller, denser charts** (the chart blocks were 21–38 columns wide with the skill, 28–76 without;
    e.g. a 57-cell bar without it), as the "keep it small" rule asks;
  - **tier C routed as designed**: with the skill the pie became a 100% stacked bar, said so, and kept the
    3% slice (the baseline drew a true 21-row pie, which was also right);
  - **visible self-checking**: one skilled agent's self-check caught two rows off by a column and fixed them;
  - a cost of roughly **+40% tokens** (≈ 47k vs 33k per task) for reading the skill.
- **The first grader was wrong, not the baseline.** It failed four correct baseline charts because they
  weren't laid out like the renderer's (no separator, `░` as a series, a value axis with values above the
  columns, the zero axis as the only vertical line). The grader now reads rows by label and bars by glyph;
  those four replies are kept in `formats/` as test fixtures.
- **A contradiction in the skill**, found by a skilled agent: "one glyph per series" versus the grouped
  example drawing both years with `█`. The rule now says what it means: series must be told apart without
  color — by glyph and legend, or by naming the series on every row.
- The 14 raw replies and their gradings are kept in `runs/2026-09-24-hand/` — also as a catalogue of
  the layouts agents invent on their own.
- Still open: whether the principles help **weaker models** and **harder charts** (more bars, stacked with
  negatives, frames, CJK labels) — where counting errors are likely. That is the next test (roadmap 1.6).

### Hand-drawn results, 1.6 (2026-09-24): a weaker model, harder charts

Haiku on all eleven prompts, and the model of run 1.5 ("strong") on the four new harder ones — with and
without the skill, one run per configuration, independent agents that could not run code.

| eval | tier | Haiku with skill | Haiku without | strong with skill | strong without |
|---|---|---|---|---|---|
| hand-hbar-ranking | A | 6/6 | 5/6 | | |
| hand-hbar-grouped | A | 7/7 | 6/7 | | |
| hand-sparkline | A | 3/3 | 3/3 | | |
| hand-vbar | A | 5/5 | 3/5 | | |
| hand-diverging | A | 5/6 | 5/6 | | |
| hand-line | B | 5/5 | 4/5 | | |
| hand-pie | C | 4/5 | 2/5 | | |
| hand-hbar-many (14 bars, framed) | B | 6/7 | 4/7 | 7/7 | 7/7 |
| hand-stacked-negative | B | 6/8 | 4/8 | 8/8 | 8/8 |
| hand-cjk-framed | B | 6/7 | 5/7 | 7/7 | 7/7 |
| hand-line-large (14 points, 12 rows) | C | 6/7 | 4/7 | 7/7 | 6/7 |
| **total** | | **59/66 (89%)** | **45/66 (68%)** | **29/29** | **28/29** |

Tokens per task (mean): Haiku 51k with the skill, 30k without; strong 79k with, 34k without.

What this run showed:

- **For a weaker model the skill is worth about twenty points of correctness**: 89% against 68% overall,
  83% against 59% on the four harder prompts, 95% against 76% on the seven of run 1.5.
  Where the difference came from:
  - **The code block.** Without the skill, Haiku left the chart outside a fenced block in 6 of 11
    replies (so a chat client would re-flow it). With the skill: once.
  - **Lengths.** Without the skill, Haiku miscounted bars in 3 of the 6 bar charts it drew by eye
    (`197` drawn as 21 cells where 19 were right; `38` as 31 for 29; Q1's `18` drawn to the 25 row).
    With the skill, one length in about fifty was wrong (a stacked `49` drawn 19 cells for 23).
  - **Scales from the data.** Without the skill, Haiku's line axes ran 5–15 and 15–70 for data of 6–14 and
    29–64. With it, both line axes ran from the maximum to the minimum, as the principles say.
  - **Tier C routing.** With the skill the pie became a proportional 100% stacked bar. Without it Haiku
    drew arcs (`╯╰╱╲`, not in the font-safe set) that were not in proportion.
- **What the skill does not fix for a weaker model is column counting.** Five of its seven failures with
  the skill are one column off, or a ragged edge (the other two: a missing code block, one miscounted
  segment): a diverging zero axis one column off in one row; a
  stacked chart's zero one column off in one month; a frame broken by the one label longer than the rest
  (`notifications`); a CJK frame with Japanese labels padded by characters rather than columns; a
  12 × 40 line whose peak and low sit at the wrong days. The drawing guide's self-check asked for
  straight frames and aligned separators but not for these two cases. It now also asks that the zero
  axis be in the same column on every row (count what is left of it), and that CJK and emoji count as
  two columns.
- **A strong model draws even the harder charts right without the skill** (28/29; the one miss is a
  line axis rounded to 63–30 for data of 64–29, which is closer to style than to error). The skill's
  effect on it stays what run 1.5 found: smaller charts, visible working, tier routing — at more than
  twice the tokens.
- **A finding for the principles, not the model.** The renderer draws stacked bars with negatives with
  no zero line at all (the zero is only where the glyphs change), while §4.5 says the zero line of a
  diverging chart is an axis that "stays visible on every row". The strong agent with the skill noticed
  this and drew `¦` because the prompt asked for a zero line. The grader accepts both forms; which one
  the principles want is a decision for their next version.
- **The grader was wrong three times before the models were**, and each fix is now a test in
  `test/test_hand_grader.py`: a chart outside a code block made every later check fail with zeros
  (now only the fence check fails); numbered rows (`1. auth`) and `░` used as a named series were not
  read; and a blank line counted as a frame corner, because `"" in "┌╭╔┏"` is true in Python. Its glyph
  check also now allows letters of any script (Japanese titles) and the rest of WGL4 for text (`← → − ≈`).
  Re-graded, the replies of run 1.5 still score 37/37 each.
- The 30 raw replies and their gradings are in `runs/2026-09-24-hand-1.6/`.

## Results (one run per configuration, so read the numbers as indicative)

| | pass rate, with skill | pass rate, without | tokens (with / without) | time (with / without) |
|---|---|---|---|---|
| iteration 1 (first version) | 94% (17/18) | 100% (18/18) | — | — |
| iteration 2 (after the fixes below) | **100% (31/31)** | 96% (30/31) | 36.2k / 32.7k | 27s / 25s |

What the evals showed, and what was changed because of it:

- The baseline agent is already good at simple charts (it writes a throw-away script), so on easy prompts the
  skill's advantage is small; it costs ~10% more tokens. Its value is consistency (correct scaling, alignment,
  legends, stacked/negative layouts, dirty CSV parsing) and not re-inventing that each time.
- The one skill failure in iteration 1 was a renderer defect: the first and last x-axis labels were clipped
  (`Jan` printed as `an`), and labels crowded into each other. Fixed: labels stay inside the plot and colliding
  ones are dropped.
- With `style: "ascii"` an agent still had to post-process the output with `sed` because `│` and `┤` slipped
  through. Fixed: `ascii` style is now pure ASCII (`|` separators, `+` axis ticks), including for line charts.
- An agent's `--values p99` failed because the column was `p99_ms`. Fixed: CSV columns match by unique prefix.

The trigger description was optimised with the skill-creator loop (60/40 train/test split, 3 runs per query):
the original scored 11/12 train and 7/8 held-out; the adopted version scored 11/12 and 8/8. The difference is
one query, i.e. within noise.
