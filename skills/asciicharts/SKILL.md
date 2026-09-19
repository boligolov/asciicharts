---
name: asciicharts
description: Use this skill to turn a handful of numbers, or a CSV file, into a plain-text chart (Unicode/ASCII) pasted right into the reply — bar, line, area, sparkline, histogram, pie, heatmap, boxplot, scatter, dot plot. Trigger on any request to plot, chart, graph, visualize or draw a histogram or distribution of numbers the user gives inline or in a file, e.g. "quick histogram of these response times", rankings, trends over time, shares of a whole, benchmark results, "top N by X", and whenever a chart would help in a terminal, README, commit message, PR description or code comment, even if the user never says "chart". A dependency-free Python script renders it, so prefer it to describing numbers in prose or hand-drawing ASCII bars. Not for PNG/SVG/image files, interactive dashboards, or plotting-library code (matplotlib, seaborn, pandas), explanations of chart concepts, or stats calculations without a chart. Also use when an `asciicharts` MCP server is connected.
license: MIT
compatibility: Needs Python 3 on PATH (standard library only, nothing to install).
---

# asciicharts

`scripts/asciicharts.py` turns numbers into a text chart you paste into your reply inside a fenced
code block. It exists because hand-drawn charts are almost always misaligned or wrong, and a table
of numbers hides the shape that a bar or a trend line shows at a glance.

Run it from this skill's directory, or with the full path (`python3` if `python` isn't found).
Everything below prints the chart to stdout; problems go to stderr with exit code 1 and a
one-line message that says what to fix.

## Quick start

From data you already have, as a JSON spec on stdin (avoids shell-quoting trouble, especially on Windows):

```sh
echo '{"chartType":"hbar","title":"Browser share","labels":["Chrome","Firefox","Safari"],"series":[{"values":[62,21,12]}]}' | python scripts/asciicharts.py -
```

From a CSV file, no JSON needed (see [From a CSV](#from-a-csv)):

```sh
python scripts/asciicharts.py --csv latency.csv --chart hbar --values p99 --sort -p99 --limit 3 --set title="Slowest endpoints, p99 ms"
```

```
┌───────────────────────────────────────────────────────────┐
│                 Slowest endpoints, p99 ms                 │
├───────────────────────────────────────────────────────────┤
│ /upload   │ ████████████████████████████████████████ 4200 │
│ /search   │ ██████████████████                       1900 │
│ /checkout │ █████████                                950  │
└───────────────────────────────────────────────────────────┘
```

As a library: `from asciicharts import render_chart` (raises `ChartError`, a `ValueError`, on bad input).
If an MCP server named `asciicharts` is connected, its `render_chart` tool takes the same fields and
its `list_charts` tool returns the catalogue below.

## Workflow

1. **Pick the chart** for the question being asked (table below).
2. **Build the input** — a CSV command if the data is in a file, otherwise a JSON spec. Not sure how to shape `series`? `python scripts/asciicharts.py --list` prints every chart with what it draws, how to fill `series`, its options and a working example.
3. **Run it.** If it errors, read the message and fix the input; the messages name the column, row or field at fault.
4. **Paste the chart in a code block** and add a sentence on what it shows. The chart is monospaced art and only lines up in a monospaced font.
5. **Check it against the data**: bar lengths and printed numbers should match what you were given.

## Pick the chart

| the question | chart | how the data goes in |
|---|---|---|
| how does one metric trend, inline in a sentence | `sparkline` | one series of values |
| which is biggest / a ranking / one value per category | `hbar` (long names) or `vbar` | one series + `labels` |
| several measures per category, or parts of a whole | grouped `hbar`/`vbar`, or `"stacked": true` | one series per measure + `labels` |
| how does it change over time | `line` (precise) or `area` (volume) | series of values, `labels` = x axis |
| two series on different scales | `dual_axis` | exactly two series |
| relationship between two numbers | `scatter` | `points`: `{x, y}` |
| shares of a whole | `pie`, or a stacked `hbar` (easier to compare) | one series per slice |
| how are raw values distributed | `histogram` (`bins`) or `boxplot` per group | raw samples, not pre-bucketed |
| a grid of values | `heatmap` | one series per row, `labels` = columns |
| values against a target or each other, axis not starting at 0 | `dotplot`, or `line` + `threshold` | like `hbar` |

Pass raw samples to `histogram` and `boxplot` — they compute the bins and quartiles themselves.
Negative values work everywhere: bars and areas grow both ways from a zero line, stacked ones too.

## From a CSV

`--csv FILE` (or `-` for stdin) plus `--chart TYPE`. The first row must be the header. The delimiter
(`,` `;` tab `|`) is detected, and numbers may carry `$`, `%`, thousands separators or a decimal comma.

| flag | meaning |
|---|---|
| `--label COL` | column that names the rows/categories (the x column for `scatter`). Default: the first text column |
| `--values COLS` | comma-separated columns to plot. Default: every numeric column |
| `--sort COL` | sort rows; `-COL` or `COL:desc` for descending |
| `--limit N` | keep the first N rows, after sorting — this is how you get "top N" |
| `--set KEY=VALUE` | any chart option: `title=…`, `border=none`, `width=60`, `stacked=true` (repeatable) |
| `--print-spec` | print the JSON spec instead of the chart, to tweak and rerun |

Columns can be given by name (case-insensitive), by a unique prefix (`p99` finds `p99_ms`) or as 1-based numbers. How rows become chart parts depends
on the chart: bars, lines and areas make each value column a series with the label column as categories;
`pie` makes one slice per row; `heatmap` makes one matrix row per CSV row; `scatter` plots each value
column against the label (x) column. Rows that don't parse (`n/a`, empty cells) are reported by row and
column instead of being dropped silently — clean or filter the file first, or pick other `--values`.

## The spec

Required: `chartType`, `series` (each `{name, values}` or `{name, points}`). Optional, the ones you'll
use most: `title`, `labels`, `border` (`none` is the most compact), `width`/`height` (max 500/200),
`stacked`, `style`, `threshold`, `showPoints`, `bins`. Every option, the limits and the error
messages are in [references/reference.md](references/reference.md); every chart rendered, with the
spec that made it, is in [references/gallery.md](references/gallery.md) — look there to choose a style.

## Making it read well

- **Use `"style": "ascii"` when you don't know where the text will be shown.** Default bars use only whole `█` blocks and series use glyphs that even Consolas has, so charts are safe in nearly every font; only `"style": "fine"` bars and sparklines use eighth blocks that some default editor fonts lack, which then substitute them and make the right edge look ragged. The `ascii` style (bars, histogram, area and line charts) draws with plain `# X H W = : | .` — 23 distinct characters, so even a dozen series stay distinguishable — with `|` separators and `+` axis ticks; add `"border": "ascii"` and the whole chart, frame included, is pure ASCII.
- **Keep it around 60–80 columns** for chat, commit messages and PR text; the default widths already fit.
- **Sort and trim before plotting.** A ranking of 40 bars is unreadable; `--sort -x --limit 10` (or sort in your own code) says more than all of them.
- **Label things.** A `title` and named series cost nothing and remove the guessing; legends appear automatically for several series.
- **Whole numbers print without decimals, others with two.** Round or scale (thousands, ms→s) yourself if the raw values are noisy.

## Not the right tool

The user needs an image file (PNG/SVG/PDF), an interactive or zoomable chart, or thousands of points
where the fine detail matters — use a plotting library for those. For a long series that only needs
its shape, aggregate first (per hour, per day) or use a `sparkline`.
