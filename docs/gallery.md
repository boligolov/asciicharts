# Gallery

One example of every chart type and style. Every block below is real output of `asciicharts.py`.
In the source repository a test checks that each printed output is exactly what the renderer produces for the spec above it.

Highlights: **12 chart types**; grouped, stacked and **diverging** bars/areas (negative values grow
the other way from a zero baseline); **6 border styles**; **`halftone`**, **`ascii`** and **`dotted`**
styles; optional ANSI 256-color output.

## Contents

<!-- toc -->
- **[sparkline](#sparkline)**
- **vbar**: [grouped](#vbar-grouped) · [custom width](#vbar-custom-width) · [stacked](#vbar-stacked) · [halftone style](#vbar-halftone-style) · [ascii style](#vbar-ascii-style) · [diverging](#vbar-diverging) · [stacked, diverging](#vbar-stacked-diverging)
- **hbar**: [single series](#hbar-single-series) · [fine style](#hbar-fine-style) · [stacked](#hbar-stacked) · [halftone, stacked](#hbar-halftone-stacked) · [ascii style](#hbar-ascii-style) · [ascii, many series](#hbar-ascii-many-series) · [diverging](#hbar-diverging) · [stacked, diverging](#hbar-stacked-diverging)
- **line**: [default](#line) · [threshold + points](#line-threshold--points) · [labelled thresholds](#line-labelled-thresholds) · [dotted style, Bloomberg-inspired](#line-dotted-style-bloomberg-inspired)
- **area**: [single series](#area-single-series) · [stacked](#area-stacked) · [stacked, diverging](#area-stacked-diverging)
- **[dotplot](#dotplot)**
- **scatter**: [two groups](#scatter-two-groups)
- **[dual_axis](#dual_axis)**
- **[pie](#pie)**
- **[histogram](#histogram)**
- **[heatmap](#heatmap)**
- **[boxplot](#boxplot)**
<!-- /toc -->

## Chart types at a glance

| chartType   | what it draws                                              |
|-------------|--------------------------------------------------------------|
| `sparkline` | one-line trend, no axes                                      |
| `vbar`      | vertical bars — single / grouped / stacked                   |
| `hbar`      | horizontal bars — single / grouped / stacked                 |
| `line`      | one or many line series, with left-axis value ticks          |
| `area`      | line series filled to a zero baseline — overlaid or stacked  |
| `scatter`   | (x, y) points only, one or many series                       |
| `dual_axis` | exactly two line series, independent left/right y-axes       |
| `pie`       | circular pie chart + legend with percentages                 |
| `histogram` | buckets raw values into bins and draws them as horizontal bars |
| `heatmap`   | 2-D matrix as shaded (or colored) cells                      |
| `boxplot`   | min / Q1 / median / Q3 / max, computed from raw samples       |
| `dotplot`   | one marker per category/series on a shared value axis (Cleveland dot plot) |

## Examples

Each spec is printed above its output: save it as `spec.json` and run `python asciicharts.py spec.json` to reproduce any example.

> [!NOTE]
> These examples use Unicode beyond plain ASCII: box-drawing frames, block and shade characters (`█▓▒░▌▄`) for bars, simple geometric markers (`●○▲■`) and — only with `style: "fine"` and in sparklines — eighth blocks (`▏▎▍▌▋▊▉`, `▁▂▃▅▆▇`). GitHub's own rendering and most terminals (iTerm2, Windows Terminal, Ghostty, …) have full glyph coverage and show these perfectly aligned. Some fonts do not: Consolas, Courier New and Lucida Console — the defaults of many Windows editors — lack the eighth blocks, and silently substitute another font for just those characters, which throws off column alignment even though the text is correct. The telltale sign is a crooked right border on an otherwise rectangular chart. Every line genuinely has the same character count (the test suite checks this), so a jagged wall means the viewer, not the generator. Everything except `fine` bars and sparklines is drawn with glyphs that Consolas and Courier New contain; if one of those examples looks ragged in your editor, view this file on GitHub or switch to a font with full coverage (**Cascadia Code**, **JetBrains Mono**, **Noto Sans Mono**, **DejaVu Sans Mono**).

### sparkline

```json
{ "chartType": "sparkline", "border": "none", "series": [{ "name": "latency", "values": [4, 6, 5, 9, 3, 7, 8, 2, 6, 9, 4] }] }
```

```
latency ▃▅▄█▂▆▇▁▅█▃ 2..9
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
╭─────────────────────────────────────────────────────────────╮
│                     Revenue by quarter                      │
├─────────────────────────────────────────────────────────────┤
│ ░░░░░░░░░░░░░░ ░░░░░░░░░░░░░░ ░░░░░░░░░░░░░░ ░░░░░░░▓▓▓▓▓▓▓ │
│ ░░░░░░░░░░░░░░ ░░░░░░░░░░░░░░ ░░░░░░░░░░░░░░ ███████▓▓▓▓▓▓▓ │
│ ░░░░░░░░░░░░░░ ░░░░░░░░░░░░░░ ░░░░░░░▓▓▓▓▓▓▓ ███████▓▓▓▓▓▓▓ │
│ ░░░░░░░░░░░░░░ ░░░░░░░▓▓▓▓▓▓▓ ░░░░░░░▓▓▓▓▓▓▓ ███████▓▓▓▓▓▓▓ │
│ ░░░░░░░░░░░░░░ ███████▓▓▓▓▓▓▓ ███████▓▓▓▓▓▓▓ ███████▓▓▓▓▓▓▓ │
│ ░░░░░░░▓▓▓▓▓▓▓ ███████▓▓▓▓▓▓▓ ███████▓▓▓▓▓▓▓ ███████▓▓▓▓▓▓▓ │
│ ███████▓▓▓▓▓▓▓ ███████▓▓▓▓▓▓▓ ███████▓▓▓▓▓▓▓ ███████▓▓▓▓▓▓▓ │
│ ███████▓▓▓▓▓▓▓ ███████▓▓▓▓▓▓▓ ███████▓▓▓▓▓▓▓ ███████▓▓▓▓▓▓▓ │
│ ███████▓▓▓▓▓▓▓ ███████▓▓▓▓▓▓▓ ███████▓▓▓▓▓▓▓ ███████▓▓▓▓▓▓▓ │
│ ███████▓▓▓▓▓▓▓ ███████▓▓▓▓▓▓▓ ███████▓▓▓▓▓▓▓ ███████▓▓▓▓▓▓▓ │
│       Q1             Q2             Q3             Q4       │
│                                                             │
│ █ 2025   ▓ 2026                                             │
╰─────────────────────────────────────────────────────────────╯
```

With more than one series, each gets its own shade (`█`, `▓`, `▒`, …) even in the default `solid` style — matching the legend below the chart — not just when color is on. A lone series stays a plain solid block, no shading needed.

### vbar (custom width)

`width` is optional: without it the bars thicken to fill a 60-character plot, as above. It isn't just cosmetic padding either way — pass a smaller one for a compact chart (here 24) and every bar/column narrows to fit it, down to one character with `"width": 1`.

```json
{
  "chartType": "vbar",
  "title": "Revenue by quarter (width: 24)",
  "border": "rounded",
  "height": 10,
  "width": 24,
  "labels": ["Q1", "Q2", "Q3", "Q4"],
  "series": [
    { "name": "2025", "values": [30, 45, 40, 60] },
    { "name": "2026", "values": [35, 50, 55, 70] }
  ]
}
```

```
╭────────────────────────────────╮
│ Revenue by quarter (width: 24) │
├────────────────────────────────┤
│ ░░░░ ░░░░ ░░░░ ░░▓▓            │
│ ░░░░ ░░░░ ░░░░ ██▓▓            │
│ ░░░░ ░░░░ ░░▓▓ ██▓▓            │
│ ░░░░ ░░▓▓ ░░▓▓ ██▓▓            │
│ ░░░░ ██▓▓ ██▓▓ ██▓▓            │
│ ░░▓▓ ██▓▓ ██▓▓ ██▓▓            │
│ ██▓▓ ██▓▓ ██▓▓ ██▓▓            │
│ ██▓▓ ██▓▓ ██▓▓ ██▓▓            │
│ ██▓▓ ██▓▓ ██▓▓ ██▓▓            │
│ ██▓▓ ██▓▓ ██▓▓ ██▓▓            │
│  Q1   Q2   Q3   Q4             │
│                                │
│ █ 2025   ▓ 2026                │
╰────────────────────────────────╯
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
╔═════════════════════════════════════════════════════════════╗
║                Revenue by quarter (stacked)                 ║
╠═════════════════════════════════════════════════════════════╣
║                                              ▓▓▓▓▓▓▓▓▓▓▓▓▓▓ ║
║                                              ▓▓▓▓▓▓▓▓▓▓▓▓▓▓ ║
║                ▓▓▓▓▓▓▓▓▓▓▓▓▓▓                ▓▓▓▓▓▓▓▓▓▓▓▓▓▓ ║
║                ▓▓▓▓▓▓▓▓▓▓▓▓▓▓ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓ ██████████████ ║
║                ██████████████ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓ ██████████████ ║
║ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓ ██████████████ ██████████████ ██████████████ ║
║ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓ ██████████████ ██████████████ ██████████████ ║
║ ██████████████ ██████████████ ██████████████ ██████████████ ║
║ ██████████████ ██████████████ ██████████████ ██████████████ ║
║ ██████████████ ██████████████ ██████████████ ██████████████ ║
║       Q1             Q2             Q3             Q4       ║
║                                                             ║
║ █ Product   ▓ Services                                      ║
╚═════════════════════════════════════════════════════════════╝
```

### vbar (halftone style)

`style: "halftone"` trades the flat solid-block fill for a lighter, stippled per-series shade — closer to the dot-matrix look of the Bloomberg Businessweek charts that inspired it, and it keeps series visually distinct from each other even without color (compare to the plain "vbar (grouped)" example above, where every series is drawn with the same solid block and only its position tells them apart).

```json
{
  "chartType": "vbar",
  "title": "Revenue by quarter (halftone)",
  "border": "rounded",
  "height": 10,
  "style": "halftone",
  "labels": ["Q1", "Q2", "Q3", "Q4"],
  "series": [
    { "name": "2025", "values": [30, 45, 40, 60] },
    { "name": "2026", "values": [35, 50, 55, 70] }
  ]
}
```

```
╭─────────────────────────────────────────────────────────────╮
│                Revenue by quarter (halftone)                │
├─────────────────────────────────────────────────────────────┤
│                                                     ▒▒▒▒▒▒▒ │
│                                              ▓▓▓▓▓▓▓▒▒▒▒▒▒▒ │
│                                      ▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▒▒▒▒▒▒▒ │
│                       ▒▒▒▒▒▒▒        ▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▒▒▒▒▒▒▒ │
│                ▓▓▓▓▓▓▓▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▒▒▒▒▒▒▒ │
│        ▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▒▒▒▒▒▒▒ │
│ ▓▓▓▓▓▓▓▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▒▒▒▒▒▒▒ │
│ ▓▓▓▓▓▓▓▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▒▒▒▒▒▒▒ │
│ ▓▓▓▓▓▓▓▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▒▒▒▒▒▒▒ │
│ ▓▓▓▓▓▓▓▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▒▒▒▒▒▒▒ │
│       Q1             Q2             Q3             Q4       │
│                                                             │
│ ▓ 2025   ▒ 2026                                             │
╰─────────────────────────────────────────────────────────────╯
```

> [!NOTE]
> Halftone bars round to whole rows/columns, like solid bars do by default (only `style: "fine"` has sub-cell precision), since there's no fractional-height glyph for a shade character like `▒`.

### vbar (ascii style)

`style: "ascii"` is the same idea as halftone, but with plain ASCII characters instead of Unicode shade glyphs — `#`, `X`, `H`, `W`, `=`, `:`, `|`, `.`, in roughly that ink-density order, followed by `@`, `%`, `&`, `$`, `M`, `N`, `D`, `O`, `U`, `S`, `G`, `Z`, `/`, `\`, `!` once there are more than eight series (23 distinct glyphs before the ramp wraps around). This is a closer match to how Bloomberg Businessweek actually built these charts: their "ZINJIN 2014 REVENUE BY PRODUCT" bar tiles `X` for the biggest segment and thins out through `.` and `-` for smaller ones, their "MOBILE DEVICES RUNNING WINDOWS" chart literally repeats `XXX` for one series and `|||` for another with a `XXX Smartphones  ||| Tablets` legend, and "SHARE OF ANALYSTS' RATINGS THAT ARE A BUY" uses `::: Shell  ### Total  ||| BP`. Since it's plain ASCII, it also sidesteps the Unicode block-glyph coverage caveat above entirely — useful if you don't know what font the chart will land in.

```json
{
  "chartType": "vbar",
  "title": "Revenue by quarter (ascii)",
  "border": "rounded",
  "height": 10,
  "style": "ascii",
  "labels": ["Q1", "Q2", "Q3", "Q4"],
  "series": [
    { "name": "2025", "values": [30, 45, 40, 60] },
    { "name": "2026", "values": [35, 50, 55, 70] }
  ]
}
```

```
╭─────────────────────────────────────────────────────────────╮
│                 Revenue by quarter (ascii)                  │
├─────────────────────────────────────────────────────────────┤
│ ,,,,,,,,,,,,,, ,,,,,,,,,,,,,, ,,,,,,,,,,,,,, ,,,,,,,@@@@@@@ │
│ ,,,,,,,,,,,,,, ,,,,,,,,,,,,,, ,,,,,,,,,,,,,, #######@@@@@@@ │
│ ,,,,,,,,,,,,,, ,,,,,,,,,,,,,, ,,,,,,,@@@@@@@ #######@@@@@@@ │
│ ,,,,,,,,,,,,,, ,,,,,,,@@@@@@@ ,,,,,,,@@@@@@@ #######@@@@@@@ │
│ ,,,,,,,,,,,,,, #######@@@@@@@ #######@@@@@@@ #######@@@@@@@ │
│ ,,,,,,,@@@@@@@ #######@@@@@@@ #######@@@@@@@ #######@@@@@@@ │
│ #######@@@@@@@ #######@@@@@@@ #######@@@@@@@ #######@@@@@@@ │
│ #######@@@@@@@ #######@@@@@@@ #######@@@@@@@ #######@@@@@@@ │
│ #######@@@@@@@ #######@@@@@@@ #######@@@@@@@ #######@@@@@@@ │
│ #######@@@@@@@ #######@@@@@@@ #######@@@@@@@ #######@@@@@@@ │
│       Q1             Q2             Q3             Q4       │
│                                                             │
│ # 2025   @ 2026                                             │
╰─────────────────────────────────────────────────────────────╯
```

### vbar (diverging)

Any negative value switches vbar/hbar into a **diverging** chart: instead of every bar growing up from the bottom row, the zero baseline moves to wherever `0` actually falls in the data's range, and bars grow up or down (hbar: left or right) from there — a dashed guide marks the baseline itself. This is exactly the shape of Bloomberg's "MODERN TIMES PREMIUM SUBSCRIBER GROWTH" chart (`## Satellite TV  == Third-party networks`, one series shrinking, the other growing, both sharing one zero line).

```json
{
  "chartType": "vbar",
  "title": "Subscriber growth YoY (diverging)",
  "border": "rounded",
  "height": 10,
  "style": "ascii",
  "labels": ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7"],
  "series": [
    { "name": "Satellite TV", "values": [-6, -8, -5, -9, -7, -4, -8] },
    { "name": "Third-party", "values": [3, 5, 2, 8, 4, 6, 9] }
  ]
}
```

```
╭──────────────────────────────────────────────────╮
│        Subscriber growth YoY (diverging)         │
├──────────────────────────────────────────────────┤
│                                              @@@ │
│                         @@@           @@@    @@@ │
│           @@@           @@@           @@@    @@@ │
│    @@@    @@@    @@@    @@@    @@@    @@@    @@@ │
│    @@@    @@@    @@@    @@@    @@@    @@@    @@@ │
│ ------------------------------------------------ │
│ ###    ###    ###    ###    ###    ###    ###    │
│ ###    ###    ###    ###    ###    ###    ###    │
│ ###    ###           ###    ###           ###    │
│        ###           ###                  ###    │
│   Q1     Q2     Q3     Q4     Q5     Q6     Q7   │
│                                                  │
│ # Satellite TV   @ Third-party                   │
╰──────────────────────────────────────────────────╯
```

> [!NOTE]
> A chart of all-non-negative values renders identically to before (the common case is untouched, byte-for-byte). Values that are all negative anchor at the top row instead of diverging around a visible zero line. Diverging rounds to whole rows/columns, like halftone/ascii — there's no partial-height glyph that fills from either end. Stacked charts diverge too — see the stacked examples below.

### vbar (stacked, diverging)

With `stacked: true`, positive values stack upward from the zero baseline and negative ones stack downward from it. Each side gets rows in proportion to its largest stack, so a small negative side is still visible.

```json
{
  "chartType": "vbar",
  "title": "Cash flow by quarter (stacked)",
  "border": "rounded",
  "height": 12,
  "stacked": true,
  "style": "ascii",
  "labels": [
    "Q1",
    "Q2",
    "Q3",
    "Q4"
  ],
  "series": [
    {
      "name": "Product",
      "values": [
        30,
        45,
        25,
        60
      ]
    },
    {
      "name": "Services",
      "values": [
        15,
        20,
        18,
        25
      ]
    },
    {
      "name": "Refunds",
      "values": [
        -12,
        -20,
        -30,
        -5
      ]
    }
  ]
}
```

```
╭─────────────────────────────────────────────────────────────╮
│               Cash flow by quarter (stacked)                │
├─────────────────────────────────────────────────────────────┤
│                                              @@@@@@@@@@@@@@ │
│                                              @@@@@@@@@@@@@@ │
│                @@@@@@@@@@@@@@                ############## │
│                @@@@@@@@@@@@@@                ############## │
│ @@@@@@@@@@@@@@ ############## @@@@@@@@@@@@@@ ############## │
│ ############## ############## @@@@@@@@@@@@@@ ############## │
│ ############## ############## ############## ############## │
│ ############## ############## ############## ############## │
│ ----------------------------------------------------------- │
│ %%%%%%%%%%%%%% %%%%%%%%%%%%%% %%%%%%%%%%%%%% %%%%%%%%%%%%%% │
│                %%%%%%%%%%%%%% %%%%%%%%%%%%%%                │
│                               %%%%%%%%%%%%%%                │
│       Q1             Q2             Q3             Q4       │
│                                                             │
│ # Product   @ Services   % Refunds                          │
╰─────────────────────────────────────────────────────────────╯
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
│ Firefox │ ██████████████░░░░░░░░░░░░░░░░░░░░░░░░░░ 21 │
│ Safari  │ ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 12 │
│ Other   │ ███░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 5  │
└───────────────────────────────────────────────────────┘
```

The light `░` behind each bar is a background **track**: the rest of the 0..max scale, so a short bar's true size is visible at a glance instead of fading into blank space. It's on by default for `solid`/`fine` hbar and vbar (single or grouped, not stacked or diverging — those have no single "rest of the axis" to shade) and never shows up in `halftone`/`ascii`, which already have their own texture.

### hbar (fine style)

By default bars end on whole character cells, which looks the same in every font. `style: "fine"` ends each bar with an eighth-block glyph (`▏▎▍▌▋▊▉`) for sub-cell precision — sharper when values are close — but those glyphs are missing from Consolas and Courier New, where they make the right edge of the chart ragged (see the note above). Single-series vertical bars and histograms take the same style (a vbar with several series draws each series with its own fill glyph, always in whole rows).

```json
{
  "chartType": "hbar",
  "title": "Browser share (fine)",
  "border": "light",
  "style": "fine",
  "labels": [
    "Chrome",
    "Firefox",
    "Safari",
    "Other"
  ],
  "series": [
    {
      "values": [
        62,
        21,
        12,
        5
      ]
    }
  ]
}
```

```
┌───────────────────────────────────────────────────────┐
│                 Browser share (fine)                  │
├───────────────────────────────────────────────────────┤
│ Chrome  │ ████████████████████████████████████████ 62 │
│ Firefox │ █████████████▌░░░░░░░░░░░░░░░░░░░░░░░░░░ 21 │
│ Safari  │ ███████▋░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 12 │
│ Other   │ ███▏░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 5  │
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

### hbar (halftone, stacked)

Halftone applies the same way to hbar — including stacked segments, where each series already got its own glyph (`fills`), just swapped for the lighter `halftoneFills` ramp.

```json
{
  "chartType": "hbar",
  "title": "Revenue by region (halftone)",
  "border": "light",
  "stacked": true,
  "style": "halftone",
  "labels": ["EMEA", "APAC", "Americas"],
  "series": [
    { "name": "Product", "values": [40, 25, 55] },
    { "name": "Services", "values": [15, 20, 18] }
  ]
}
```

```
┌────────────────────────────────────────────────────────┐
│              Revenue by region (halftone)              │
├────────────────────────────────────────────────────────┤
│ EMEA     │ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▒           55 │
│ APAC     │ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▒▒▒▒                45 │
│ Americas │ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▒▒▒ 73 │
│                                                        │
│ ▓ Product   ▒ Services                                 │
└────────────────────────────────────────────────────────┘
```

### hbar (ascii style)

Single-series bars all use the same glyph (`#`, the densest in the ramp); grouped/stacked series each get their own, so — just like Bloomberg's charts — they stay distinguishable from each other in a plain-text agent reply with no color at all.

```json
{
  "chartType": "hbar",
  "title": "Data center switching market share",
  "border": "light",
  "style": "ascii",
  "labels": ["Cisco", "HPE", "Arista", "Huawei", "Juniper", "Dell", "Lenovo", "Brocade"],
  "series": [{ "values": [61, 9, 6, 4, 4, 4, 3, 2] }]
}
```

```
┌───────────────────────────────────────────────────────┐
│          Data center switching market share           │
├───────────────────────────────────────────────────────┤
│ Cisco   | ######################################## 61 │
│ HPE     | ######,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,, 9  │
│ Arista  | ####,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,, 6  │
│ Huawei  | ###,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,, 4  │
│ Juniper | ###,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,, 4  │
│ Dell    | ###,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,, 4  │
│ Lenovo  | ##,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,, 3  │
│ Brocade | #,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,, 2  │
└───────────────────────────────────────────────────────┘
```

```json
{
  "chartType": "hbar",
  "title": "Share of analysts' ratings that are a buy",
  "border": "light",
  "style": "ascii",
  "labels": ["04/01/15", "06/01/15", "08/01/15", "10/01/15"],
  "series": [
    { "name": "Shell", "values": [22, 25, 24, 30] },
    { "name": "Total", "values": [34, 30, 32, 30] },
    { "name": "BP", "values": [15, 12, 18, 22] }
  ]
}
```

```
┌───────────────────────────────────────────────────────┐
│       Share of analysts' ratings that are a buy       │
├───────────────────────────────────────────────────────┤
│ 04/01/15                                              │
│   Shell | ##########################,,,,,,,,,,,,,, 22 │
│   Total | @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ 34 │
│   BP    | %%%%%%%%%%%%%%%%%%,,,,,,,,,,,,,,,,,,,,,, 15 │
│                                                       │
│ 06/01/15                                              │
│   Shell | #############################,,,,,,,,,,, 25 │
│   Total | @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@,,,,, 30 │
│   BP    | %%%%%%%%%%%%%%,,,,,,,,,,,,,,,,,,,,,,,,,, 12 │
│                                                       │
│ 08/01/15                                              │
│   Shell | ############################,,,,,,,,,,,, 24 │
│   Total | @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@,, 32 │
│   BP    | %%%%%%%%%%%%%%%%%%%%%,,,,,,,,,,,,,,,,,,, 18 │
│                                                       │
│ 10/01/15                                              │
│   Shell | ###################################,,,,, 30 │
│   Total | @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@,,,,, 30 │
│   BP    | %%%%%%%%%%%%%%%%%%%%%%%%%%,,,,,,,,,,,,,, 22 │
└───────────────────────────────────────────────────────┘
```

### hbar (ascii, many series)

Past eight series the ramp continues with heavier and lighter characters, so a dozen stacked series are still told apart with no color and no Unicode. A long legend wraps at 100 columns instead of stretching the frame.

```json
{"chartType": "hbar", "title": "Traffic by channel (12 series)", "border": "light", "style": "ascii", "stacked": true, "width": 48, "labels": ["EMEA", "APAC", "Americas"], "series": [{"name": "Direct", "values": [9, 9, 9]}, {"name": "Search", "values": [9, 11, 10]}, {"name": "Email", "values": [9, 8, 11]}, {"name": "Social", "values": [10, 11, 13]}, {"name": "Referral", "values": [6, 8, 7]}, {"name": "Ads", "values": [7, 6, 9]}, {"name": "Affiliate", "values": [7, 8, 10]}, {"name": "Video", "values": [8, 6, 5]}, {"name": "Podcast", "values": [4, 8, 6]}, {"name": "Events", "values": [5, 6, 8]}, {"name": "Print", "values": [5, 3, 9]}, {"name": "Other", "values": [6, 6, 4]}]}
```

```
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                  Traffic by channel (12 series)                                   │
├───────────────────────────────────────────────────────────────────────────────────────────────────┤
│ EMEA     | ####@@@@%%%%&&&&&$$$WWWMMMNNNNHHDDDGGUUU         85                                    │
│ APAC     | ####@@@@@%%%%&&&&&$$$$WWWMMMMNNNHHHHDDDGUUU      90                                    │
│ Americas | ####@@@@@%%%%%&&&&&&$$$WWWWMMMMMNNNHHHDDDDGGGGUU 101                                   │
│                                                                                                   │
│ # Direct   @ Search   % Email   & Social   $ Referral   W Ads   M Affiliate   N Video   H Podcast │
│ D Events   G Print   U Other                                                                      │
└───────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### hbar (diverging)

```json
{
  "chartType": "hbar",
  "title": "Estimated sales growth (diverging)",
  "border": "light",
  "labels": ["ABB", "Aetna", "Apple", "Bankers Pet.", "Biogen"],
  "series": [{ "values": [-8.2, 4.9, 27.6, -42.8, 7.8] }]
}
```

```
┌────────────────────────────────────────────────────────────────┐
│               Estimated sales growth (diverging)               │
├────────────────────────────────────────────────────────────────┤
│ ABB          │                    █████¦                -8.20  │
│ Aetna        │                         ¦███             4.90   │
│ Apple        │                         ¦███████████████ 27.60  │
│ Bankers Pet. │ ████████████████████████¦                -42.80 │
│ Biogen       │                         ¦████            7.80   │
└────────────────────────────────────────────────────────────────┘
```

The `|` marks the zero column on any bar that doesn't already reach it (a bar that does reach zero starts right there, no separate marker needed).

### hbar (stacked, diverging)

The same idea sideways: positives stack right, negatives stack left, first series nearest zero on both sides. The number at the end of each row is the net total.

```json
{
  "chartType": "hbar",
  "title": "Revenue vs refunds by region",
  "border": "light",
  "stacked": true,
  "width": 40,
  "labels": [
    "EMEA",
    "APAC",
    "Americas"
  ],
  "series": [
    {
      "name": "Product",
      "values": [
        40,
        25,
        55
      ]
    },
    {
      "name": "Refunds",
      "values": [
        -15,
        -20,
        -8
      ]
    }
  ]
}
```

```
┌────────────────────────────────────────────────────────┐
│              Revenue vs refunds by region              │
├────────────────────────────────────────────────────────┤
│ EMEA     │   ▓▓▓▓▓▓▓▓¦█████████████████████         25 │
│ APAC     │ ▓▓▓▓▓▓▓▓▓▓¦█████████████                 5  │
│ Americas │       ▓▓▓▓¦█████████████████████████████ 47 │
│                                                        │
│ █ Product   ▓ Refunds                                  │
└────────────────────────────────────────────────────────┘
```

### line

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

`threshold` overlays a dashed reference line at a fixed y-value (e.g. an SLA or target); `showPoints` marks each actual data point with a bold dot, and — since a solid block clashes with round point markers — switches the connecting line itself to a thin centered dot (`·`) instead of `█`.

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
│    60 ┤                                   ··●·                      │
│ 54.29 ┤                               ·●··    ··                    │
│ 48.57 ┤- - - - - - - - - - - - - - -·· - - - - -·●·- - - - - - - -  │
│ 42.86 ┤                    ·●··   ··               ···              │
│ 37.14 ┤                  ··    ··●                    ·●··          │
│ 31.43 ┤               ·●·                                 ··●··     │
│ 25.71 ┤   ··●··    ···                                         ···● │
│    20 ┤●··     ··●·                                                 │
│                                                                     │
│ - - threshold: 50                                                   │
└─────────────────────────────────────────────────────────────────────┘
```

### line (labelled thresholds)

`thresholds` draws several reference lines at once — a target and an SLA, a budget and a hard limit. Each is a number or a `{value, label}` object; the scale stretches to take them all in, and each is named with its exact value to the right of the plot, on its own row, so the names never cover the data. (A line sits on the nearest row; the note keeps the precise value.)

```json
{
  "chartType": "line",
  "title": "Latency p99 (ms)",
  "height": 10,
  "showPoints": true,
  "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
  "thresholds": [
    { "value": 106, "label": "target" },
    { "value": 140, "label": "SLA" }
  ],
  "series": [{ "values": [92, 98, 120, 131, 112, 101, 95] }]
}
```

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│                                 Latency p99 (ms)                                  │
├───────────────────────────────────────────────────────────────────────────────────┤
│    140 ┤- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -   SLA: 140    │
│ 134.67 ┤                                                                          │
│ 129.33 ┤                           ··●·                                           │
│    124 ┤                      ·····    ···                                        │
│ 118.67 ┤                  ·●··            ····                                    │
│ 113.33 ┤                ··                    ·●··                                │
│    108 ┤- - - - - - -···- - - - - - - - - - - - - ····· - - - - - -   target: 106 │
│ 102.67 ┤           ··                                  ··●····                    │
│  97.33 ┤     ····●·                                           ·····●              │
│     92 ┤●····                                                                     │
│         Mon     Tue       Wed       Thu       Fri       Sat      Sun              │
└───────────────────────────────────────────────────────────────────────────────────┘
```

### line (dotted style, Bloomberg-inspired)

`style: "dotted"` replaces the solid connecting stroke with a sparse `+`-plotted trace — every other pixel along the path — which is exactly how the trend lines look in Bloomberg Businessweek's [Year Ahead 2016](https://www.bloomberg.com/graphics/year-ahead-2016/) ASCII graphics (the "APPLE REVENUE" chart there plots iPhone revenue the same way, `+` marks and all). Independent of `showPoints`/`pointChar`.

```json
{
  "chartType": "line",
  "title": "Apple revenue",
  "height": 10,
  "width": 50,
  "style": "dotted",
  "series": [{ "name": "iPhone", "values": [15, 16, 17.5, 19, 20, 21.5, 23, 24.5, 26, 27.5, 29, 30] }]
}
```

```
┌───────────────────────────────────────────────────────────┐
│                       Apple revenue                       │
├───────────────────────────────────────────────────────────┤
│    30 ┤                                                ++ │
│ 28.33 ┤                                       ++ + + +    │
│ 26.67 ┤                                 + + +             │
│    25 ┤                              ++                   │
│ 23.33 ┤                        + + +                      │
│ 21.67 ┤                     ++                            │
│    20 ┤               + + +                               │
│ 18.33 ┤            ++                                     │
│ 16.67 ┤  + + + + +                                        │
│    15 ┤+                                                  │
└───────────────────────────────────────────────────────────┘
```

### area (single series)

Fills the region between the line and a zero baseline, interpolating between data points so the fill has no gaps — inspired by Bloomberg's "cumulative flows" chart, which fills its negative "actively managed" region below zero the same way this fills below a falling line.

```json
{
  "chartType": "area",
  "title": "Actively managed fund flows",
  "height": 8,
  "series": [{ "values": [20, 10, -20, -60, -120, -180, -260, -340, -420, -520, -600] }]
}
```

```
┌────────────────────────────────────────────────────────────────────┐
│                    Actively managed fund flows                     │
├────────────────────────────────────────────────────────────────────┤
│  100 ┤                                                             │
│    0 ┤████████████████████████████████████████████████████████████ │
│ -100 ┤                 ███████████████████████████████████████████ │
│ -200 ┤                           █████████████████████████████████ │
│ -300 ┤                                   █████████████████████████ │
│ -400 ┤                                           █████████████████ │
│ -500 ┤                                                 ███████████ │
│ -600 ┤                                                        ████ │
└────────────────────────────────────────────────────────────────────┘
```

Like line, `area` picks up `style: "halftone"`/`"ascii"` for the fill glyph, and multiple overlaid series are told apart with a shade/letter per series (the first series painted on top of the rest wherever they overlap).

### area (stacked)

`stacked: true` bands series cumulatively from zero instead of overlaying them — each series' own contribution to the running total, not its raw value, is what's visible at any point.

```json
{
  "chartType": "area",
  "title": "Mobile data traffic (stacked)",
  "height": 8,
  "stacked": true,
  "style": "ascii",
  "labels": ["2014", "2015", "2016", "2017", "2018", "2019"],
  "series": [
    { "name": "Other", "values": [1, 2, 3, 5, 8, 12] },
    { "name": "Video", "values": [0.2, 0.4, 0.8, 1.5, 2.5, 4] }
  ]
}
```

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Mobile data traffic (stacked)                    │
├─────────────────────────────────────────────────────────────────────┤
│    16 +                                                         ::: │
│ 13.71 +                                                     ::::::: │
│ 11.43 +                                                 ::::::::### │
│  9.14 +                                           ::::::########### │
│  6.86 +                                     ::::::################# │
│  4.57 +                             ::::::::####################### │
│  2.29 +                 ########################################### │
│     0 +############################################################ │
│        2014     2015        2016        2017        2018       2019 │
│                                                                     │
│ # Other   : Video                                                   │
└─────────────────────────────────────────────────────────────────────┘
```

### area (stacked, diverging)

Stacked areas share one axis: the labelled range spans the largest positive stack down to the largest negative one.

```json
{
  "chartType": "area",
  "title": "Inflows vs outflows",
  "border": "light",
  "height": 9,
  "width": 40,
  "stacked": true,
  "style": "ascii",
  "series": [
    {
      "name": "In",
      "values": [
        1,
        3,
        5,
        4,
        6
      ]
    },
    {
      "name": "Out",
      "values": [
        -1,
        -2,
        -4,
        -3,
        -1
      ]
    }
  ]
}
```

```
┌─────────────────────────────────────────────────┐
│               Inflows vs outflows               │
├─────────────────────────────────────────────────┤
│  6.58 +                                     ### │
│  5.26 +                  #######       ######## │
│  3.95 +             ########################### │
│  2.63 +        ################################ │
│  1.32 +   ##################################### │
│     0 +######################################## │
│ -1.32 +:::::::::::::::::::::::::::::::::::::::: │
│ -2.63 +          :::::::::::::::::::::::::      │
│ -3.95 +                 ::::::::::              │
│                                                 │
│ # In   : Out                                    │
└─────────────────────────────────────────────────┘
```

### dotplot

A Cleveland dot plot: one row per category, a marker at each series' value, connected to the left edge by a light leader line. Unlike vbar/hbar, the value axis zooms to the data's actual range instead of always including 0 — position carries the value, not a filled run's length. This mirrors Bloomberg's "2016 APARTMENT RENT GROWTH FORECAST" chart (city names positioned along a percentage axis with dashed leader lines).

```json
{
  "chartType": "dotplot",
  "title": "2016 apartment rent growth forecast",
  "width": 30,
  "labels": ["Oakland", "San Francisco", "Seattle", "Denver", "Chicago", "Detroit"],
  "series": [{ "values": [5.2, 4.8, 4.4, 3.6, 2.8, 2.2] }]
}
```

```
┌─────────────────────────────────────────────────────┐
│         2016 apartment rent growth forecast         │
├─────────────────────────────────────────────────────┤
│ Oakland       │ ·····························● 5.20 │
│ San Francisco │ ·························●···· 4.80 │
│ Seattle       │ ·····················●········ 4.40 │
│ Denver        │ ··············●··············· 3.60 │
│ Chicago       │ ······●······················· 2.80 │
│ Detroit       │ ●····························· 2.20 │
│ value axis: [2.20, 5.20]                            │
└─────────────────────────────────────────────────────┘
```

With more than one series, every category overlays one marker per series on the same row — each series gets its own shape (`●`, `○`, `▲`, `■`, …), same ramp as scatter's markers — and the trailing per-row value is dropped in favor of a legend, since a single number wouldn't say which series it belonged to.

### scatter (two groups)

Each series gets its own marker shape (`●`, `○`, `▲`, `■`, …), so groups are distinguishable at a glance without needing color.

```json
{
  "chartType": "scatter",
  "title": "Height vs weight",
  "width": 40,
  "height": 14,
  "series": [
    { "name": "group A", "points": [{ "x": 158, "y": 52 }, { "x": 160, "y": 55 }, { "x": 162, "y": 54 }, { "x": 165, "y": 60 }, { "x": 167, "y": 58 }, { "x": 170, "y": 65 }, { "x": 172, "y": 68 }, { "x": 163, "y": 62 }] },
    { "name": "group B", "points": [{ "x": 175, "y": 80 }, { "x": 178, "y": 78 }, { "x": 180, "y": 85 }, { "x": 183, "y": 88 }, { "x": 185, "y": 90 }, { "x": 182, "y": 82 }, { "x": 188, "y": 92 }, { "x": 177, "y": 86 }] }
  ]
}
```

```
┌──────────────────────────────────────────┐
│             Height vs weight             │
├──────────────────────────────────────────┤
│                                        ○ │
│                                  ○ ○     │
│                          ○   ○           │
│                                ○         │
│                       ○                  │
│                           ○              │
│                                          │
│                                          │
│                   ●                      │
│                 ●                        │
│        ● ●                               │
│             ●                            │
│    ● ●                                   │
│ ●                                        │
│ x: [158, 188]  y: [52, 92]               │
│ ● group A   ○ group B                    │
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
║ 20..28 │ █████████████████████████████████        5 ║
║ 28..36 │ ████████████████████                     3 ║
║ 36..44 │ ███████                                  1 ║
║ 44..52 │                                          0 ║
║ 52..60 │ █████████████                            2 ║
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
┌──────────────────────────────────────────────────────────────────┐
│                         Traffic by hour                          │
├──────────────────────────────────────────────────────────────────┤
│         Mon         Tue         Wed         Thu         Fri      │
│ 9am ░░░░░░░░░░░ ░░░░░░░░░░░ ░░░░░░░░░░░ ▒▒▒▒▒▒▒▒▒▒▒ ░░░░░░░░░░░  │
│ 1pm ▒▒▒▒▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▓▓▓▓ ▓▓▓▓▓▓▓▓▓▓▓ ▓▓▓▓▓▓▓▓▓▓▓ ▒▒▒▒▒▒▒▒▒▒▒  │
│ 5pm ███████████ ▓▓▓▓▓▓▓▓▓▓▓ ███████████ ███████████ ███████████  │
│                                                                  │
│ ░ 20..38.75   ▒ 38.75..57.50   ▓ 57.50..76.25   █ 76.25..95      │
└──────────────────────────────────────────────────────────────────┘
```

Without `width` the cells widen to fill a 60-character grid; with many columns they stay at least 3 characters wide. With `"useColor": "on"` cells render as colored `███` blocks along a blue→red ANSI 256 ramp instead of the `" ░▒▓█"` shade ladder.

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
│ Class A │             ├──────███████║██████─────────────┤     min=55 q1=62.75 med=71 q3=78.75 max=95 │
│ Class B │ ├──────────────█████║█████───────────────────────┤  min=40 q1=58.50 med=64 q3=69.50 max=99 │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Boxplot values are computed automatically from the raw sample population you pass in — you don't precompute quartiles yourself.
