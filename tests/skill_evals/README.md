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
