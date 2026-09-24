# Drawing text charts by hand

How to produce a correct text chart **without running any code**: which numbers to compute, how to turn
them into rows of characters, and how to check the result before you answer. Every example below is real
output of the reference renderer for the spec printed above it, and every number in the working is one
you can recompute.

If a tool is available — the `asciicharts` MCP server, the `asciicharts` binary, or
`python scripts/asciicharts.py` — use it: it is exact. Draw by hand when there is no tool, or when the
chart is small enough that a tool is overkill.

## Which charts to draw by hand

Language models miscount characters. A bar of 17 `█` next to one of 6, a right border at column 44 — that
is where hand-drawn charts go wrong. So the method below never eyeballs: compute every length first,
then build each row by repeating a glyph a known number of times, then count again.

| tier | charts | what to do |
|---|---|---|
| **A — reliable** | sparkline, hbar (up to ~10 bars), small vbar, dotplot | draw it |
| **B — careful** | line and area on a small grid, histogram, boxplot, small heatmap, scatter with a few points | draw it small (plot ≤ 20 × 6), compute everything, self-check |
| **C — use a tool** | pie, dual_axis, anything large | use a tool; without one, draw the simpler equivalent given in its section and say so |

## The protocol (every chart)

1. **Pick small sizes.** Bars 10–20 cells long; plots at most 20 columns × 6 rows. Small is what you
   can count.
2. **Compute a table first**, before drawing a single glyph: for each value, its cell count (or row,
   column). Write it down.
3. **Round half away from zero**: `2.5 → 3`, `7.5 → 8`, `−2.5 → −3`; otherwise to the nearest integer.
4. **A non-zero value never gets 0 cells** — make it 1. Zero gets 0.
5. **Build each row as counted runs**: `█ × 7 + ░ × 13`, never "about this long".
6. **Pad labels** with spaces to the longest label, so every bar starts in the same column.
7. **Print the values** next to bars: integers as they are, others with two decimals (`26.40`); below 1,
   two significant digits (`0.0042`).
8. **Prefer no frame.** Put the title on its own line above the chart. A frame's right border is the
   first thing that shows a miscount; add one only when asked (see *Frames* below).
9. **Answer in a fenced code block** (```` ``` ````), or alignment is lost.
10. **Run the self-check** at the end of this document.

**Glyphs.** Series 1–8: `█ ▓ ▒ ░ ▌ ▄ ▐ ▀`. The empty rest of a bar (the *track*): `░` (use `▒` if the bar
itself is `░`). Separator between labels and bars: `│`. For output that must be pure ASCII: series
`# @ % & $ W M N H`, track `,`, separator `|`.

---

## Tier A

### sparkline

A one-line trend: one glyph per value, 8 heights.

```
index = min(7, floor((v − lo) / (hi − lo) × 8))       lo, hi = min and max of the series
glyph = "▁▂▃▄▅▆▇█"[index]                              all values equal: every glyph is ▄
```

```json
{ "chartType": "sparkline", "border": "none", "series": [{ "name": "p99", "values": [4, 6, 5, 9, 3, 7, 8, 2, 6, 9, 4] }] }
```

```
p99 ▃▅▄█▂▆▇▁▅█▃
```

Working: lo = 2, hi = 9, so `(v − 2) / 7 × 8`: 4 → 2.29 → 2 `▃`; 6 → 4.57 → 4 `▅`; 5 → 3.43 → 3 `▄`;
9 → 8 → capped to 7 `█`; 3 → 1.14 → 1 `▂`; 7 → 5.71 → 5 `▆`; 8 → 6.86 → 6 `▇`; 2 → 0 `▁`.

Check: as many glyphs as values; the maximum is `█`, the minimum `▁`.

### hbar — one series

The best general-purpose chart: rankings, categories, long labels.

```
W     = bar length (10–20)
cells = round(v / max × W)          (≥ 1 if v ≠ 0)
row   = label padded to the longest label + " │ " + "█" × cells + "░" × (W − cells) + " " + value
```

```json
{ "chartType": "hbar", "border": "none", "width": 20, "labels": ["Chrome", "Firefox", "Safari"], "series": [{ "values": [62, 21, 12] }] }
```

```
Chrome  │ ████████████████████ 62
Firefox │ ███████░░░░░░░░░░░░░ 21
Safari  │ ████░░░░░░░░░░░░░░░░ 12
```

| label | v | v / 62 × 20 | cells | track |
|---|---|---|---|---|
| Chrome | 62 | 20.00 | 20 | 0 |
| Firefox | 21 | 6.77 | 7 | 13 |
| Safari | 12 | 3.87 | 4 | 16 |

Check: `cells + track = 20` on every row; the longest bar is exactly `W`; every `│` in the same column.

### hbar — several series (grouped)

Each category on its own line, then one indented row per series; a blank line between categories. The
series names are in the rows, so no legend is needed. Scale everything to the **overall** maximum.

```json
{ "chartType": "hbar", "border": "none", "width": 12, "labels": ["Q1", "Q2"], "series": [{ "name": "2025", "values": [30, 45] }, { "name": "2026", "values": [36, 48] }] }
```

```
Q1
  2025 │ ████████░░░░ 30
  2026 │ █████████░░░ 36

Q2
  2025 │ ███████████░ 45
  2026 │ ████████████ 48
```

Working: max = 48, W = 12: 30 → 7.5 → **8**; 36 → 9; 45 → 11.25 → 11; 48 → 12.

### hbar — stacked (parts of a whole)

Segments of one bar, series 1 first. The segments must add up to the bar's total **exactly**, so split
with the largest-remainder method:

```
total cells = round(row_sum / max_row_sum × W)
exact_i     = v_i / row_sum × total
cells_i     = floor(exact_i); give the cells still missing, one each, to the largest fractional parts
row         = label │ segments, then spaces up to W, then the row sum; legend below
```

```json
{ "chartType": "hbar", "stacked": true, "border": "none", "width": 20, "labels": ["EMEA", "APAC"], "series": [{ "name": "Product", "values": [40, 25] }, { "name": "Services", "values": [20, 10] }] }
```

```
EMEA │ █████████████▓▓▓▓▓▓▓ 60
APAC │ █████████▓▓▓         35

█ Product   ▓ Services
```

| row | sum | total cells | exact | floor | +1 to largest remainder | result |
|---|---|---|---|---|---|---|
| EMEA | 60 | 20 | 13.33, 6.67 | 13, 6 | Services (.67) | 13 + 7 |
| APAC | 35 | round(11.67) = 12 | 8.57, 3.43 | 8, 3 | Product (.57) | 9 + 3 |

Check: segments + padding = W on every row; the legend glyphs are the segment glyphs, in order.

### hbar — negative values (diverging)

Bars grow left and right from a zero axis. The axis column belongs to no bar.

```
unit     = (W − 1) / (max − min)                 min < 0 (and max ≥ 0)
axis     = round(−min × unit)                    the column of ¦, counting from 0
cells    = round(|v| × unit)                     (≥ 1 if v ≠ 0)
v > 0: cells right of the axis;  v < 0: cells left of it;  0: nothing
```

```json
{ "chartType": "hbar", "border": "none", "width": 21, "labels": ["North", "South", "West"], "series": [{ "values": [8, -4, 2] }] }
```

```
North │        ¦█████████████ 8
South │ ███████¦              -4
West  │        ¦███           2
```

Working: min = −4, max = 8, W = 21, unit = 20 / 12 = 1.667, axis = round(6.67) = 7 (so 7 cells to its
left, 13 to its right); 8 → 13.3 → 13; −4 → 6.67 → 7; 2 → 3.33 → 3.

### vbar

Columns are drawn top row first. A bar of `rows` height fills the bottom `rows` rows of its column.

```
H       = rows (4–8)
rows    = round(v / max × H)        (≥ 1 if v ≠ 0)
b       = bar width in columns (2–4); 1 space between categories
row r (r = H at the top … 1 at the bottom): each bar shows "█" × b if rows ≥ r, else "░" × b
label   = centred under its bar
```

```json
{ "chartType": "vbar", "border": "none", "height": 5, "width": 11, "labels": ["Q1", "Q2", "Q3"], "series": [{ "values": [30, 45, 60] }] }
```

```
░░░ ░░░ ███
░░░ ███ ███
███ ███ ███
███ ███ ███
███ ███ ███
Q1  Q2  Q3
```

Working: max = 60, H = 5: 30 → 2.5 → **3**; 45 → 3.75 → 4; 60 → 5. Row 5 (top): only Q3 (5 ≥ 5); row 4:
Q2 and Q3; rows 3–1: all.

**Several series side by side**: each category holds one bar per series (`█`, `▓`, …) with no gap
between them; the category label is centred under the group; legend below.

```json
{ "chartType": "vbar", "border": "none", "height": 5, "width": 14, "labels": ["Q1", "Q2", "Q3"], "series": [{ "name": "2025", "values": [30, 45, 40] }, { "name": "2026", "values": [35, 50, 60] }] }
```

```
░░░░ ░░░░ ░░▓▓
░░░░ ██▓▓ ░░▓▓
██▓▓ ██▓▓ ██▓▓
██▓▓ ██▓▓ ██▓▓
██▓▓ ██▓▓ ██▓▓
 Q1   Q2   Q3

█ 2025   ▓ 2026
```

Working: max = 60, H = 5 — 2025: 3, 4, 3 rows; 2026: 3 (35 → 2.92), 4 (50 → 4.17), 5.

Check: every row has the same width; each column's filled rows equal its computed `rows`; vbar prints no
values, so if exact numbers matter, use hbar.

### dotplot

One row per category, a marker on a shared axis that does **not** start at zero — for close values.

```
col  = round((v − min) / (max − min) × (W − 1))       count columns from 0
row  = label │ "·" × W with ● at col, then the value; last line: value axis: [min, max]
```

```json
{ "chartType": "dotplot", "border": "none", "width": 11, "labels": ["Oakland", "Seattle", "Denver"], "series": [{ "values": [5.2, 4.4, 3.6] }] }
```

```
Oakland │ ··········● 5.20
Seattle │ ·····●····· 4.40
Denver  │ ●·········· 3.60
value axis: [3.60, 5.20]
```

Working: min = 3.6, max = 5.2, W − 1 = 10: 5.2 → 10; 4.4 → 5; 3.6 → 0.

---

## Tier B

### line

```
H rows, W columns; lo, hi = min and max of the data
row labels   value(r) = lo + (1 − r / (H − 1)) × (hi − lo),  r = 0 (top) … H − 1; right-aligned; then " ┤"
point i      column x = floor(i × (W − 1) / (n − 1)),  row y = round((1 − (v − lo) / (hi − lo)) × (H − 1))
joining      between two points, step along the longer direction; at each step round the other coordinate
             (a shallow segment: one cell per column; a steep one: one cell per row)
glyph        █ for the line; or · for the line and ● at each point (showPoints)
```

If the data crosses zero, the reference renderer widens the range slightly so that one row is exactly
0; by hand, choose H so that zero falls on a row, or skip that refinement.

```json
{ "chartType": "line", "border": "none", "height": 5, "width": 13, "labels": ["Mon", "Wed", "Fri"], "series": [{ "values": [10, 30, 20] }] }
```

```
30 ┤      ██     
25 ┤    ██  ███  
20 ┤   █       ██
15 ┤ ██          
10 ┤█            
    Mon  Wed  Fri
```

Working: labels 30, 25, 20, 15, 10. Points: x = 0, 6, 12; y = 4, 0, 2. Segment (0,4)→(6,0) is shallow
(6 columns, 4 rows): rows per column x = 0…6 are `4 − 4x/6` rounded → 4, 3, 3, 2, 1, 1, 0. Segment
(6,0)→(12,2): `2(x − 6)/6` → 0, 0, 1, 1, 1, 2, 2 for x = 6…12. X labels are centred under their points
and kept inside the plot.

With markers (`showPoints`), the same cells, `·` for the line and `●` on the points:

```json
{ "chartType": "line", "border": "none", "height": 5, "width": 13, "showPoints": true, "series": [{ "values": [10, 30, 20] }] }
```

```
30 ┤      ●·     
25 ┤    ··  ···  
20 ┤   ·       ·●
15 ┤ ··          
10 ┤●            
```

Check: one cell per column along a shallow segment; the top label is the maximum, the bottom one the
minimum; every row has the same width.

### area

A line filled down to zero. Compute the value at **every column** by linear interpolation, then fill from
its row down to the zero row.

```
pos = x × (n − 1) / (W − 1);  i = floor(pos);  f = pos − i;  value = v[i] × (1 − f) + v[i+1] × f
range: min(data, 0) … max(data, 0)
```

```json
{ "chartType": "area", "border": "none", "height": 4, "width": 12, "series": [{ "values": [1, 4, 2, 3] }] }
```

```
   4 ┤   ██       
2.67 ┤  ██████████
1.33 ┤████████████
   0 ┤████████████
```

Working: range 0…4, H = 4, rows are 4, 2.67, 1.33, 0. Column 3: pos = 3 × 3 / 11 = 0.82 → 1 + 0.82 × 3 =
3.45 → row round((1 − 3.45/4) × 3) = round(0.41) = 0, so column 3 is filled from the top row down.

### histogram

Count first, then draw an hbar of the counts.

```
width of a bin = (max − min) / bins
bin(v)         = floor((v − min) / width), the maximum goes into the last bin
label          = "a..b" for each bin
```

```json
{ "chartType": "histogram", "border": "none", "bins": 3, "width": 12, "series": [{ "values": [3, 5, 7, 8, 9, 12, 14, 15, 21] }] }
```

```
3..9   │ ████████████ 4
9..15  │ █████████    3
15..21 │ ██████       2
```

Working: min 3, max 21, 3 bins of 6: [3, 9) holds 3, 5, 7, 8; [9, 15) holds 9, 12, 14; [15, 21] holds 15,
21. Counts 4, 3, 2 → bars of 12, 9, 6 (W = 12, max 4). No track in a histogram.

### boxplot

Compute the five numbers first; the quartiles interpolate between sorted values.

```
sort the values; n of them
Q(q) = s[a] + (s[b] − s[a]) × (p − a),  p = q × (n − 1), a = floor(p), b = ceil(p)
min, Q(0.25), median Q(0.5), Q(0.75), max
col(v) = round((v − min) / (max − min) × (W − 1))
row: ─ from min to max, █ from Q1 to Q3, then ├ at min, ┤ at max, ║ at the median; the numbers after it
```

```json
{ "chartType": "boxplot", "border": "none", "width": 21, "series": [{ "name": "api", "values": [12, 15, 18, 20, 22, 25, 40] }] }
```

```
api │ ├──███║██───────────┤  min=12 q1=16.50 med=20 q3=23.50 max=40
```

Working: n = 7. Q1: p = 1.5 → 15 + (18 − 15) × 0.5 = 16.5; median: p = 3 → 20; Q3: p = 4.5 → 22 + 3 × 0.5 =
23.5. Columns (W − 1 = 20, range 28): 0, 3.2 → 3, 5.7 → 6, 8.2 → 8, 20.

### heatmap

A grid of shaded cells, one row per series.

```
norm  = (v − min) / (max − min)
shade = "░▒▓█"[min(3, floor(norm × 4))]         every value is visible: never a blank cell
cell  = the shade × 3 (or wider), one space between cells; column headers centred over the cells
```

```json
{ "chartType": "heatmap", "border": "none", "width": 15, "labels": ["Mon", "Tue", "Wed", "Thu"], "series": [{ "name": "am", "values": [2, 4, 6, 8] }, { "name": "pm", "values": [9, 7, 5, 3] }] }
```

```
   Mon Tue Wed Thu 
am ░░░ ▒▒▒ ▓▓▓ ███ 
pm ███ ▓▓▓ ▒▒▒ ░░░ 
```

Working: min 2, max 9: 2 → 0 `░`; 4 → 1.14 → 1 `▒`; 6 → 2.29 → 2 `▓`; 8 → 3.43 → 3 `█`; 9 → 4 → 3 `█`;
7 → 2.86 → 2 `▓`; 5 → 1.71 → 1 `▒`; 3 → 0.57 → 0 `░`.

### scatter (a few points)

```
col = round((x − xmin) / (xmax − xmin) × (W − 1));  row = H − 1 − round((y − ymin) / (ymax − ymin) × (H − 1))
one marker per series (● ○ ▲ ■); two series on one cell: *; last line: x: [xmin, xmax]  y: [ymin, ymax]
```

```json
{ "chartType": "scatter", "border": "none", "width": 11, "height": 5, "series": [{ "name": "A", "points": [{ "x": 0, "y": 0 }, { "x": 5, "y": 4 }, { "x": 10, "y": 2 }] }] }
```

```
     ●     
           
          ●
           
●          
x: [0, 10]  y: [0, 4]
```

Working: (0, 0) → column 0, row 4; (5, 4) → column 5, row 0; (10, 2) → column 10, row 2.

---

## Tier C — use a tool, or draw the simpler equivalent

### pie

A pie needs an angle test for every cell — unreliable by hand. **Without a tool, draw a 100% stacked
bar** instead: it shows the same shares, and lengths are easier to compare than angles anyway.

```json
{ "chartType": "hbar", "stacked": true, "border": "none", "width": 20, "labels": ["share"], "series": [{ "name": "Chrome", "values": [60] }, { "name": "Safari", "values": [25] }, { "name": "Other", "values": [15] }] }
```

```
share │ ████████████▓▓▓▓▓▒▒▒ 100

█ Chrome   ▓ Safari   ▒ Other
```

Working: 60 %, 25 %, 15 % of 20 cells = 12, 5, 3 (the largest-remainder rule when they don't divide
evenly). Add the percentages to the legend if they matter: `█ Chrome 60%`.

For reference, the pie the renderer draws for the same data (16 columns):

```json
{ "chartType": "pie", "border": "none", "width": 16, "series": [{ "name": "Chrome", "values": [60] }, { "name": "Safari", "values": [25] }, { "name": "Other", "values": [15] }] }
```

```
    ▒▒▒▒████    
  ▒▒▒▒▒▒██████  
 ▓▓▓▒▒▒▒███████ 
▓▓▓▓▓▓▓▒████████
▓▓▓▓▓▓▓█████████
 ▓▓▓▓▓█████████ 
  ▓▓██████████  
    ████████    

█ Chrome: 60 (60.0%)
▓ Safari: 25 (25.0%)
▒ Other: 15 (15.0%)
```

### dual_axis

Two lines on independent scales share one grid — two sets of row labels, two interpolations, crossings.
**Without a tool, draw two small line charts one above the other**, each with its own axis, same width
and the same x labels. For reference, the renderer's version:

```json
{ "chartType": "dual_axis", "border": "none", "height": 4, "width": 13, "series": [{ "name": "Temp", "values": [10, 16, 14] }, { "name": "Humidity", "values": [80, 60, 70] }] }
```

```
16 ┤▒    ████    ├ 80   
14 ┤ ▒▒██    ████├ 73.33
12 ┤ ██▒▒    ▒▒▒▒├ 66.67
10 ┤█    ▒▒▒▒    ├ 60   

left:  █ Temp
right: ▒ Humidity
```

### Anything large

More than ~10 bars, plots wider than ~30 columns or taller than ~8 rows, many series: the counting error
grows with size. Use a tool, or reduce (top-N, fewer points, a smaller plot) and say what you left out.

---

## Frames

Add a frame only when it is asked for. Then:

```
inner  = width of the widest line (count every character; CJK and most emoji count 2)
top    = "┌" + "─" × (inner + 2) + "┐"
title  = "│ " + title centred in inner (the extra space goes right) + " │", then "├" + "─" × (inner + 2) + "┤"
row    = "│ " + line + spaces up to inner + " │"
bottom = "└" + "─" × (inner + 2) + "┘"
```

```json
{ "chartType": "hbar", "title": "Browsers", "width": 10, "labels": ["Chrome", "Safari"], "series": [{ "values": [62, 21] }] }
```

```
┌────────────────────────┐
│        Browsers        │
├────────────────────────┤
│ Chrome │ ██████████ 62 │
│ Safari │ ███░░░░░░░ 21 │
└────────────────────────┘
```

Working: the widest line `Chrome │ ██████████ 62` is 6 + 3 + 10 + 3 = 22, so the rules are 24 `─`; the title
(8) gets 7 spaces on each side. Use only `┌┐└┘─│├┤` (or `+ - |`): heavy and rounded corners are missing
from common fonts.

---

## Self-check before you answer

- [ ] Every length was computed from a formula above, and the table of numbers matches the drawing.
- [ ] On every bar row, filled cells + track (or padding) = the bar length.
- [ ] The longest bar is exactly the full length; the maximum of a sparkline is `█`.
- [ ] Every line of the chart has the same width (count them; with a frame, the right border is straight).
- [ ] Labels are padded so all `│` separators line up.
- [ ] Bars start at zero, or grow both ways from a marked axis.
- [ ] Each series has its own glyph; the legend shows the same glyphs in the same order.
- [ ] The values are printed where the drawing is approximate.
- [ ] The chart is in a fenced code block.
- [ ] Tier C without a tool: you drew the simpler equivalent and said so.
