# Tool reference

Two MCP tools — **`list_charts`** and **`render_chart`** — plus the same renderer as a Python function and command line (see the README). The MCP tools work identically over stdio and over the HTTP transport's `/mcp` endpoint.

Everything below applies equally to the tool arguments, to the dict you pass to `asciicharts.render_chart()`, and to the JSON the `asciicharts.py` command line reads.

## `render_chart`

| field       | type              | applies to                          | notes                                                                 |
|-------------|-------------------|--------------------------------------|------------------------------------------------------------------------|
| `chartType` | string, required  | all                                   | `sparkline`, `vbar`, `hbar`, `line`, `area`, `scatter`, `dual_axis`, `pie`, `histogram`, `heatmap`, `boxplot`, `dotplot` |
| `series`    | array, required   | all                                   | see below — meaning depends on `chartType`                             |
| `labels`    | string[]          | vbar, hbar, histogram, heatmap, dotplot | category labels / column headers                                     |
| `title`     | string            | all                                   | shown centered above the chart                                         |
| `width`     | int               | most types                            | defaults vary by chart type; for `vbar`, thickens each bar/column to fill the requested width; for `heatmap`, widens each cell so the grid fills it (both default to 60); for `hbar`/`dotplot`, sets the axis width |
| `height`    | int               | most types                            | defaults vary by chart type                                            |
| `border`    | string            | all                                   | `none`, `ascii`, `light` (default), `heavy`, `double`, `rounded`       |
| `style`     | string            | vbar, hbar, histogram, line, area     | vbar/hbar/histogram/area: `solid` (default; bars end on whole character cells — for single-baseline, non-stacked hbar/vbar, the rest of each bar's own cell run up to the axis scale is shaded with a light `░` background track), `fine` (hbar/histogram/single-series vbar: bars end on eighth-block glyphs for sub-cell precision, needs a font that has them — Consolas does not; a vbar with several series always uses whole rows, one fill glyph per series), `halftone` (stippled Unicode shades per series instead of flat blocks) or `ascii` (plain-ASCII characters per series, one 23-glyph ramp ordered dense to light — `#`, `@`, `%`, `&`, `$`, `W`, `M`, `N`, `H`, `D`, `G`, `U`, `O`, `S`, `Z`, `X`, `=`, `/`, `\`, `:`, `|`, `!`, `.` — with the same background track as `solid`/`fine`, drawn with `,` instead of `░` so it stays plain ASCII too). line: `solid` (default) or `dotted` (sparse `+`-plotted trend line) |
| `stacked`   | bool              | vbar, hbar, area                      | stack series (bars side-by-side per category, or area bands cumulative from zero) instead of grouping/overlaying |
| `bins`      | int               | histogram                             | default 10                                                              |
| `useColor`  | string            | all                                   | `auto` (default, same as off — output goes to an agent, not a terminal), `on`, `off` |
| `threshold` | number            | line                                  | draws a dashed horizontal reference line at this y-value                |
| `thresholds`| array             | line                                  | several reference lines, each a number or `{"value": 106, "label": "target"}`; each is dashed and named with its value right of the plot. At most 20, labels up to 40 characters |
| `showPoints`| bool              | line                                  | marks each data point with a glyph on top of the line (and switches the connector to a thin dot) |
| `pointChar` | string            | line, with showPoints                 | override the point glyph for every series (default: a large circle `●`, with a distinct shape per additional series) |

Each entry in `series` has `name`, `values`, and `points` — which ones you fill in depends on `chartType`:

- `sparkline`, `line`, `area`, `histogram`: `values` is the sample sequence
- `vbar`, `hbar`, `dotplot`: `values` holds one number per category (aligned with `labels`) — vbar/hbar draw multiple series grouped or stacked, dotplot always overlays them on the same row
- `scatter`, `dual_axis` (as points): `points` holds `{x, y}` samples — `dual_axis` actually takes two `values` series, one per axis
- `pie`: `values` sums to the slice's magnitude, `name` is its label
- `heatmap`: `values` is one matrix row, `name` is the row label, `labels` are column headers
- `boxplot`: `values` is the raw sample population — min/Q1/median/Q3/max are computed for you

## Diverging bars

`vbar` and `hbar` render a **diverging** chart automatically the instant any value in the data is negative: instead of every bar starting at the bottom row (or left edge), the zero baseline moves to wherever `0` actually falls in the value range, and bars grow toward either side of it — a dashed/`|` guide marks the baseline itself. A chart where every value is non-negative renders exactly as before; this isn't an opt-in flag, just what negative data does. `area` gets the same treatment for overlaid (non-stacked) series. **Stacked** vbar/hbar/area diverge as well: positive values stack up (right) from the baseline and negative values stack down (left) from it, first series nearest zero; for stacked hbar the number at the end of the row is the net total.

## Limits

Requests are bounded so a single call can't ask for a gigantic chart: `width` ≤ 500, `height` ≤ 200, `bins` ≤ 500, at most 100 series and 50,000 values/points in total. Values must be finite numbers (no NaN/Infinity) no larger than 1e15 in magnitude. `title`, `labels` and series names are at most 200 characters; control characters in them (newlines, tabs, escape sequences) are replaced by spaces, so a string from untrusted data can't break the chart's rows or send escape codes to a terminal. Text is aligned by the columns it takes on screen, not by its length: CJK characters and most emoji count as two, combining accents as none, so labels in any script keep the frame straight (emoji joined into one glyph with zero-width joiners, like 👨‍👩‍👧, are drawn differently by different terminals and can still be off). `pointChar` must be one column wide. Violations are reported as errors, not truncated.

## Errors

Invalid input raises `asciicharts.ChartError` (a `ValueError`); over MCP it comes back as an `isError` tool result carrying the same message, so an agent can read it and correct the call.

## `list_charts`

Takes no arguments. Returns the catalogue of chart types — one entry per `chartType`, in a stable order:

| field     | meaning |
|-----------|---------|
| `type`    | the `chartType` value to pass to `render_chart` |
| `summary` | what the chart draws and when to use it |
| `series`  | how to fill `series` for this type |
| `options` | the `render_chart` options that affect this chart (every chart also accepts `title`, `border` and `useColor`) |
| `example` | a minimal valid `render_chart` call |

It is the same data as `python asciicharts.py --list` and `asciicharts.list_charts()`. The `options` lists are checked by the test suite against the renderers: a listed option changes the output for that chart, and an unlisted one does not.

See `gallery.md` (next to this file; also `docs/gallery.md` in the source repository) for an annotated example of every chart type and style.
