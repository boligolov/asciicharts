# asciicharts principles v1.0

*The principles of text charts* — version 1.0, 2026-09-24. Licensed under CC BY 4.0.

This document is the distilled knowledge behind `asciicharts`: how to turn numbers into a chart made of
characters, what every rule is for, which calculations produce which cells, and which mistakes we made on
the way. It is written for two readers:

- **An agent that must draw a chart without running code.** Sections 1–6 give the rules, section 13 is
  a step-by-step procedure with a self-check.
- **An engineer (or agent) re-implementing the renderer in another language** — Rust, Go, TypeScript.
  Sections 4–9 are the specification, sections 11–12 are what went wrong and what is still a
  trade-off, section 14 is the porting checklist.

Every example output in this document is real output of `asciicharts.py`, not a drawing.

**Contents:** 0 Status and conformance · 1 The medium · 2 The glyph alphabet · 3 Identity without color ·
4 From numbers to cells · 5 Layout · 6 Text · 7 The twelve chart types · 8 Styles · 9 Input, limits and
errors · 10 Other media · 11 Mistakes we made · 12 Limitations and choices · 13 Drawing by hand ·
14 Porting checklist · 15 The requirements

---

## 0. Status and conformance

**Version.** asciicharts principles **v1.0**, published 2026-09-24. Every change to how a chart is drawn is
a new version, recorded in `spec/CHANGELOG.md` of the asciicharts repository
(https://github.com/boligolov/asciicharts), together with regenerated conformance outputs.

**Licence.** The principles and the conformance suite are licensed under the Creative Commons Attribution
4.0 International License (CC BY 4.0, https://creativecommons.org/licenses/by/4.0/): copy, adapt and build
on them, commercially too, with credit — *"asciicharts principles v1.0" by asciicharts contributors*. The
reference implementations are MIT-licensed code.

**Key words.** "MUST", "MUST NOT", "SHOULD", "SHOULD NOT" and "MAY" in section 15 are to be interpreted as
described in RFC 2119 and RFC 8174 when, and only when, they appear in capitals. Sections 1–14 are
informative: they explain, derive and illustrate; section 15 and the conformance suite are normative.

**Two kinds of conformance.**

1. **A renderer** conforms to v1.0 when it reproduces the conformance suite — `spec/conformance/` in the
   repository: 317 specs with their exact output or error message, and the 31 documented examples —
   **byte for byte**. Sections 4–9 describe the arithmetic and layout the suite pins down; where prose
   and suite disagree, the suite wins and the prose is a bug.
2. **A chart**, however it was made — by a renderer, another library, or an agent drawing by hand —
   follows the principles when it meets every MUST of section 15. That is the standard section 13's
   hand-drawing recipes aim for; exact byte equality with the reference output is not required of it.

---

## 1. The medium: a grid of character cells

A text chart is a rectangle of **cells**. Each cell holds exactly one glyph, every cell has the same
width, and a row is a line of text. Everything else follows from these facts.

**1.1 A cell is about twice as tall as it is wide.** Monospace fonts have an advance width of roughly
0.6 em and a line height of about 1.2 em, so one row is about as tall as two columns are wide. Anything
that must look round or square compensates:

- a pie chart scales vertical distances by 2 (`PIE_ASPECT = 2.0`);
- a default pie is 44 columns × 22 rows, and one row is worth two columns (`width = height × 2`);
- a heatmap cell is at least 3 columns wide × 1 row, close to a square.

**1.2 Resolution is coarse, and quantisation is the main source of error.** A plot `H` rows tall can show
`H` distinct heights. A value maps to the nearest row, so the worst positional error is half a row:
`(hi − lo) / (2 × (H − 1))` in data units. That is why every chart that loses precision to the grid
also prints the exact value in text (bar value labels, threshold notes, boxplot statistics, dotplot and
scatter ranges). **The cells show the shape; the numbers carry the precision.**

**1.3 The output contract.**

- Plain text, `\n` line endings, no tabs.
- With a frame, **every line has the same display width** (section 6). This is the property a reader
  notices first when it breaks: a crooked right border.
- **Deterministic:** the output is a pure function of the spec. No clock, no randomness, no terminal
  size detection, no locale. The same spec gives the same bytes on every machine, so outputs can be
  snapshotted, diffed and compared across implementations.
- Without a frame (`border: "none"`), lines keep the width they were drawn with; trailing spaces inside
  a plot are part of it and are not stripped (only the x-axis label row is right-trimmed).

**1.4 A chart is read in a monospace context.** Terminals, code blocks in Markdown/chat, logs, commit
messages, PR descriptions. When you paste a chart into Markdown, put it in a fenced code block, or the
proportional font and whitespace collapsing destroy it.

---

## 2. The glyph alphabet

### 2.1 Font safety is the first constraint

A monospace font that lacks a glyph does not show a box: the renderer (terminal, editor, browser)
silently **borrows that one glyph from another font** whose advance width differs. The text is still
correct, every line still has the same number of characters, but the right edge of the chart goes
ragged. Readers blame the chart. So the alphabet is chosen by what the *weakest common fonts* contain —
Consolas, Courier New and Lucida Console, the defaults of many Windows editors.

| tier | glyphs | status |
|---|---|---|
| 0 — ASCII | printable U+0020–U+007E | always safe |
| 1 — safe Unicode | Latin-1 (U+00A0–U+00FF, includes `·` and `¦`), the **WGL4** box drawing: light and double lines only (`─│┌┐└┘├┤┬┴┼` and `═║╔╗╚╝╠╣╦╩╬` …), the shades `░▒▓█`, the half blocks `▌▄▐▀`, the markers `●○▲■□▼♦◊►◄` | the default alphabet |
| 2 — needs a capable font | heavy (`━┃┏┓`), rounded (`╭╮╰╯`) and dashed box drawing; eighth blocks `▁▂▃▄▅▆▇` (vertical) and `▏▎▍▋▊▉` (horizontal); quadrants; braille | only on request (`border: "heavy"`/`"rounded"`, `style: "fine"`) and in sparklines, documented as such |

Rules that come out of this:

- **Bars end on whole cells by default.** Eighth-block bar ends are opt-in (`style: "fine"`).
- **No sub-cell canvas.** We once had quadrant and braille modes for lines and scatter (4 or 8 dots per
  cell). They were removed: the glyphs are missing from common fonts, and a braille dot cannot carry a
  per-series shape, so series could only be told apart by color.
- **Sparklines are the one default exception**: a one-line trend needs eighth-height ticks
  `▁▂▃▄▅▆▇█` to have any vertical resolution at all. Document it.
- A test walks the whole golden corpus and fails if any default output contains a glyph outside tier 0–1.
  "Box drawing is safe" is not precise enough: the fonts cover the WGL4 subset, and the test checks that
  set (it caught the boxplot median, once a heavy `┃`, now `║`).

### 2.2 Ink density: shades are a ramp, not decoration

Each glyph covers a fraction of its cell with ink. Order glyphs by that fraction and you have a ramp:

| glyph | ` ` | `░` | `▒` | `▓` | `█` |
|---|---|---|---|---|---|
| ink | 0% | ~25% | ~50% | ~75% | 100% |

- **Magnitude** (heatmap cells) uses the ramp in order: `SHADES = [" ", "░", "▒", "▓", "█"]`.
- **Series identity** uses glyphs that are *far apart* in density or texture, so neighbours are distinct:
  `FILLS = ["█", "▓", "▒", "░", "▌", "▄", "▐", "▀"]`. The first four are the shade ramp from the dense end;
  the half blocks (≈50% ink with a direction: left, bottom, right, top) extend it to eight series.
- **The first series gets the densest glyph** (`█`, or `#` in ASCII). A single series is always a plain
  solid bar; shading appears only when there is something to distinguish.
- **Halftone style** starts one step lighter: `HALFTONE_FILLS = ["▓", "▒", "░", "▌", "▄", "▐", "▀", ":"]`.

**The ASCII density ramp** (style `ascii`), 23 glyphs ordered dense to light, so the first series are the
most distinct from each other:

```
# @ % & $ W M N H D G U O S Z X = / \ : ; ! '
```

`#` leads regardless of exact rank because it plays the role of `█`. Area charts swap `@` and `:`
(`AREA_ASCII_FILLS`): stacked areas often put thin bands on a big first band, and a light second glyph
reads better there. With more series than glyphs, the ramp wraps around. The ramp holds none of the ascii
style's structural glyphs (`|` separator, `.` connector, `,` track, `+` axis, `-` dashes): its light end
is `; ! '`, not `| ! .`, which it once was.

### 2.3 Every glyph has exactly one role per chart

A reader decodes a chart by glyph. If one glyph means two things, the chart lies. The roles:

| role | Unicode | ASCII | notes |
|---|---|---|---|
| bar / area fill, series *i* | `FILLS[i]` | `ASCII_FILLS[i]` | legend swatch is the same glyph |
| bar track (background) | `░`, or `▒` if the bar itself is `░` | `,` | see 2.4 |
| line stroke, single series | `█` | `#` | full-cell stroke |
| line stroke, series *i* of many | `FILLS[i]` | `ASCII_FILLS[i]` | |
| line connector with point markers | `·` | `.` | thin, so markers stand out |
| dotted line | `+` on every other cell | | |
| point marker, series *i* | `●○▲■□▼♦◊►◄` | `o x * + ^ v @ % & $` | |
| threshold / reference line | `-` on even columns | `-` | |
| zero baseline (diverging vbar) | `-` across the whole row | `-` | owned by no bar |
| zero axis (diverging hbar) | `¦` | `+` | owned by no bar; not the separator |
| label / plot separator | `│` | `\|` | |
| y-axis tick | `┤` (left), `├` (right axis) | `+` | |
| dotplot background | `·` | | |
| markers of different series in one cell (scatter, dotplot) | `*` | | legend adds `* overlap` |
| boxplot | `─` whisker, `█` box, `├` min, `┤` max, `║` median | | |

The ASCII track glyph is a comma precisely because a comma is used nowhere else — not in the ramp, not
as a marker, not as the connector `.`. A test enforces it.

### 2.4 The track

A short bar fades into blank space, and the eye cannot tell how short it is. So the unused part of each
bar, up to the chart's own `0..max` scale, is drawn with a light **track** glyph, like the background of
a progress bar:

```
Chrome  │ ████████████████████ 62
Firefox │ ███████░░░░░░░░░░░░░ 21
Safari  │ ████░░░░░░░░░░░░░░░░ 12
```

- On for single and grouped hbar/vbar in styles `solid`, `fine`, `ascii`.
- Off for stacked and diverging bars (there is no single "rest of the axis"), for `halftone` (already
  textured) and for histograms.
- A zero value is drawn as all track: the bar exists, it is empty.
- The track glyph must never equal the bar's own glyph (grouped vbar's 4th series is `░`, so its track is
  `▒`).

### 2.5 Borders

Six styles. A frame is (top-left, top-right, bottom-left, bottom-right, horizontal, vertical,
left-T, right-T):

| style | glyphs |
|---|---|
| `light` (default) | `┌ ┐ └ ┘ ─ │ ├ ┤` |
| `rounded` | `╭ ╮ ╰ ╯ ─ │ ├ ┤` |
| `heavy` | `┏ ┓ ┗ ┛ ━ ┃ ┣ ┫` |
| `double` | `╔ ╗ ╚ ╝ ═ ║ ╠ ╣` |
| `ascii` | `+ + + + - \| + +` |
| `none` | no frame; a title becomes a plain first line |

`light` (the default), `double` and `ascii` are safe everywhere; `heavy` and `rounded` need a tier-2 font
(section 2.1) and are opt-in for that reason.

---

## 3. Identity without color

**3.1 Color is additive, never required.** Every series is distinguishable by glyph alone, because
charts end up in places with no color: logs, emails, screen readers' text, monochrome terminals,
colorblind readers, an LLM's context. Color (`useColor: "on"`) paints the same glyphs; it never replaces
them. The default is off (`auto` means off): output usually goes to an agent or a file, not a TTY.

**3.2 The legend swatch is the exact glyph the series is drawn with**, in series order, followed by the
name: `█ Product   ▓ Refunds`. Entries are joined by three spaces and wrap to a new line before
exceeding 100 columns, so a legend of 23 series never stretches the frame.

**3.3 When color is on:** ANSI 256-color foreground, `ESC[38;5;<n>m` … `ESC[0m`, reset after every
colored run (never let color leak to the next cell or line).

| use | palette (xterm-256 indexes) |
|---|---|
| series *i* | `[39, 208, 40, 201, 51, 226]` — blue, orange, green, magenta, cyan, yellow, cycling |
| heatmap | 16 steps blue → red: `[21, 27, 33, 39, 45, 51, 87, 123, 159, 195, 226, 220, 214, 208, 202, 196]` |
| thresholds | `244` (grey) |

Escape sequences have zero display width; strip them before measuring (section 6). These colors are
tuned for dark backgrounds; on a light page they need darkening (the website applies
`brightness(0.62) saturate(1.35)`).

---

## 4. From numbers to cells: the arithmetic

### 4.1 Two primitives that must be exact

**Rounding is half away from zero**, not banker's rounding:

```
round(x) = trunc(x) + sign(x)   if |x − trunc(x)| ≥ 0.5
         = trunc(x)             otherwise
```

Python's `round()` rounds half to even (`round(2.5) == 2`); the renderer was ported from Go, whose
`math.Round` rounds away (`3`). A cell is either filled or not, so a different rounding rule changes
pictures. Pick one rule, write it down, use it everywhere.

**Sums are plain left-to-right float additions.** Python 3.12's `sum()` is compensated and can differ
from a naive loop in the last bit, which is enough to flip a rounding decision. Same reason, same fix.

Integer positions use floor division on non-negative integers (`i × (W − 1) // (n − 1)`).

### 4.2 The scale (domain) depends on what the mark encodes

| chart | domain | why |
|---|---|---|
| bars (hbar, vbar, histogram), non-negative | `0 .. max` | **length encodes value**: a bar that doesn't start at zero lies |
| bars with a negative value | `min(0, data) .. max(0, data)` | both directions from a real zero |
| stacked bars | `0 .. max column total` (and the negative side's own max) | the whole stack is the value |
| line, dual_axis (each axis) | `min .. max` of the data, extended to include every threshold | position encodes value; zooming is honest because the axis is labelled |
| area, overlaid | `min(0, data) .. max(0, data)` | area encodes volume from zero |
| scatter | x and y each `min .. max` | |
| dotplot | `min .. max` (does **not** start at 0) | differences between close values; the range is printed |
| heatmap | `min .. max` of the whole matrix | |
| sparkline | each series its own `min .. max` | shape only |
| boxplot | global `min .. max` across groups | groups comparable |

**Zero on a row.** When a line, area or dual_axis range crosses zero, it is widened just enough that 0
falls exactly on a row: try every inner row `z` for zero, take the one needing the smallest step
`max(hi / z, −lo / (H − 1 − z))`, and set `lo = −step × (H − 1 − z)`, `hi = step × z`. The baseline row
is then labelled `0` (it used to read `0.50`), every row is a multiple of one step, and a zero value
lands on it. Data `−3 … 7` on 6 rows becomes `−4.67 … 7`; a range that doesn't cross zero is untouched.

**A degenerate domain** (`hi == lo`, all values equal) becomes `v − 1 .. v + 1`: nothing divides by
zero, and a flat series sits in the middle of the plot (a flat sparkline is `▄▄▄`) instead of on an edge.
Printed ranges (dotplot, scatter) still show the data's own `[v, v]`, never the padded one. Bars are the
exception: they always start at zero, so only all-zero bar data needs a range, `0 .. 1`.

### 4.3 Mapping a value to a row or column

Rows are numbered from the top (`0`) to the bottom (`H − 1`).

```
y_row(v)   = round((1 − (v − lo) / (hi − lo)) × (H − 1))     # value → row, top = hi
x_col(i)   = i × (W − 1) // (n − 1)                          # i-th of n samples → column (0 if n ≤ 1)
```

The first sample sits on column 0, the last on column `W − 1`; samples in between are spread with floor
division. Scatter maps x like y: `round((x − lo) / (hi − lo) × (W − 1))`.

### 4.4 Bar lengths

```
cells = round(v / max × W)           # hbar length in columns, W = bar width (default 40)
rows  = round(v / max × H)           # vbar height in rows
if v > 0 and cells == 0: cells = 1   # a non-zero value never disappears
cells = min(cells, W)
```

Worked example, `W = 20`, values 62, 21, 12: `20`, `21/62×20 = 6.77 → 7`, `12/62×20 = 3.87 → 4` — the
chart in 2.4.

**`fine` style** measures in eighths: `e = round(v / max × W × 8)`, draws `e // 8` full blocks and, if
`e % 8 > 0`, one partial glyph `EIGHTHS[e % 8]` (`▏▎▍▌▋▊▉` horizontally, `▁▂▃▄▅▆▇` vertically).
(hbar's `fine` path truncates the fraction instead: `full = int(len)`, `idx = int(frac × 8)`.)

### 4.5 Diverging bars (negative values)

When any value is negative, bars grow both ways from a zero line instead of all starting at the edge.
**The zero line is an axis and belongs to no bar**: a positive bar starts just past it, a negative one
ends just before it. Then `+v` and `−v` get the same length, zero draws nothing (not a one-cell stub
that looks like a small value), and the axis stays visible on every row.

hbar, width `W` (one cell is the axis, `W − 1` are shared by both sides):

```
unit     = (W − 1) / (max − min)                       # cells per data unit; min < 0 ≤ max
zero_col = clamp(round(−min × unit), 0, W − 1)         # the axis: ¦ (+ in the ascii style)
cells    = round(|v| × unit), at least 1 if v ≠ 0
v > 0: the cells right of zero_col;   v < 0: the cells left of it
```

```
up   │           ¦██████████ 10
zero │           ¦           0
down │ ██████████¦           -10
tiny │           ¦█          0.10
```

The axis glyph is `¦`, not `│` or `|`: those already separate the labels from the bars.

vbar, height `H`: `zero_row = y_row(0)`, kept at least one row from the top when there are positive
values and one row from the bottom (plots of 3 rows or more), and drawn as `-` across the whole plot. A
positive bar fills the rows from `y_row(v)` down to just above the baseline, a negative one from just
below the baseline down to `y_row(v)`; at least one row either way.

```
        ███    
███     ███    
███     ███    
---------------
    ███     ███
            ███
            ███
Jan Feb Mar Apr
```

### 4.6 Stacked bars: the largest-remainder method

A stack must add up exactly: the segments of a column must sum to the column's rounded total, or stacks
of equal totals get different heights. Rounding each segment separately does not guarantee that.

```
total  = round(column_sum / max_column_sum × H)          # cells for the whole stack
exact  = [v / column_sum × total for v in values]
cells  = [floor(e) for e in exact]
rest   = total − sum(cells)
give one extra cell to the `rest` segments with the largest fractional parts
         (ties: the earlier series first — a stable sort by descending fraction)
```

Series 0 sits at the base, the next on top of it, in order.

**A stacked bar keeps every non-zero segment**: the largest-remainder split can leave a small value with
no cell (3% of 20 cells is 0.6, and the spare cells go to larger fractions), so any non-zero segment left
empty takes one cell from the largest segment, and a stack that rounds to nothing gets one cell. Areas
don't do this: their values are interpolated per column, and a thin band would be inflated everywhere.

**Stacked with negatives** (diverging stacks): positive values stack up (right) from the zero line,
negative values stack down (left), series 0 nearest zero on both sides.

```
pos_cells  = clamp(round(max_pos / (max_pos + max_neg) × H), 1, H − 1)   # H rows or W columns
neg_cells  = H − pos_cells
each side: total = round(side_sum / side_max × side_cells), split by largest remainder
```

`max_pos` and `max_neg` are the largest positive and negative column totals. Each side gets at least
one cell when it has data. For stacked hbar the number printed at the end of the row is the **net**
total:

```
EMEA │   ▓▓▓▓▓▓████████████████ 25
APAC │ ▓▓▓▓▓▓▓▓██████████       5

█ Product   ▓ Refunds
```

### 4.7 Lines: Bresenham between samples

Each sample becomes a point `(x_col(i), y_row(v))`; consecutive points are joined with Bresenham's
line algorithm (8-connected: one cell per step, diagonal steps allowed). Consequences:

- **The stroke is exactly one cell wide.** A steep segment becomes a vertical run of cells in one
  column, a flat one a horizontal run.
- The single-series stroke is `█`: a full-cell stroke reads as a solid line from a distance.
- With `showPoints`, the stroke switches to the thin `·` and each sample gets a marker (`●` …): a solid
  stroke would swallow round markers.
- `style: "dotted"` lights every other cell of each segment (and always the endpoints), with `+`.
- Several series: series *i* draws with `FILLS[i]`; later series overwrite earlier ones where they cross.

**Draw order (z-order) on the canvas:** series strokes in series order → threshold dashes, **only into
empty cells** (a reference line goes behind the data) → point markers on top.

### 4.8 Areas: interpolate per column

An area needs a value at every column, not only at samples:

```
pos = x × (n − 1) / (W − 1);   i = floor(pos);   f = pos − i
value(x) = values[i] × (1 − f) + values[i + 1] × f        # linear interpolation
```

- **Overlaid:** for each column, fill from `y_row(value(x))` to the zero row, inclusive. Paint the last
  series first so series 0 ends on top.
- **Stacked:** per column, exactly like stacked bars (4.6), with the column's interpolated values.
- **Stacked with negatives:** positive bands up from the zero row, negative bands down. If zero falls on
  the bottom row, it moves up one row so the negative side has room.

### 4.9 Pie: sample every cell at its centre

```
default size 44 × 22; width only → height = width // 2; height only → width = height × 2
cx, cy  = W / 2, H / 2
radius  = min(W / 2, H / 2 × 2)
for each cell (x, y):
    dx = x + 0.5 − cx;   dy = (y + 0.5 − cy) × 2           # × 2: the cell aspect ratio
    outside if hypot(dx, dy) > radius
    angle = atan2(dx, −dy), in [0, 2π)                    # 0 at 12 o'clock, clockwise
    slice = first i with angle / 2π ≤ cumulative_fraction[i]
    glyph = FILLS[slice]
```

A non-zero slice too thin to own any cell (0.1% of a small pie) gets the one inside cell whose angle is
nearest the middle of its own, taken from a slice with cells to spare: a value never exists only in the
legend. The legend carries the numbers: `█ Chrome: 62 (62.0%)`, percentages with one decimal.

### 4.10 Histogram: bins

```
lo, hi = min, max of the samples (hi = lo + 1 if equal);  bin_width = (hi − lo) / bins   (bins default 10)
bin(v) = clamp(floor((v − lo) / bin_width), 0, bins − 1)      # the last bin also takes v == hi
label  = "{lo + i·w}..{lo + (i+1)·w}"
```

Bins are half-open `[a, b)` except the last, which is closed. The counts are then drawn as a single-series
hbar (no track).

### 4.11 Boxplot: quantiles

Quartiles use linear interpolation between order statistics (the "type 7" definition, the default in
R, NumPy and Excel's `QUARTILE.INC`):

```
sorted s, n values;  pos = q × (n − 1);  a = floor(pos);  b = ceil(pos)
Q(q) = s[a] + (s[b] − s[a]) × (pos − a)
```

Five numbers: min, Q(0.25), median Q(0.5), Q(0.75), max — computed from raw samples, never asked of the
caller. Positions: `clamp(round((v − gmin) / (gmax − gmin) × (W − 1)), 0, W − 1)`; draw `─` from min to
max, `█` from Q1 to Q3, then `├` at min, `┤` at max, `║` at the median (later writes win). The exact
statistics follow as text.

### 4.12 Quantising to a small set of levels

Split the range into **equal buckets**, one per visible level:

```
norm   = (v − lo) / (hi − lo)                     # 0..1
level  = min(n − 1, floor(norm × n))              # bucket 0..n−1; the maximum joins the top bucket
tick   = SPARK_TICKS[level(norm, 8)]              # "▁▂▃▄▅▆▇█" (▁ if the series is flat)
shade  = SHADES[1 + level(norm, 4)]               # "░▒▓█" — never the blank
color  = HEAT_RAMP[level(norm, 16)]               # 16 colors
```

Two traps this avoids. Scaling by `n − 1` and flooring (`floor(norm × (n − 1))`) gives the top level to
the exact maximum alone and squeezes everything else down. And **blank is not a level**: a heatmap cell
that holds a value must be visible, or the lowest values read as "no data" (the old renderer left the
bottom fifth of every heatmap empty, and a heatmap of equal values entirely empty).

### 4.13 Numbers as text

- Integers print without decimals (`|v − trunc(v)| < 1e−9` counts as one, which absorbs float noise
  like `2.0000000001`): `62`.
- From 1 up, two decimals: `26.40`, `123456789.50`.
- Below 1, **two significant digits**, so small values stay apart: `0.50`, `0.050`, `0.0010`, `0.0042`
  (digits = max(2, 1 − floor(log10 |v|))); below 1e−7, exponent form `3e-09`. Two fixed decimals would
  print `0.001` and `0.004` both as `0.00`. log10 is the correctly rounded one (C's): right under a power
  of ten it decides the digits — log10 0.09999999999999996 is −1.0000000000000002, so a histogram edge
  computed as that prints `-0.100`; a log10 that is off by an ulp (Go's `math.Log10`) prints `-0.10`.
- Pie percentages: one decimal.
- **Axis labels are the exact values of their rows**, `lo + (1 − r / (H − 1)) × (hi − lo)`, rounded to
  12 significant digits first (float noise would print `−27.999999999` as `−28.00`), right-aligned to the
  widest label. They are honest (that row *is* that value) but not "nice": `26.40`, `22.80`. Zero is
  always on a row when the range crosses it (4.2); a `−0` never prints.
- A threshold snaps to its nearest row, so its label prints the exact value next to it.

### 4.14 Magnitude limit

Values are limited to `|v| ≤ 1e15`. Beyond about `2^53 ≈ 9e15`, `lo + 1 == lo` in float64, so the
degenerate-domain fix stops working, and ranges like `1e308 − (−1e308)` overflow to infinity and turn
every position into NaN. No readable chart needs larger numbers.

---

## 5. Layout: composing the parts

### 5.1 Anatomy

```
╭───────────────────────────────╮
│         Browser share         │   ← title, centred
├───────────────────────────────┤   ← rule under the title
│ Chrome  │ ████████████████ 62 │   ← label column │ plot │ value
│ Firefox │ █████░░░░░░░░░░░ 21 │
╰───────────────────────────────╯
```

Top to bottom: title → plot rows (with the y-axis on the left for line-like charts) → x-axis labels →
blank line → legend → notes (threshold footnote, value ranges).

### 5.2 The frame

```
inner  = max display width of the title and of every body line
top    = TL + H × (inner + 2) + TR
row    = V + " " + line + spaces to inner + " " + V
title  = centred in inner: floor(pad / 2) spaces left, the rest right; followed by LT + H… + RT
bottom = BL + H × (inner + 2) + BR
```

One space of padding inside each side. The frame never truncates: it grows to the widest line, which is
why lines must be measured in display columns (section 6).

### 5.3 Label columns

Category labels are padded to the widest label (in display columns), then ` │ ` (ASCII ` | `), then the
bar, then a space and the value:

```
Chrome  │ ████████████████████ 62
```

Grouped hbar puts each category on its own line and indents its series under it, separated by a blank
line; the series names are inline, so it needs no legend:

```
Q1
  2025 │ ██████████░░░░░░ 30
  2026 │ ███████████░░░░░ 35

Q2
  2025 │ ██████████████░░ 45
  2026 │ ████████████████ 50
```

### 5.4 vbar layout

```
gap        = 1 column between categories
k          = number of series side by side (1 if stacked)
bar_w      = max(1, (W − (n − 1) × gap) // (n × k))        # W default 60
group_w    = max(k × bar_w, widest label)
bars start = (group_w − k × bar_w) // 2 inside each group
labels     = centred under their group; the label row is right-trimmed
```

Floor division means the chart can be a few columns narrower than `W` (asked 23, got 19 below). Heights:
`round(v / max × H)` per bar, `H` default 10.

```
░░░░ ░░░░ ░░░░ ░░▓▓
░░░░ ░░░░ ░░▓▓ ██▓▓
░░░░ ██▓▓ ░░▓▓ ██▓▓
██▓▓ ██▓▓ ██▓▓ ██▓▓
██▓▓ ██▓▓ ██▓▓ ██▓▓
██▓▓ ██▓▓ ██▓▓ ██▓▓
 Q1   Q2   Q3   Q4

█ 2025   ▓ 2026
```

### 5.5 Axes for line, area and dual_axis

```
{row value, right-aligned to the widest} ┤{plot row}
```

The x-axis labels go under the plot, indented by the axis width + 2. Placement:

1. Truncate each label to 8 columns.
2. Centre it under its sample's column, then clamp it inside the plot, so the first and last labels are
   never cut (`Jan` must not become `an`).
3. Always keep the first and last. Keep a middle label only if it starts after the previous kept label
   ends (at least one space between) and ends before the last label starts. Drop the rest rather than
   let them run together (`JaFeb`).

```
   30 ┤                     ██       
26.40 ┤                   ██  ████   
22.80 ┤                 ██        ███
19.20 ┤      █████    ██             
15.60 ┤  ████     ████               
   12 ┤██                            
       Mon   Tue    Wed    Thu    Fri
```

dual_axis adds the second axis on the right, `├ {value}` left-aligned, and a two-line legend
(`left:  █ Temp` / `right: ▒ Humidity %`). Its two series use `█` and `▒`.

### 5.6 Reference lines (thresholds)

- A reference line is `-` on every even column of its row, drawn only into empty cells: it goes behind
  the data, so a line running along it is never cut into `-█-█`.
- The domain is extended so every reference line is inside the plot.
- A single unnamed `threshold` is explained in a footnote: `- - threshold: 50` (on a new paragraph, or
  on the legend line with several series).
- Named `thresholds` are labelled **to the right of the plot, on their own row**: `target: 25`. The label
  never covers data; lines that snap to the same row share it (`a: 5, b: 5.01`).

```
   30 ┤                     ●·       
26.40 ┤- - - - - - - - - -·· -···· -   target: 25
22.80 ┤                 ··        ··●
19.20 ┤      ·●···    ··             
15.60 ┤  ····     ···●               
   12 ┤●·                            
```

### 5.7 Default sizes

A chart without `width` should fill a readable width, not shrink to its data.

| chart | default size |
|---|---|
| line, area, dual_axis | plot 60 × 10 |
| scatter | plot 60 × 15 |
| vbar | plot 60 wide × 10 tall |
| heatmap | grid 60 wide (cells ≥ 3), one row per series |
| hbar, histogram | bar 40 long |
| dotplot, boxplot | axis 40 wide |
| pie | 44 × 22 |

`width`, when given, is the **plot's** width (bars, grid or axis), not the whole output: labels, axis
text, values and the frame come on top. That keeps the plot's resolution predictable.

---

## 6. Text: labels, names and titles

### 6.1 Measure in display columns, not characters

`len()` counts code points; a terminal counts columns. They differ:

| text | code points | columns |
|---|---|---|
| `東京` (CJK) | 2 | 4 — East Asian Wide/Fullwidth characters take 2 |
| `🍕` (most emoji) | 1 | 2 |
| `été` written as `e + U+0301 + …` | 5 | 3 — combining marks take 0 |
| `\x1b[31mred\x1b[0m` | 12 | 3 — escape sequences take 0 |

The model used:

```
width(ch) = 0  if ch is a combining mark or its category is Mn, Me or Cf (accents, ZWJ, variation selectors)
          = 2  if East_Asian_Width(ch) is W or F
          = 1  otherwise
```

Every pad, centre, truncation and frame width uses display columns; ASCII strings take a fast path
(`len`), so ASCII output is byte-identical to a naive implementation. Known limit: emoji joined with
zero-width joiners (`👨‍👩‍👧`) are drawn one or several glyphs wide depending on the terminal; no
column model gets them right everywhere.

### 6.2 Placing text on a grid

When a label is written into a row of cells (x-axis, vbar labels), a wide character occupies its cell
**and** the next one; the second cell is left empty (a "shadow") so the joined row keeps the right
width. Combining marks join the previous cell.

**Truncation never splits a wide character:** if the cut would leave half of one, it becomes a space.
`月曜日` in a 5-column heatmap cell becomes `月曜 `.

### 6.3 Untrusted text is sanitised

Titles and labels often come from data, and data comes from anywhere.

- **Control characters (Unicode category Cc)** — newline, tab, carriage return, ESC, DEL, the C1 range —
  are **replaced by spaces**. A newline would break the chart's rows; `ESC[2J` in a title would clear
  the screen of whoever `cat`s the output.
- Title, labels and series names are limited to 200 characters; threshold labels to 40.
- The point marker (`pointChar`) must be exactly one column wide: a wide glyph would push the rest of
  its row one column right.

---

## 7. The twelve chart types

Pick by the question, not by the data shape:

| the question | chart |
|---|---|
| how does one metric trend, inline in a sentence | `sparkline` |
| which is biggest, a ranking, long category names | `hbar` |
| one value per category, short names, few categories | `vbar` |
| several measures per category / parts of a whole | grouped or `stacked` `hbar`/`vbar` |
| how does it change over time | `line` (values) or `area` (volume) |
| two series on different scales | `dual_axis` |
| relationship between two numbers | `scatter` |
| shares of a whole | `pie`, or a stacked `hbar` (lengths compare better than angles) |
| how are raw values distributed | `histogram`, or `boxplot` per group |
| a grid of values (hour × weekday) | `heatmap` |
| close values where zero is irrelevant; values against a target | `dotplot`, or `line` + `thresholds` |

### sparkline

One row per series, `name ▁▂▃…`, each series scaled to its own range (4.12). No axes; use
`border: "none"` to put it inline in a sentence or a log line. Needs eighth-height glyphs (tier 2).

```
p99 ▃▅▄█▂▆▇▁▅█▃
```

### hbar

Single, grouped (5.3), stacked, diverging (4.5–4.6). Value after every bar, track behind bars (2.4).
The best chart for rankings: labels of any length stay readable, and length is the most accurately read
visual variable.

### vbar

Single, grouped side by side, stacked, diverging (5.4). No value labels, so the value is only as precise
as a row; prefer hbar when exact values matter.

### line

Several series on a shared axis (4.7), optional `showPoints`, `pointChar`, `threshold`, `thresholds`,
x-axis `labels` (5.5). At least two values per series.

### area

Overlaid or stacked, negative values fill downward (4.8). All series the same length.

```
    5 ┤   ████                 
 2.50 ┤█████████               
    0 ┤████████████████████████
-2.50 ┤           ██████████   
   -5 ┤                 █      
```

### scatter

`points: [{x, y}]` per series, one marker shape per series, ranges printed below. Default 60 × 15. Where
markers of different series land on the same cell, the cell shows `*` and the legend adds
`* overlap` (dotplot does the same) — the last series drawn must not silently hide the others.

```
     ○              
          ●         
              ○     
                    
                   ●
●                   
x: [1, 5]  y: [1, 5]
● A   ○ B
```

### dual_axis

Exactly two series, independent left and right scales (5.5).

```
18 ┤▒▒           ██████     ├ 80   
16 ┤  ▒▒▒▒   ████      █████├ 73.75
14 ┤      ▒▒▒               ├ 67.50
12 ┤  ████   ▒▒▒▒      ▒▒▒▒▒├ 61.25
10 ┤██           ▒▒▒▒▒▒     ├ 55   

left:  █ Temp
right: ▒ Humidity %
```

### pie

One series per slice, `values[0]` is its size, non-negative and not all zero (4.9).

```
       ▒▒▒▒▒█████       
    ▒▒▒▒▒▒▒▒████████    
  ▒▒▒▒▒▒▒▒▒▒██████████  
 ▓▓▒▒▒▒▒▒▒▒▒███████████ 
▓▓▓▓▓▓▓▒▒▒▒▒████████████
▓▓▓▓▓▓▓▓▓▓▒▒████████████
▓▓▓▓▓▓▓▓▓▓▓█████████████
▓▓▓▓▓▓▓▓▓███████████████
 ▓▓▓▓▓▓████████████████ 
  ▓▓▓█████████████████  
    ████████████████    
       ██████████       

█ Chrome: 62 (62.0%)
▓ Safari: 21 (21.0%)
▒ Other: 17 (17.0%)
```

### histogram

Exactly one series of **raw samples**; bins are computed (4.10).

```
12..19 │ ████████████████ 4
19..26 │ ████████████████ 4
26..33 │ ████████         2
33..40 │ ████████         2
```

### heatmap

One series per row (`name` = row label), `labels` = column headers, shade or color per cell (4.12).
Cell width `max(3, (W + 1) // columns − 1)`, one space between cells, headers centred over cells.

```
    Mon Tue Wed Thu Fri 
9am ░░░ ░░░ ░░░ ▒▒▒ ░░░ 
5pm ███ ▓▓▓ ███ ███ ███ 
```

### boxplot

One series of raw samples per group (4.11).

```
A │       ├──███║███─────┤    min=55 q1=62.75 med=71 q3=78.75 max=95
B │ ├──────██║███──────────┤  min=40 q1=58.50 med=64 q3=69.50 max=99
```

### dotplot (Cleveland)

One row per category, `·` background, a marker per series at `round((v − min)/(max − min) × (W − 1))`;
the axis is zoomed to the data and its range is printed. With one series the value follows the row.

```
Oakland │ ···················● 5.20
Seattle │ ··········●········· 4.40
Denver  │ ●··················· 3.60
value axis: [3.60, 5.20]
```

---

## 8. Styles

| style | effect |
|---|---|
| `solid` (default) | whole-cell bars, `FILLS` per series, track on |
| `fine` | bars end on eighth-block glyphs (tier 2 fonts only); ignored by charts without bars |
| `halftone` | lighter stippled series glyphs (`HALFTONE_FILLS`), no track |
| `ascii` | pure ASCII: the 23-glyph ramp, `,` track, `\|` separators, `+` axis ticks, `o x * + …` markers — combine with `border: "ascii"` for output that survives any font, email and legacy terminals |
| `dotted` | line charts: every other cell of the stroke, `+` |

---

## 9. Input, limits and errors

### 9.1 The spec

One JSON object, the same for the library, the CLI and the MCP tool:

```
chartType   sparkline | vbar | hbar | line | area | scatter | dual_axis | pie | histogram | heatmap | boxplot | dotplot
series      [{name?, values?: number[], points?: [{x, y}]}]
labels?     string[]            category labels, x-axis labels, heatmap column headers
title?, width?, height?, border?, style?, stacked?, bins?, useColor?,
threshold?, thresholds?: (number | {value, label?})[], showPoints?, pointChar?
```

A catalogue (`list_charts`) says, per chart type, what it draws, how `series` is read, which options
matter and a minimal example. A test renders every example and checks that **every listed option
changes the output and every unlisted one does not** — an option that silently does nothing is a bug
(we shipped one: section 11).

### 9.2 Limits

Every request is bounded, because renderers allocate `width × height` grids and output goes into
someone's context window:

| limit | value |
|---|---|
| `width` / `height` | ≤ 500 / ≤ 200 |
| `bins` | ≤ 500 |
| series | ≤ 100 |
| values + points, all series | ≤ 50,000 |
| magnitude of any number | ≤ 1e15, finite |
| title, each label, each name | ≤ 200 characters |
| thresholds | ≤ 20, labels ≤ 40 characters |

Violations are **errors, not truncation**. Truncating silently hides data.

### 9.3 Strict types

Numbers are numbers: `"1"` is not `1`, `true` is not `1`, `null` is not `0`. An API layer that coerces
(Pydantic's lax mode did) makes the same spec render in one entry point and fail in another. Integers
are accepted where floats are expected.

### 9.4 Error messages are for the caller to fix the call

One line, where, what was wrong, what was expected, the offending value quoted:

```
series 0 "latency" must contain at least two values
labels length (1) must match each series' values length (3)
width must be at most 500, got 9999
series 0 value must be at most 1e15 in magnitude, got 1e+308
invalid border "wavy" (expected one of: none, ascii, light, heavy, double, rounded)
row 3, column "v" is not a number: "n/a"
thresholds 0: label must be at most 40 characters, got 41
```

An agent can correct its own call from such a message. A crash with an empty message ("Error executing
tool") gives it nothing — every internal exception reachable from input is a bug.

### 9.5 Numbers from tables (CSV)

Real CSV files are dirty. The CSV reader:

- sniffs the delimiter among `,` `;` tab `|`; strips a BOM, blank lines; pads short rows;
- parses decorated numbers: surrounding spaces, `$ € £` prefixes, a trailing `%`, thousands separators
  (`1,234.5`), a decimal comma when the file is not comma-separated (`3,14`);
- treats a column as numeric if every non-empty cell parses; the first text column is the label column;
- resolves column references by exact name, case-insensitive name, 1-based index, unique prefix
  (`p99` → `p99_ms`), unique substring — and reports ambiguity with the candidates;
- sorts numerically for numeric columns (`-col` or `col:desc`), then `limit`s;
- reports the exact cell on error: `row 3, column "v" is not a number: "n/a"` (row numbers count the
  header as row 1, like a spreadsheet).

---

## 10. Showing text charts in other media

**Markdown and chat.** Fenced code block. Nothing else keeps alignment.

**Terminals.** Most modern terminals (Windows Terminal, iTerm2, Ghostty, GNOME) have full coverage. The
default Windows console font and editors using Consolas lack tier-2 glyphs.

**Browsers.** A web page is the hardest place:

- Use a monospace font that covers **every** glyph the renderer can emit, self-hosted if necessary
  (the website uses DejaVu Mono). The browser's per-glyph fallback is exactly the ragged-edge problem of
  2.1, and a decorative "pixel" font will lack block and box glyphs entirely.
- Line height about **1.15–1.2**: box-drawing verticals and full blocks are designed to touch the next
  row; at 1.5 frames turn into dashed lines and bars into stripes.
- `white-space: pre`, no letter spacing, horizontal scroll on narrow screens rather than wrapping.
- Color: convert ANSI 256 indexes to hex (6×6×6 cube: levels `0, 95, 135, 175, 215, 255`; greys
  `8 + 10 × (n − 232)`), and darken for light themes.

**Email and legacy systems.** `style: "ascii"`, `border: "ascii"`.

---

## 11. Mistakes we made, and what each one taught

| mistake | symptom | principle |
|---|---|---|
| Sub-cell canvas (quadrant, braille) and eighth-block bar ends by default | ragged right edges in Consolas/Courier; braille series indistinguishable without color | font safety first (2.1); every series needs a shape, not only a color (3.1) |
| Stacked bars assumed non-negative values | the Go version **panicked** on a negative value in a stack | negative values are normal data: diverging stacks (4.6) |
| `vbar` computed `width` and never used it | the option silently did nothing | a test proves each listed option changes the output (9.1) |
| `vbar` without `width` drew 1-column bars; heatmap cells were always 3 columns | "pencil-thin" charts next to 70-column line charts | every chart fills a default plot width (5.7) |
| x-axis labels centred without bounds | first and last labels cut (`Jan` → `an`), neighbours merged (`JaFeb`) | clamp inside the plot, keep the ends, drop colliding middles (5.5) |
| Legend on one line | 23 series stretched the frame to hundreds of columns | wrap legends at 100 columns (3.2) |
| Track glyph equal to a series glyph | the 4th grouped series' bar vanished into its own background | one role per glyph (2.3) |
| ASCII glyphs as a "core 8 + extra 15" | series 9+ looked like different weights at random | one density-ordered ramp (2.2) |
| Language rounding and summation used implicitly | Python port differed from Go output by one cell | explicit half-away-from-zero rounding and left-to-right sums (4.1) |
| Values unbounded | `1e308, −1e308` → infinity → NaN → a crash with no message in 9 chart types | bound magnitudes (4.14); no internal exception may reach the caller (9.4) |
| Control characters passed through | `\n` broke rows; `ESC[2J` reached the terminal | sanitise untrusted text (6.3) |
| Width measured with `len()` | CJK, emoji and accents made frames crooked | display columns everywhere (6.1) |
| API layer coerced types | `"1"` and `true` rendered over MCP, failed in the library | strict types at every entry point (9.3) |
| Text lengths unbounded | a 10,000-character title made a 10,004-column chart | bound text too (9.2) |
| Solid stroke with point markers | markers drowned in the `█` line | thin connector `·` with markers (4.7) |
| Hand-maintained example outputs in docs | the gallery drifted from the renderer (a stale stacked vbar, a missing border) | generate examples from their specs and check them in CI |
| Web page: decorative pixel font, line height 1.5 | block and box glyphs fell back to another font; frames looked dashed | self-host a full-coverage font, tight line height (10) |

The following were found by the analysis that produced this document, confirmed on the running
renderer, and fixed. Several were hiding **in the golden files**: a golden file pins behaviour, it does
not prove it right — the corpus faithfully preserved a heatmap drawn entirely blank and a dotplot row
missing a series.

| mistake | symptom | principle |
|---|---|---|
| Levels picked with `floor(norm × (n − 1))`, blank as the lowest shade | the bottom fifth of every heatmap was empty; a heatmap of equal values was **entirely blank**; the top level only for the exact maximum | equal buckets; blank is not a level (4.12) |
| The zero row/column shared by positive and negative bars | `+3` one row taller than `−3`; zero drew a stub; a diverging hbar had no one-cell minimum, so `−1.41` next to `76` **vanished** | the zero line is an axis owned by no bar (4.5) |
| Threshold dashes written over data | a line along a threshold was cut into `-█-█` | reference lines go behind the data (4.7) |
| Markers of different series on one cell: last one wins | a dotplot row of four series showed three | show an overlap glyph `*` and say so in the legend (7) |
| A slice thinner than a cell got no cells | a 0.1% slice existed only in the legend | every non-zero value owns at least one cell (4.9) |
| Two fixed decimals everywhere | `0.001` and `0.004` both printed `0.00` | two significant digits below 1 (4.13) |
| Zero between rows; axis labels with float noise | an area chart's baseline read `0.50`; a label read `−28.00` for `−28`; a `−0` | put zero on a row; round labels to 12 significant digits (4.2, 4.13) |
| All-equal data scaled to `v .. v + 1` | flat lines on the bottom edge; `value axis: [5, 6]` for data that is all 5 | a centred range, and print the data's own range (4.2) |
| "Box drawing is font-safe" | the heavy `┃` boxplot median is not in Consolas; the test accepted the whole block | the safe set is WGL4, and the test checks exactly that (2.1) |
| Structural glyphs inside the series ramp | `|` (the ascii separator) and `.` (the connector) were ramp glyphs 21 and 23; the ascii diverging axis was `|` too | one role per glyph, pinned by a test (2.2, 2.3) |

---

## 12. Known limitations and deliberate choices

The analysis behind this document found eleven imperfections in the renderer. Nine are fixed (section
11, second table): the golden corpus was regenerated one fix at a time, each diff reviewed and
confined to the charts the fix concerned. What remains is either a deliberate trade-off or future work —
a port should know these, and may improve on them:

1. **Axis labels are exact row values, not "nice" numbers.** Rows read `26.40, 22.80` rather than
   `25, 20`. Zero is always on a row (4.2), but a nice-number domain (steps of 1, 2, 2.5, 5 × 10ⁿ) would
   widen the data's range and leave rows unused; the reference keeps the plot filled instead.
2. **vbar prints no values.** Its value is only as precise as a row, and the one-cell minimum makes a
   tiny value look bigger than it is (`0.1` next to `10` fills one of four rows). Use hbar when exact
   values matter — it prints every one.
3. **`width` is approximate for vbar** (floor division, 5.4: asked 23, got 19), and **hbar's default bar
   is 40** long while other plots default to 60 — with labels and values an hbar ends up about as wide.
4. **Crossing lines overwrite each other.** Where two line series cross, the later series is drawn on
   top; lines crossing is ordinary, so there is no overlap glyph for them (unlike markers, section 7).
5. **Boxplot marks on one cell:** the median `║` wins over `├`/`┤` when they coincide; the statistics
   printed after the row always give the exact five numbers.
6. **Emoji built with zero-width joiners** have no reliable width (6.1).
7. **Large numbers are printed in full** (`123456789.50`); there are no SI suffixes (`123.5M`).

---

## 13. Drawing a chart by hand (for agents without a code tool)

You can produce a correct text chart by following these steps. Work the numbers out explicitly; do not
eyeball lengths.

### 13.1 Choose

1. Choose the chart type from the table in section 7. When in doubt: **hbar** (rankings, categories),
   **line** (time), **sparkline** (inline trend).
2. Choose the size: bars 20–40 columns long, line plots 40–60 × 6–10.
3. Unicode alphabet (`█▓▒░`, `│┤`, `─┌┐└┘`) unless the destination may lack fonts (email, logs of old
   systems): then ASCII (`#@%&`, `|`, `+-`).

### 13.2 hbar recipe

```
1. max  = largest value (if any value is negative, use the diverging rules in 4.5)
2. for each value: cells = round(v / max × W), half away from zero; if v > 0 and cells = 0 → 1
3. labels: pad every label with spaces to the longest label
4. each line: label + " │ " + "█" × cells + "░" × (W − cells) + " " + value
5. value text: integers as is, others with two decimals
```

Example, `W = 20`: `62 → 20`, `21 → 20 × 21 / 62 = 6.77 → 7`, `12 → 3.87 → 4`:

```
Chrome  │ ████████████████████ 62
Firefox │ ███████░░░░░░░░░░░░░ 21
Safari  │ ████░░░░░░░░░░░░░░░░ 12
```

Several series: series 1 `█`, series 2 `▓`, series 3 `▒`, series 4 `░`; add the legend
`█ name1   ▓ name2`.

### 13.3 vbar recipe

```
1. H rows (6–10). rows(v) = round(v / max × H), at least 1 for a non-zero value
2. bar width b columns (2–6); one space between categories
3. build the grid top row first: a cell at row r (r = 1 at the bottom … H at the top) is filled if r ≤ rows(v)
4. the label row: each label centred under its bar
```

Example, `H = 6`, `max = 70`, 2025 = `30 45 40 60` → rows `3 4 3 5`; 2026 = `35 50 55 70` → rows
`3 4 5 6` — the chart in 5.4.

### 13.4 sparkline recipe

```
1. lo, hi = min, max
2. for each value: index = min(7, floor((v − lo) / (hi − lo) × 8)); glyph = "▁▂▃▄▅▆▇█"[index]
```

`4 6 5 9 3 7 8 2 6 9 4` (lo 2, hi 9) → `▃▅▄█▂▆▇▁▅█▃`.

### 13.5 line recipe

```
1. lo, hi = min, max (plus any threshold); H rows; W columns
2. row labels: value(r) = lo + (1 − r / (H − 1)) × (hi − lo) for r = 0 (top) … H − 1
3. sample i goes to column x = floor(i × (W − 1) / (n − 1)) and row y = round((1 − (v − lo)/(hi − lo)) × (H − 1))
4. connect consecutive points with a one-cell-wide path (Bresenham); mark with █ (or · plus ● at samples)
5. each line: right-aligned label + " ┤" + plot row
```

Worked: `12 18 15 30 24`, `H = 6`, `W = 30` → labels `30, 26.40, 22.80, 19.20, 15.60, 12`; columns
`0, 7, 14, 21, 29`; rows `5, 3, 4, 0, 2` — the chart in 5.5.

### 13.6 Self-check before you answer

- [ ] Every framed line has the same width (count columns; CJK counts 2).
- [ ] Every bar length / row count was computed, not guessed; the longest bar is exactly `W`.
- [ ] Bars start at zero (or diverge from a marked zero).
- [ ] Each series has its own glyph, and the legend uses the same glyphs in the same order.
- [ ] Values are printed where the grid loses precision.
- [ ] The chart is inside a fenced code block.

---

## 14. Porting checklist (Rust, Go, TypeScript, …)

**Architecture.** One pure function `render(spec) → Result<String, Error>`: normalise and validate the
spec (section 9) → dispatch on `chartType` → render a body (list of lines) → wrap in the frame (5.2).
Charts that draw freely (line, scatter, dual_axis) share a canvas: a grid of `(glyph, color)` cells with
`set` (bounds-checked, out-of-range ignored) and Bresenham `line`. Keep the catalogue (section 9.1) as
data; generate `--list`, the tool description and tests from it.

**Conformance.** `spec/conformance/corpus.json` holds 317 random specs with their exact output (or, for a few,
their exact error message); `spec/conformance/gallery.json` / `gallery.txt` the documented examples; its
`README.md` gives the exact format. Run them against
the port. To reach byte parity:

- rounding half away from zero (4.1); left-to-right float sums;
- stable sort by descending fraction in the largest-remainder method (ties → lower index);
- floor division for column positions; `trunc` (not floor) where the reference uses `int()` on
  non-negative values — equivalent there, but keep it in mind;
- number formatting: `%.0f` / `%.2f` with correct binary rounding (Rust's `format!` and Python's
  `format` agree; hand-written formatters often do not);
- `atan2`/`hypot` for the pie — IEEE-754 results are stable enough, but compare the pie goldens early;
- **the Unicode tables:** East Asian Width and general category depend on the Unicode version. Python's
  `unicodedata` and a Rust crate (`unicode-width`) may disagree on newer emoji. Pin the version and test
  with the CJK/emoji/combining cases.

The corpus reflects the fixed behaviour described in this document. If a port changes behaviour on
purpose (section 12 lists candidates), do it one change per commit and regenerate its goldens with a
reviewed diff: every changed case should be one the change is about.

**Robustness.**

- Validate before allocating; every limit in 9.2.
- No panics from input: overflow, NaN, empty series, a single value, all-equal values, all zeros, all
  negatives, labels wider than the plot, 1,000 categories — each must render or return a ChartError.
- Sanitise text (6.3). Strict types at the API boundary (9.3).

**Performance.** The worst case is bounded: 500 × 200 cells, 50,000 values. In Python a maximal chart
renders in 20–60 ms. Measure display width on the ASCII fast path; cache per-glyph widths (charts reuse a
handful of glyphs); build rows as arrays and join once.

**Tooling that paid off.**

- Golden files for everything, regenerated only on purpose, with the diff reviewed.
- Examples in documentation generated from their specs, with a `--check` mode run by the tests.
- A test that every chart's catalogue example renders framed and unframed.
- A test that default output uses only tier 0–1 glyphs (2.1).
- A stress test with hostile specs through the real API (MCP), not only unit tests.

---

## 15. The requirements

Normative for v1.0 (section 0). Each requirement names the section that explains it.

**Any chart** — rendered or hand-drawn:

- **R1** (§1.3) A chart MUST be plain text meant for a monospace grid. If it is framed, every line MUST
  have the same display width.
- **R2** (§2.1) By default a chart MUST use only tier-0 and tier-1 glyphs: ASCII, Latin-1, the WGL4 box
  drawing, the shades `░▒▓█`, the half blocks `▌▄▐▀` and the markers `●○▲■□▼♦◊►◄`. Tier-2 glyphs (heavy
  or rounded box lines, eighth blocks, braille) MAY be used only when asked for, and in sparklines.
- **R3** (§2.3, §3.2) Within a chart, a glyph MUST have one role. A legend MUST show the exact glyph each
  series is drawn with.
- **R4** (§3.1) Series MUST be distinguishable without color: by glyph and legend, or by naming the series
  on every row. Color MAY be added; it MUST NOT be the only difference.
- **R5** (§2.2) Magnitude SHOULD be encoded by ink density (`░▒▓█`); series SHOULD get glyphs far apart in
  density or texture, the first series the densest.
- **R6** (§4.2, §4.5) A bar MUST start at zero, or grow both ways from a marked zero axis that belongs to
  no bar. A line or dot plot MAY zoom to its data; it MUST then show the range it uses.
- **R7** (§4.1, §4.4) Lengths and positions MUST be computed from the values — `round(v / max × W)`,
  rounding half away from zero — not estimated.
- **R8** (§4.4, §4.6, §4.9, §4.12) A non-zero value MUST NOT disappear: at least one cell for a bar, a
  stacked segment or a pie slice, and a visible (never blank) heatmap cell. Zero MUST be visibly empty.
- **R9** (§7) A series MUST NOT silently hide another: overlapping marks of different series MUST be
  marked as overlaps.
- **R10** (§1.2) Where the grid only approximates a value, the value SHOULD be printed — after the bar,
  in the legend, on the axis, or as a range.
- **R11** (§6) Text MUST be measured in display columns (CJK and most emoji take two, combining marks
  none); a wide character MUST NOT be cut in half; control characters MUST NOT reach the output.
- **R12** (§5.7) Without a requested size, a chart SHOULD fill a readable default plot width;
  a requested width SHOULD mean the plot, not the decoration around it.

**A renderer**, in addition:

- **R13** (§1.3) A renderer MUST be deterministic: the same spec gives the same bytes, with no dependence
  on time, randomness, locale or terminal.
- **R14** (§4.1, §4.6) A renderer MUST sum left to right and split stacks by the largest-remainder method,
  so that every stack adds up exactly.
- **R15** (§9) A renderer MUST bound its input (§9.2), accept only well-typed values (§9.3), and reject an
  invalid spec with a one-line message that says what to fix (§9.4). It MUST NOT crash on any input.

**Documentation** of charts SHOULD show examples generated from their specs and checked against the
renderer, never hand-edited (§11): a golden file pins behaviour; it does not prove it right.
