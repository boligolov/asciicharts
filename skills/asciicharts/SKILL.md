---
name: asciicharts
description: Use this skill to draw a chart out of text characters (Unicode/ASCII) in the reply — bar, line, area, sparkline, histogram, pie, heatmap, boxplot, scatter, dot plot — from numbers given inline, a CSV file, or an ExCSV file's own #chart suggestion. Trigger on any request to plot, chart, graph, visualize or draw a histogram or distribution of numbers, e.g. "quick histogram of these response times", rankings, trends over time, shares of a whole, benchmark results, "top N by X", and whenever a chart would help in a terminal, README, commit message, PR description or code comment, even if the user never says "chart". It teaches drawing such charts correctly by hand and uses an exact renderer when available (MCP server, asciicharts command or bundled Python script), so prefer it to describing numbers in prose or eyeballing ASCII bars. Not for PNG/SVG/image files, interactive dashboards, plotting-library code (matplotlib, seaborn, pandas), explanations of chart concepts, or stats calculations without a chart.
license: MIT
compatibility: Works without any tool (the charts are drawn by hand from references/drawing.md); a connected asciicharts MCP server, the asciicharts command (a single binary), or Python 3 (standard library only) makes them exact.
---

# asciicharts

A chart made of text characters shows the shape of numbers where images can't go: chat replies, terminals,
commit messages, PR descriptions, code comments, logs. This skill is the know-how to draw one **right** —
lengths that match the values, frames that stay straight in any font, series you can tell apart without
color — either by hand or with an exact renderer.

Hand-drawn text charts usually go wrong in one way: characters are eyeballed, not counted. Everything
here is about not doing that.

## Workflow

1. **Pick the chart** for the question (table below).
2. **Pick how to draw it**, first match wins:
   - an MCP server named `asciicharts` is connected → its `render_chart` tool (same fields as the JSON
     spec below; `list_charts` returns the catalogue);
   - you can run commands and `asciicharts --version` works → the `asciicharts` command (a single
     binary, nothing else needed): the same arguments and output as the script below — replace
     `python scripts/asciicharts.py` with `asciicharts` — except ExCSV files, which only the script reads;
   - you can run commands and have Python 3 → `scripts/asciicharts.py` from this skill (see
     [With the script](#with-the-script));
   - otherwise → **draw it by hand** with [references/drawing.md](references/drawing.md). Its tier tells
     you what is safe to draw by hand; for tier C (pie, dual_axis, anything large) draw the simpler
     equivalent it gives and say so.
3. **Draw or render it.** By hand: compute the table of lengths first, then build each row from counted
   runs of glyphs. With a tool: if it reports an error, the one-line message says what to fix.
4. **Check it** against the data: the self-check at the end of `drawing.md` for a hand-drawn chart;
   printed values and bar lengths against the numbers you were given for a rendered one.
5. **Answer with the chart in a fenced code block** and a sentence on what it shows. Outside a code block
   the alignment is lost.

## Pick the chart

| the question | chart | by hand |
|---|---|---|
| how does one metric trend, inline in a sentence | `sparkline` | A |
| which is biggest / a ranking / one value per category | `hbar` (long names) or `vbar` | A |
| several measures per category, or parts of a whole | grouped `hbar`/`vbar`, or `"stacked": true` | A |
| close values where zero doesn't matter; values against each other | `dotplot` | A |
| how does it change over time | `line` (precise) or `area` (volume) | B |
| how are raw values distributed | `histogram` (`bins`) or `boxplot` per group | B |
| a grid of values (hour × weekday) | `heatmap` | B |
| relationship between two numbers | `scatter` (`points`: `{x, y}`) | B, a few points |
| shares of a whole | `pie` — or a 100% stacked `hbar`, easier to compare | C (use the stacked bar) |
| two series on different scales | `dual_axis` | C (two small line charts) |
| values against a target | `line` + `thresholds` (labelled reference lines) | B |

**By hand**: A — draw it; B — draw it small (plot ≤ 20 × 6) and check every number; C — use a tool, or
draw the equivalent in brackets.

Pass raw samples to `histogram` and `boxplot` (the tool computes bins and quartiles; by hand, compute them
first as `drawing.md` shows). Negative values work everywhere: bars and areas grow both ways from a zero
line.

## The rules that make a text chart right

The full reasoning is in [references/principles.md](references/principles.md); the glyphs in
[references/glyphs.md](references/glyphs.md). The ones you apply every time:

- **Compute lengths, don't eyeball them**: `cells = round(v / max × W)`, rounding half away from zero.
  A non-zero value gets at least one cell; zero gets none.
- **Bars start at zero** (or grow both ways from a marked zero axis). Lines and dot plots may zoom in —
  then print the range.
- **Only font-safe glyphs**: `█ ▓ ▒ ░ ▌ ▄ ▐ ▀`, light box lines `─ │ ┌ ┐ └ ┘ ├ ┤`, markers `● ○ ▲ ■`.
  A glyph the reader's font lacks is drawn from another font and breaks the alignment. When you don't
  know where the text will be shown, use plain ASCII.
- **Series must be told apart without color**: one glyph per series, the densest first, and a legend
  with the exact glyph (`█ 2025   ▓ 2026`) — or, where every bar row names its own series (grouped
  hbar), the same `█` for all of them.
- **Print the numbers** where the grid is approximate: after each bar, in the legend, as axis labels.
- **Keep it small**: 60–80 columns in total; by hand, bars of 10–20 cells.
- **Every line the same width.** Pad labels to the longest one; count CJK characters and most emoji as
  two columns. A frame is optional — its right border is the first place a miscount shows.

## With the script

`scripts/asciicharts.py` is one file, standard library only. Run it from this skill's directory or with
its full path (`python3` if `python` isn't found). It prints the chart to stdout; problems go to stderr
with exit code 1 and a one-line message that says what to fix. The `asciicharts` command (the Go build,
from github.com/boligolov/asciicharts releases) takes the same arguments and prints the same bytes.

From data you already have, as a JSON spec on stdin (avoids shell-quoting trouble, especially on Windows):

```sh
echo '{"chartType":"hbar","title":"Browser share","labels":["Chrome","Firefox","Safari"],"series":[{"values":[62,21,12]}]}' | python scripts/asciicharts.py -
```

From a CSV file, no JSON needed (see [From a CSV](#from-a-csv), or [From an ExCSV file](#from-an-excsv-file) if the file starts with `#!excsv`):

```sh
python scripts/asciicharts.py --csv latency.csv --chart hbar --values p99 --sort -p99 --limit 3 --set title="Slowest endpoints, p99 ms"
```

```
┌───────────────────────────────────────────────────────────┐
│                 Slowest endpoints, p99 ms                 │
├───────────────────────────────────────────────────────────┤
│ /upload   │ ████████████████████████████████████████ 4200 │
│ /search   │ ██████████████████░░░░░░░░░░░░░░░░░░░░░░ 1900 │
│ /checkout │ █████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 950  │
└───────────────────────────────────────────────────────────┘
```

Not sure how to shape `series`? `python scripts/asciicharts.py --list` prints every chart with what it
draws, how to fill `series`, its options and a working example. As a library:
`from asciicharts import render_chart` (raises `ChartError`, a `ValueError`, on bad input).

## The spec

Required: `chartType`, `series` (each `{name, values}` or `{name, points}`). Optional, the ones you'll
use most: `title`, `labels`, `border` (`none` is the most compact), `width`/`height` (max 500/200),
`stacked`, `style`, `threshold` / `thresholds` (labelled, e.g. a target and an SLA), `showPoints`, `bins`.
Every option, the limits and the error messages are in [references/reference.md](references/reference.md);
every chart rendered, with the spec that made it, is in [references/gallery.md](references/gallery.md) —
look there to choose a style.

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

Columns can be given by name (case-insensitive), by a unique prefix (`p99` finds `p99_ms`) or as 1-based
numbers. Bars, lines and areas make each value column a series with the label column as categories;
`pie` makes one slice per row; `heatmap` makes one matrix row per CSV row; `scatter` plots each value
column against the label (x) column. Rows that don't parse (`n/a`, empty cells) are reported by row and
column instead of being dropped silently — clean or filter the file first, or pick other `--values`.

Without a way to run the script, read the CSV yourself, sort and trim it, and draw by hand as above.

## From an ExCSV file

[ExCSV](https://github.com/boligolov/excsv) is CSV that describes itself: a `#!excsv` first line, then
`#`-prefixed lines above the rows — column types and roles (`#column`) and chart suggestions
(`#chart type=bar x=category y=amount ...`). `--csv` detects it and renders a suggestion directly:

```sh
python scripts/asciicharts.py --csv sales.excsv --chart-name top_categories   # by name
python scripts/asciicharts.py --csv sales.excsv                              # auto-picks the file's only suggestion
python scripts/asciicharts.py --csv sales.excsv --list-charts                # see what's available: name, type, title
```

With several suggestions and no `--chart-name`, the error names every choice. `sort=`, `limit=`,
`aggregate=`, `color=` and `stack=` are honored; `type=bar bin=N x=amount y=count()` becomes a histogram.
A suggestion with no text equivalent (`tick`/`text`, `#chart-vega`) fails with a clear message.
`--chart TYPE` still works on an ExCSV file: it reads just the data rows, with `--label`/`--values`
defaulting to the file's declared `role=dimension`/`role=measure` columns.

## Making it read well

- **Use `"style": "ascii"` (and `"border": "ascii"`) when you don't know where the text will be shown**:
  a density-ordered ramp of 23 plain-ASCII series glyphs (`#`, `@`, `%`, `&`, `$`, `W`, `M`, `N`, `H`, `D`, `G`, `U`, `O`, `S`, `Z`, `X`, `=`, `/`, `\`, `:`, `;`, `!`, `'`),
  `|` separators, `+` axis ticks, `,` as the bar track — pure ASCII, frame included.
- **The light background behind a bar is the rest of the axis**, like a progress-bar track (`░`, or `,` in
  ASCII): a short bar's real size reads at a glance. Stacked and diverging bars, `halftone` and histograms
  have none.
- **Sort and trim before plotting.** A ranking of 40 bars is unreadable; the top 10 says more.
- **Label things.** A title and named series remove the guessing; several series get a legend.
- **Round or scale the raw values** (thousands, ms → s) if they are noisy; whole numbers print without
  decimals, others with two (below 1, two significant digits).

## Not the right tool

The user needs an image file (PNG/SVG/PDF), an interactive or zoomable chart, or thousands of points where
the fine detail matters — use a plotting library for those. For a long series that only needs its shape,
aggregate first (per hour, per day) or use a `sparkline`.
