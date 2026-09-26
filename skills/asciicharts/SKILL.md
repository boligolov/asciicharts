---
name: asciicharts
description: Use this skill to draw a chart out of text characters (Unicode/ASCII) in the reply — bar, line, area, sparkline, histogram, pie, heatmap, boxplot, scatter, dot plot — from numbers given inline, a CSV file, or an ExCSV file's own #chart suggestion. Trigger on any request to plot, chart, graph, visualize or draw a histogram or distribution of numbers, e.g. "quick histogram of these response times", rankings, trends over time, shares of a whole, benchmark results, "top N by X", and whenever a chart would help in a terminal, README, commit message, PR description or code comment, even if the user never says "chart". It teaches drawing such charts correctly by hand and uses an exact renderer when available (MCP server, achart command or bundled Python script), so prefer it to describing numbers in prose or eyeballing ASCII bars. Not for PNG/SVG/image files, interactive dashboards, plotting-library code (matplotlib, seaborn, pandas), explanations of chart concepts, or stats calculations without a chart.
license: MIT
metadata:
  version: "0.1.2"
compatibility: Works without any tool (the charts are drawn by hand from references/drawing.md); a connected asciicharts MCP server, the achart command (a single binary), or Python 3 (standard library only) makes them exact.
---

# asciicharts

Text charts for chat replies, terminals, commits, PRs, code comments and logs — with lengths that match
the values, frames that stay straight in any font, and series you can tell apart without color.
Hand-drawn text charts go wrong in one way: characters are eyeballed, not counted. Count them.

## Workflow

1. **Pick the chart** (table below).
2. **Pick how to draw it** — the first that works:
   - MCP server `asciicharts` connected → its `render_chart` tool (the JSON spec below; `list_charts` is the catalogue);
   - `achart --version` works → the `achart` command: same arguments and output as the script, except ExCSV;
   - Python 3 → `python scripts/asciicharts.py` ([below](#with-the-script));
   - nothing → **draw by hand** with [references/drawing.md](references/drawing.md) and
     [references/glyphs.md](references/glyphs.md). That is all you need to read; open
     [references/principles.md](references/principles.md) only for *why* a rule exists.
3. **Check it**: by hand, run the self-check at the end of `drawing.md`; rendered, compare the printed
   values with the data. A tool error is one line saying what to fix.
4. **Answer with the chart in a fenced code block** — outside one the alignment is lost — and one
   sentence on what it shows.

## Pick the chart

| the question | chart | by hand |
|---|---|---|
| one metric's trend, inline in a sentence | `sparkline` | A |
| a ranking, one value per category | `hbar` (long names) or `vbar` | A |
| several measures per category, or parts of a whole | grouped `hbar`/`vbar`, or `"stacked": true` | A |
| close values, zero irrelevant | `dotplot` | A |
| change over time | `line` (precise) or `area` (volume) | B |
| distribution of raw values | `histogram` (`bins`) or `boxplot` per group | B |
| a grid (hour × weekday) | `heatmap` | B |
| two numbers' relationship | `scatter` (`points`: `{x, y}`) | B, few points |
| values against a target | `line` + `thresholds` | B |
| shares of a whole | `pie` | C → 100% stacked `hbar` |
| two series on different scales | `dual_axis` | C → two small line charts |

By hand: **A** draw it; **B** draw it small (plot ≤ 20 × 6) and check every number; **C** use a tool, or
draw the equivalent after the arrow and say so. Pass raw samples to `histogram`/`boxplot`; negative values
work everywhere (bars grow both ways from a zero axis).

## The rules

- **Compute lengths**: `cells = round(v / max × W)`, half away from zero; a non-zero value gets at least
  one cell, zero gets none.
- **Bars start at zero**, or grow both ways from a marked zero axis. Lines and dot plots may zoom in —
  then print the range.
- **Font-safe glyphs only**: `█ ▓ ▒ ░ ▌ ▄ ▐ ▀`, `─ │ ┌ ┐ └ ┘ ├ ┤`, `● ○ ▲ ■`. A missing glyph comes from
  another font and breaks the alignment. Unsure where it will be shown: `"style": "ascii"` and
  `"border": "ascii"` (by hand: `# @ % &`, `|`, `+`). The one exception is the sparkline: a one-line
  trend needs the eighth blocks `▁▂▃▄▅▆▇█`, which some fonts (Consolas) lack.
- **Series told apart without color**: one glyph per series, densest first, and a legend with those
  glyphs (`█ 2025   ▓ 2026`) — or the series named on every row.
- **Print the numbers** where the grid is approximate: after hbars, under vbars, a sparkline's `lo..hi`,
  a heatmap's key (`░ 3..18   ▒ 18..34 …`), in legends, on axes. Numbers shown together (a column,
  an axis, a legend, a range) share their decimals: `5.00` above `3.59`, `66.00..85.50`.
- **Small and even**: 60–80 columns; by hand, bars of 10–20 cells. Every line the same display width:
  pad labels to the longest, count CJK and most emoji as two columns. Frame only when asked.
- **Sort and trim** before plotting (top 10, not 40 bars); give a title; round or scale noisy values.

## With the script

`scripts/asciicharts.py` — one file, standard library only (`python3` if `python` isn't found). Chart on
stdout; on bad input, exit 1 and a one-line error on stderr. `--list` prints every chart type with how to
fill `series` and a working example. As a library: `from asciicharts import render_chart` — it returns a
string; on Windows print it after `sys.stdout.reconfigure(encoding="utf-8")`, or the frame and any
non-Latin text come out wrong (the command line does this itself).

A JSON spec on stdin (no shell-quoting trouble):

```sh
echo '{"chartType":"hbar","title":"Browser share","labels":["Chrome","Firefox","Safari"],"series":[{"values":[62,21,12]}]}' | python scripts/asciicharts.py -
```

Straight from a CSV:

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

## The spec

Required: `chartType`, `series` (each `{name, values}` or `{name, points}`). Common options: `title`,
`labels`, `border` (`none` is the most compact), `width`/`height`, `stacked`, `style`, `thresholds`
(labelled reference lines), `showPoints`, `bins`. All options, limits and errors:
[references/reference.md](references/reference.md); every chart with its spec:
[references/gallery.md](references/gallery.md).

## From a CSV

`--csv FILE` (`-` for stdin) and `--chart TYPE`. Header row required; the delimiter (`, ; tab |`) is
detected; numbers may carry `$`, `%`, thousands separators or a decimal comma.

- `--label COL` — the category column (x for `scatter`); default: the first text column.
- `--values COLS` — columns to plot, comma-separated; default: every numeric column.
- `--sort COL` (`-COL` or `COL:desc` descending) and `--limit N` — "top N".
- `--set KEY=VALUE` — any option (`title=…`, `border=none`, `width=60`), repeatable.
- `--print-spec` — print the JSON spec instead, to tweak and rerun.

Columns match by name (any case), unique prefix (`p99` → `p99_ms`) or 1-based number. Each value column
is a series; `pie` makes a slice per row, `heatmap` a matrix row per row, `scatter` plots value columns
against the label column. Unparseable cells (`n/a`, empty) are an error naming row and column, never
dropped silently. No way to run the script: read the CSV, sort, trim, and draw by hand.

## From an ExCSV file

[ExCSV](https://github.com/boligolov/excsv) is CSV with a `#!excsv` first line and `#` meta lines above
the rows: column roles (`#column`) and chart suggestions (`#chart type=bar x=category y=amount`). The
script (not the `achart` command yet) renders a suggestion directly:

```sh
python scripts/asciicharts.py --csv sales.excsv --list-charts                # the file's suggestions
python scripts/asciicharts.py --csv sales.excsv --chart-name top_categories   # one by name (the only one if omitted)
```

`sort=`, `limit=`, `aggregate=`, `color=`, `stack=` are honored; `bin=N` makes a histogram; `tick`/`text`
and `#chart-vega` fail with a clear message. `--chart TYPE` reads just the data rows, defaulting
`--label`/`--values` to the `role=dimension`/`role=measure` columns.

## Not the right tool

Image files (PNG/SVG/PDF), interactive charts, or thousands of points whose detail matters — use a
plotting library. A long series that only needs its shape: aggregate it, or use a `sparkline`.
