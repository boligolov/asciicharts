# ascii-charts-mcp

An [MCP](https://modelcontextprotocol.io) server with a single tool, `render_chart`, that turns numeric data into an ASCII/Unicode text chart and hands it back as plain text — no image, no library on the caller's side, just a string an agent can drop straight into a reply.

Written in Go on the official [`modelcontextprotocol/go-sdk`](https://github.com/modelcontextprotocol/go-sdk). All rendering (line drawing, quadrant/braille sub-character packing, bar scaling, pie rasterization, box-and-whisker math) is hand-rolled — the only dependency is the MCP SDK itself.

## Features

- **10 chart types**: `sparkline`, `vbar`, `hbar`, `line`, `scatter`, `dual_axis`, `pie`, `histogram`, `heatmap`, `boxplot`
- **vbar/hbar** support single-series, grouped, and stacked layouts
- **line/scatter/dual_axis** support three sub-character resolutions: `cell` (1 point per character), `quad` (2×2 dots via quadrant blocks `▘▝▀▖▌▞▛▗▚▐▜▄▙▟█`), and `braille` (2×4 dots via Unicode braille patterns) for much smoother curves
- **6 border styles**: `none`, `ascii`, `light`, `heavy`, `double`, `rounded` — with a centered title row
- Optional **ANSI 256-color** output (`useColor: on`), off by default since tool output goes to an agent, not a terminal

## Chart types at a glance

| chartType   | what it draws                                              |
|-------------|--------------------------------------------------------------|
| `sparkline` | one-line trend, no axes                                      |
| `vbar`      | vertical bars — single / grouped / stacked                   |
| `hbar`      | horizontal bars — single / grouped / stacked                 |
| `line`      | one or many line series, with left-axis value ticks          |
| `scatter`   | (x, y) points only, one or many series                       |
| `dual_axis` | exactly two line series, independent left/right y-axes       |
| `pie`       | circular pie chart + legend with percentages                 |
| `histogram` | buckets raw values into bins and draws them as horizontal bars |
| `heatmap`   | 2-D matrix as shaded (or colored) cells                      |
| `boxplot`   | min / Q1 / median / Q3 / max, computed from raw samples       |

## Examples

Generate all of these yourself with `go run ./cmd/gallery`.

> [!NOTE]
> These examples use several Unicode ranges beyond plain ASCII: box-drawing frames, eighth-block characters (`▏▎▍▌▋▊▉` / `▁▂▃▄▅▆▇`) for fractional bar widths/heights, quadrant blocks (`▘▝▖▗▞▚▛▙▜▟`) for `mode: "quad"`, and braille patterns (`⠀`-`⣿`) for `mode: "braille"`. GitHub's own rendering and most terminals (iTerm2, Windows Terminal, Ghostty, …) have full glyph coverage and will show these perfectly aligned. Some editors' **default** monospace fonts — Consolas in particular, VS Code and PyCharm's out-of-the-box choice on Windows — don't ship glyphs for the finer block/quadrant/braille characters and silently substitute a fallback font for just those, which throws off column alignment even though the underlying text is correct. If a chart below looks ragged in your editor, either view this file on GitHub, or switch your editor's monospace font to one with full coverage (e.g. **Cascadia Code**, **JetBrains Mono**, **Noto Sans Mono**, **DejaVu Sans Mono**).

### sparkline

```json
{ "chartType": "sparkline", "series": [{ "name": "latency", "values": [4, 6, 5, 9, 3, 7, 8, 2, 6, 9, 4] }] }
```

```
latency ▃▅▄█▂▆▇▁▅█▃
```

### vbar (grouped)

```json
{
  "chartType": "vbar",
  "title": "Revenue by quarter",
  "border": "rounded",
  "height": 10,
  "labels": ["Q1", "Q2", "Q3", "Q4"],
  "series": [
    { "name": "2025", "values": [30, 45, 40, 60] },
    { "name": "2026", "values": [35, 50, 55, 70] }
  ]
}
```

```
╭────────────────────╮
│ Revenue by quarter │
├────────────────────┤
│           █        │
│          ▅█        │
│     ▁  ▇ ██        │
│    ▃█  █ ██        │
│    ██ ▆█ ██        │
│ ▂█ ██ ██ ██        │
│ ██ ██ ██ ██        │
│ ██ ██ ██ ██        │
│ ██ ██ ██ ██        │
│ ██ ██ ██ ██        │
│ Q1 Q2 Q3 Q4        │
│                    │
│ █ 2025   ▓ 2026    │
╰────────────────────╯
```

### vbar (stacked)

```json
{
  "chartType": "vbar",
  "title": "Revenue by quarter (stacked)",
  "border": "double",
  "stacked": true,
  "labels": ["Q1", "Q2", "Q3", "Q4"],
  "series": [
    { "name": "Product", "values": [30, 45, 40, 60] },
    { "name": "Services", "values": [15, 20, 18, 25] }
  ]
}
```

```
╔══════════════════════════════╗
║ Revenue by quarter (stacked) ║
╠══════════════════════════════╣
║           ▓                  ║
║           ▓                  ║
║     ▓     ▓                  ║
║     ▓  ▓  █                  ║
║     █  ▓  █                  ║
║  ▓  █  █  █                  ║
║  ▓  █  █  █                  ║
║  █  █  █  █                  ║
║  █  █  █  █                  ║
║  █  █  █  █                  ║
║ Q1 Q2 Q3 Q4                  ║
║                              ║
║ █ Product   ▓ Services       ║
╚══════════════════════════════╝
```

### hbar (single series)

```json
{
  "chartType": "hbar",
  "title": "Browser share",
  "border": "light",
  "labels": ["Chrome", "Firefox", "Safari", "Other"],
  "series": [{ "values": [62, 21, 12, 5] }]
}
```

```
┌───────────────────────────────────────────────────────┐
│                     Browser share                     │
├───────────────────────────────────────────────────────┤
│ Chrome  │ ████████████████████████████████████████ 62 │
│ Firefox │ █████████████▌                           21 │
│ Safari  │ ███████▋                                 12 │
│ Other   │ ███▏                                     5  │
└───────────────────────────────────────────────────────┘
```

### hbar (stacked)

```json
{
  "chartType": "hbar",
  "title": "Revenue by region (stacked)",
  "border": "light",
  "stacked": true,
  "labels": ["EMEA", "APAC", "Americas"],
  "series": [
    { "name": "Product", "values": [40, 25, 55] },
    { "name": "Services", "values": [15, 20, 18] }
  ]
}
```

```
┌────────────────────────────────────────────────────────┐
│              Revenue by region (stacked)               │
├────────────────────────────────────────────────────────┤
│ EMEA     │ ██████████████████████▓▓▓▓▓▓▓▓           55 │
│ APAC     │ ██████████████▓▓▓▓▓▓▓▓▓▓▓                45 │
│ Americas │ ██████████████████████████████▓▓▓▓▓▓▓▓▓▓ 73 │
│                                                        │
│ █ Product   ▓ Services                                 │
└────────────────────────────────────────────────────────┘
```

### line (cell resolution)

```json
{
  "chartType": "line",
  "title": "CPU load",
  "height": 8,
  "series": [{ "values": [12, 18, 15, 30, 42, 38, 50, 45, 60, 55, 48, 35] }]
}
```

```
┌─────────────────────────────────────────────────────────────────────┐
│                              CPU load                               │
├─────────────────────────────────────────────────────────────────────┤
│    60 ┤                                         ████                │
│ 53.14 ┤                               ████    ██    ██████          │
│ 46.29 ┤                            ███    ████            ████      │
│ 39.43 ┤                   █████████                           ███   │
│ 32.57 ┤               ████                                       ██ │
│ 25.71 ┤             ██                                              │
│ 18.86 ┤   █████   ██                                                │
│    12 ┤███     ███                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

### line (threshold + points)

`threshold` overlays a dashed reference line at a fixed y-value (e.g. an SLA or target); `showPoints` marks each actual data point on top of the interpolated curve.

```json
{
  "chartType": "line",
  "title": "Response time vs SLA",
  "height": 8,
  "threshold": 50,
  "showPoints": true,
  "series": [{ "values": [20, 25, 22, 30, 45, 38, 55, 60, 48, 35, 30, 28] }]
}
```

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Response time vs SLA                         │
├─────────────────────────────────────────────────────────────────────┤
│    60 ┤                                   ██●█                      │
│ 54.29 ┤                               █●██    ██                    │
│ 48.57 ┤- - - - - - - - - - - - - - -█- - - - - -█●█- - - - - - - -  │
│ 42.86 ┤                    █●██   ██               ███              │
│ 37.14 ┤                  ██    ██●                    █●██          │
│ 31.43 ┤               █●█                                 ██●██     │
│ 25.71 ┤   ██●██    ███                                         ███● │
│    20 ┤●██     ██●█                                                 │
│                                                                     │
│ - - threshold: 50                                                   │
└─────────────────────────────────────────────────────────────────────┘
```

### line (braille resolution, two series)

`mode: "braille"` packs a 2×4 dot grid into every character cell for a much smoother curve than one point per column.

```json
{
  "chartType": "line",
  "title": "Temperature: forecast vs actual",
  "border": "heavy",
  "mode": "braille",
  "width": 50,
  "height": 10,
  "series": [
    { "name": "forecast", "values": [10, 12, 15, 14, 18, 20, 19, 17, 15, 13, 12, 11] },
    { "name": "actual",   "values": [11, 13, 14, 16, 17, 19, 21, 18, 16, 14, 13, 10] }
  ]
}
```

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃              Temperature: forecast vs actual              ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃    21 ┤                         ⡠⠔⠑⡄                      ┃
┃ 19.78 ┤                    ⢀⠤⢊⠕⠚⠤⢄⡀⠈⠢⡀                    ┃
┃ 18.56 ┤                  ⡠⠒⡡⠒⠁    ⠈⠒⢄⠘⢄                   ┃
┃ 17.33 ┤                ⢀⡼⠔⠉          ⠉⠢⡑⠢⡀                ┃
┃ 16.11 ┤             ⡠⠔⢊⠏               ⠈⠑⢌⡑⢄              ┃
┃ 14.89 ┤        ⡠⠒⣤⣔⠉ ⡠⠃                   ⠈⠢⣉⠢⣀           ┃
┃ 13.67 ┤     ⢀⣀⠴⠕⠊  ⠉⠒⠁                       ⠑⠤⡑⠢⠤⣀⡀      ┃
┃ 12.44 ┤  ⢀⠤⠊⡱⠁                                 ⠈⠑⠢⢄⡈⠑⡄    ┃
┃ 11.22 ┤⡠⠒⢁⠤⠊                                       ⠈⠉⠚⠢⡤⣀ ┃
┃    10 ┤⡠⠒⠁                                             ⠘⢄ ┃
┃                                                           ┃
┃ █ forecast   ▓ actual                                     ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

### scatter (quad resolution)

```json
{
  "chartType": "scatter",
  "title": "Height vs weight",
  "mode": "quad",
  "width": 40,
  "height": 12,
  "series": [
    { "name": "group A", "points": [{ "x": 160, "y": 55 }, { "x": 165, "y": 60 }, { "x": 170, "y": 65 }, { "x": 172, "y": 68 }] },
    { "name": "group B", "points": [{ "x": 175, "y": 80 }, { "x": 180, "y": 85 }, { "x": 185, "y": 90 }, { "x": 178, "y": 78 }] }
  ]
}
```

```
┌──────────────────────────────────────────┐
│             Height vs weight             │
├──────────────────────────────────────────┤
│                                        ▖ │
│                                ▘         │
│                                          │
│                        ▘                 │
│                             ▖            │
│                                          │
│                                          │
│                    ▗                     │
│                 ▗                        │
│                                          │
│         ▗                                │
│ ▝                                        │
│ x: [160, 185]  y: [55, 90]               │
│ █ group A   ▓ group B                    │
└──────────────────────────────────────────┘
```

### dual_axis

Two series sharing one x-axis, each with its own independent y-axis scale (left / right).

```json
{
  "chartType": "dual_axis",
  "title": "Temperature (left) vs humidity (right)",
  "height": 8,
  "series": [
    { "name": "Temp °C",    "values": [10, 12, 15, 14, 18, 20, 19] },
    { "name": "Humidity %", "values": [80, 78, 65, 70, 60, 55, 58] }
  ]
}
```

```
┌────────────────────────────────────────────────────────────────────────────┐
│                   Temperature (left) vs humidity (right)                   │
├────────────────────────────────────────────────────────────────────────────┤
│    20 ┤▒▒▒▒▒                                       ██████████      ├ 80    │
│ 18.57 ┤     ▒▒▒▒▒▒                           ██████          ██████├ 76.43 │
│ 17.14 ┤           ▒▒▒                    ████                      ├ 72.86 │
│ 15.71 ┤              ▒▒▒▒      ▒▒▒▒▒▒▒███                          ├ 69.29 │
│ 14.29 ┤                 █▒▒▒▒▒▒███████▒▒▒                          ├ 65.71 │
│ 12.86 ┤            █████                 ▒▒▒▒                      ├ 62.14 │
│ 11.43 ┤     ███████                          ▒▒▒▒▒▒          ▒▒▒▒▒▒├ 58.57 │
│    10 ┤█████                                       ▒▒▒▒▒▒▒▒▒▒      ├ 55    │
│                                                                            │
│ left:  █ Temp °C                                                           │
│ right: ▒ Humidity %                                                        │
└────────────────────────────────────────────────────────────────────────────┘
```

### pie

```json
{
  "chartType": "pie",
  "title": "Browser share",
  "border": "rounded",
  "width": 32,
  "height": 16,
  "series": [
    { "name": "Chrome", "values": [62] },
    { "name": "Firefox", "values": [21] },
    { "name": "Safari", "values": [12] },
    { "name": "Other", "values": [5] }
  ]
}
```

```
╭──────────────────────────────────╮
│          Browser share           │
├──────────────────────────────────┤
│           ▒░░░░░██████           │
│        ▒▒▒▒▒░░░░█████████        │
│     ▒▒▒▒▒▒▒▒░░░░████████████     │
│    ▒▒▒▒▒▒▒▒▒▒░░░█████████████    │
│   ▓▒▒▒▒▒▒▒▒▒▒▒░░██████████████   │
│  ▓▓▓▓▓▓▒▒▒▒▒▒▒░░███████████████  │
│ ▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒░████████████████ │
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒████████████████ │
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█████████████████ │
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓███████████████████ │
│  ▓▓▓▓▓▓▓▓▓▓████████████████████  │
│   ▓▓▓▓▓▓▓█████████████████████   │
│    ▓▓▓▓▓█████████████████████    │
│     ▓▓██████████████████████     │
│        ██████████████████        │
│           ████████████           │
│                                  │
│ █ Chrome: 62 (62.0%)             │
│ ▓ Firefox: 21 (21.0%)            │
│ ▒ Safari: 12 (12.0%)             │
│ ░ Other: 5 (5.0%)                │
╰──────────────────────────────────╯
```

### histogram

```json
{
  "chartType": "histogram",
  "title": "Response times (ms)",
  "border": "double",
  "bins": 6,
  "series": [{ "values": [12, 15, 14, 18, 20, 22, 21, 25, 30, 28, 35, 40, 55, 60, 18, 19, 22] }]
}
```

```
╔═════════════════════════════════════════════════════╗
║                 Response times (ms)                 ║
╠═════════════════════════════════════════════════════╣
║ 12..20 │ ████████████████████████████████████████ 6 ║
║ 20..28 │ █████████████████████████████████▎       5 ║
║ 28..36 │ ████████████████████                     3 ║
║ 36..44 │ ██████▋                                  1 ║
║ 44..52 │                                          0 ║
║ 52..60 │ █████████████▎                           2 ║
╚═════════════════════════════════════════════════════╝
```

### heatmap

```json
{
  "chartType": "heatmap",
  "title": "Traffic by hour",
  "labels": ["Mon", "Tue", "Wed", "Thu", "Fri"],
  "series": [
    { "name": "9am", "values": [20, 35, 25, 40, 30] },
    { "name": "1pm", "values": [55, 60, 58, 62, 50] },
    { "name": "5pm", "values": [80, 70, 90, 85, 95] }
  ]
}
```

```
┌──────────────────────────┐
│     Traffic by hour      │
├──────────────────────────┤
│     Mon Tue Wed Thu Fri  │
│ 9am             ░░░      │
│ 1pm ░░░ ▒▒▒ ▒▒▒ ▒▒▒ ░░░  │
│ 5pm ▓▓▓ ▒▒▒ ▓▓▓ ▓▓▓ ███  │
└──────────────────────────┘
```

With `"useColor": "on"` cells render as colored `███` blocks along a blue→red ANSI 256 ramp instead of the `" ░▒▓█"` shade ladder.

### boxplot

```json
{
  "chartType": "boxplot",
  "title": "Test scores by class",
  "width": 50,
  "series": [
    { "name": "Class A", "values": [55, 60, 62, 65, 70, 72, 75, 80, 85, 95] },
    { "name": "Class B", "values": [40, 50, 58, 60, 63, 65, 68, 70, 78, 99] }
  ]
}
```

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                         Test scores by class                                         │
├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Class A │             ├──────███████┃██████─────────────┤     min=55 q1=62.75 med=71 q3=78.75 max=95 │
│ Class B │ ├──────────────█████┃█████───────────────────────┤  min=40 q1=58.50 med=64 q3=69.50 max=99 │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Boxplot values are computed automatically from the raw sample population you pass in — you don't precompute quartiles yourself.

## Tool reference

Single tool: **`render_chart`**.

| field       | type              | applies to                          | notes                                                                 |
|-------------|-------------------|--------------------------------------|------------------------------------------------------------------------|
| `chartType` | string, required  | all                                   | `sparkline`, `vbar`, `hbar`, `line`, `scatter`, `dual_axis`, `pie`, `histogram`, `heatmap`, `boxplot` |
| `series`    | array, required   | all                                   | see below — meaning depends on `chartType`                             |
| `labels`    | string[]          | vbar, hbar, histogram, heatmap        | category labels / column headers                                       |
| `title`     | string            | all                                   | shown centered above the chart                                         |
| `width`     | int               | most types                            | defaults vary by chart type                                            |
| `height`    | int               | most types                            | defaults vary by chart type                                            |
| `border`    | string            | all                                   | `none`, `ascii`, `light` (default), `heavy`, `double`, `rounded`       |
| `mode`      | string            | line, scatter, dual_axis              | `cell` (default), `quad`, `braille`                                    |
| `stacked`   | bool              | vbar, hbar                            | stack series instead of grouping them side by side                     |
| `bins`      | int               | histogram                             | default 10                                                              |
| `useColor`  | string            | all                                   | `auto` (default, same as off — output goes to an agent, not a terminal), `on`, `off` |
| `threshold` | number            | line                                  | draws a dashed horizontal reference line at this y-value                |
| `showPoints`| bool              | line                                  | marks each data point with a distinct glyph on top of the line          |

Each entry in `series` has `name`, `values`, and `points` — which ones you fill in depends on `chartType`:

- `sparkline`, `line`, `histogram`: `values` is the sample sequence
- `vbar`, `hbar`: `values` holds one number per category (aligned with `labels`)
- `scatter`, `dual_axis` (as points): `points` holds `{x, y}` samples — `dual_axis` actually takes two `values` series, one per axis
- `pie`: `values` sums to the slice's magnitude, `name` is its label
- `heatmap`: `values` is one matrix row, `name` is the row label, `labels` are column headers
- `boxplot`: `values` is the raw sample population — min/Q1/median/Q3/max are computed for you

## Build & run

Requires Go 1.27+.

```sh
go build -o ascii-charts-mcp .
./ascii-charts-mcp
```

The server speaks MCP over stdio, so it's meant to be launched by an MCP client (Claude Desktop, Claude Code, etc.), not run interactively by hand.

Run the example gallery (used to generate the examples above):

```sh
go run ./cmd/gallery
```

Run the tests:

```sh
go test ./...
```

## Docker

Build the image:

```sh
docker build -t ascii-charts-mcp .
```

This produces a ~9 MB image (`FROM scratch`, statically linked, no libc). Run it manually with `-i` so the MCP client's stdio actually reaches the container:

```sh
docker run -i --rm ascii-charts-mcp
```

## Using it from an MCP client

Point your client's MCP server config at the built binary:

```json
{
  "mcpServers": {
    "ascii-charts": {
      "command": "/path/to/ascii-charts-mcp"
    }
  }
}
```

Or run it through Docker instead of a local binary:

```json
{
  "mcpServers": {
    "ascii-charts": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "ascii-charts-mcp"]
    }
  }
}
```
