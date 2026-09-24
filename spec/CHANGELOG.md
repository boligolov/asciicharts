# Changelog — asciicharts principles

Versions of the principles (`principles.md`) and of the conformance suite (`conformance/`). A change to
how any chart is drawn is a change to the principles: it gets an entry here and regenerated conformance
outputs, never a silent edit.

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
