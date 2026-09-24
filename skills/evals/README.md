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
| `hand_evals.json` | seven prompts with the data inline, tagged with their hand-drawability tier (A: hbar ranking, grouped hbar, sparkline, vbar, diverging hbar; B: line; C: pie) |
| `hand_grade.py` | `python hand_grade.py <run_dir> <eval_name>` → `grading.json`, same format as `grade.py` |

What it checks — the ways hand-drawn charts go wrong: bar lengths and column heights within one cell of
`round(v / max × longest)`; a framed chart rectangular **in display columns**; only font-safe glyphs
(ASCII, Latin-1, WGL4 box drawing, shades, half blocks, markers); series that can be told apart; the
diverging bars sharing one zero line; sparkline ticks in value order with the extremes at `▁` and `█`;
the line chart's axis from the maximum to the minimum; correct percentages, and a pie (or its 100% stacked
bar substitute) in proportion. `python/tests/test_hand_grader.py` checks the grader itself: the renderer's own
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
