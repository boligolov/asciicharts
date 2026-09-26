# Changelog — asciicharts principles

Versions of the principles (`principles.md`) and of the conformance suite (`conformance/`). A change to
how any chart is drawn is a change to the principles: it gets an entry here and regenerated conformance
outputs, never a silent edit.

## v1.2 — 2026-09-26

From an agent's review of the skill: it drew twelve charts of browser shares and reported what it had to
work around.

- **A number within 1e−9 of the nearest integer prints as that integer** (§4.13). v1.1 compared with
  `trunc(v)`, so float noise *below* an integer was not absorbed: a stacked bar whose shares add up to
  `99.99999999999999` printed its total as `100.00`, next to rows that printed `100`. Conformance: 4
  corpus cases (histogram edges such as `84.00`, now `84`), one MCP answer, and a curated case pins it
  (`number/an integer reached from below`).
- **A threshold label that states its value prints alone** (§5.6): `5%`, not `5%: 5`. A label states
  the value when a number in it equals the value; `p99 goal` for 9 still prints `p99 goal: 9`.
  Conformance: no corpus case has such a label; a curated case pins it
  (`rule/a threshold label that states its value`).
- **A sparkline prints its range** (§7): `p99 ▃▅▄█▂▆▇▁▅█▃ 2..9`, one number for a flat series. Each
  series has its own scale, and without the range the ticks said nothing about the values — the agent
  wrote min and max into the title by hand. Names are padded to the widest and ticks to the longest
  series, so the ranges line up. Conformance: the 30 sparkline corpus cases, 54 MCP answers, the gallery
  example, two curated cases, and a new one pins the alignment (`rule/sparkline ranges line up`).
- **A heatmap has a legend** (§7): after a blank line, `░ 3.50..18.88   ▒ 18.88..34.25   ▓ …   █ …`, the
  four equal buckets of the data's range; with color, the ramp and `lo..hi`; all values equal, the one
  shade and the value. The shades had no key at all, against "print the numbers". Conformance: the 30
  heatmap corpus cases, 47 MCP answers, the gallery example, three curated cases; two new ones pin it
  (`rule/heatmap legend`, `rule/heatmap legend in color`).

## v1.1, moved into docs — 2026-09-26

No rule changed. The principles, this changelog and their licence moved from `spec/` to `docs/spec/`, with
the rest of the documentation.

## v1.1, suite moved — 2026-09-26

No rule changed. The conformance suite moved from `spec/conformance/` to `test/conformance/`, next to the
other checks of the repository; it is still CC BY 4.0 (`test/conformance/LICENSE`).

## v1.1 — 2026-09-24

- **Stacked bars with negatives draw their zero axis** (§4.6): `¦` (`+` in the ascii style) in hbar, a
  row of `-` in vbar, owned by no bar, as for diverging bars (§4.5). In v1.0 a stack's zero was only
  where one glyph met another — against R6 ("grow both ways from a marked zero axis") and invisible in a
  row without negatives. Hand-drawn evals found it: agents asked for a zero line had to add one the
  renderer did not draw. One cell (row) of the plot is now the axis, so each side has `N − 1` to share.
- Conformance: 6 corpus cases change (stacked hbar and vbar with negatives), the gallery's stacked
  diverging example, and two curated cases pin the rule (`rule/diverging stacked hbar`,
  `rule/diverging stacked vbar`; 107 curated cases).

## v1.0, clarified — 2026-09-24

No rule changed. §4.13 now says that floor(log10 |v|) uses a correctly rounded log10 — right under a
power of ten an ulp decides the number of digits (the Go port found it); the curated case
`number/next to a power of ten` pins it (105 curated cases).

## v1.0 — 2026-09-24

The first published version. The rules as they stood after the analysis of the reference
implementation and the fixes it led to (principles §11, second table):

- Levels (heatmap shades and colors, sparkline ticks) are equal buckets; a heatmap cell is never blank.
- The zero line of a diverging bar chart is an axis that belongs to no bar (`¦` in hbar, `-` in vbar);
  every non-zero bar keeps at least one cell.
- Reference lines (thresholds) are drawn behind the data.
- Values below 1 print two significant digits; axis labels are rounded to 12 significant digits first;
  there is no negative zero.
- All-equal data gets a range centred on its value, and printed ranges are the data's own.
- The ascii style's series ramp contains none of its structural glyphs.
- The boxplot median is `║` (WGL4); font safety is defined by the WGL4 set.
- Markers of different series on one cell show `*` and an `* overlap` note.
- When a line, area or dual_axis range crosses zero, zero falls on a labelled row.
- Every non-zero pie slice and every non-zero segment of a stacked bar owns at least one cell.

The conformance suite (317 corpus cases, 104 curated cases, 31 gallery examples) reflects exactly these rules; its first
version was captured from the original Go implementation and regenerated, case by reviewed case, with
each fix above.
