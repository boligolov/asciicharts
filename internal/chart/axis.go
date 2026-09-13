package chart

import (
	"fmt"
	"math"
	"strings"
)

// xPixel linearly maps sample index i (0..n-1) onto a 0..span-1 coordinate
// space (either pixels or character columns).
func xPixel(i, n, span int) int {
	if n <= 1 || span <= 1 {
		return 0
	}
	return i * (span - 1) / (n - 1)
}

// yPixel maps value v within [min, max] onto a 0..span-1 coordinate space,
// inverted so that max lands at row 0 (top).
func yPixel(v, min, max float64, span int) int {
	if span <= 1 {
		return 0
	}
	if max == min {
		return span - 1
	}
	frac := (v - min) / (max - min)
	return int(math.Round((1 - frac) * float64(span-1)))
}

func seriesMinMax(series []Series) (float64, float64) {
	min, max := math.Inf(1), math.Inf(-1)
	for _, s := range series {
		for _, v := range s.Values {
			min = math.Min(min, v)
			max = math.Max(max, v)
		}
	}
	if math.IsInf(min, 1) {
		return 0, 1
	}
	if min == max {
		max = min + 1
	}
	return min, max
}

func seriesMaxLen(series []Series) int {
	n := 0
	for _, s := range series {
		if len(s.Values) > n {
			n = len(s.Values)
		}
	}
	return n
}

// leftAxisLabels returns one value label per canvas row (row 0 = max,
// last row = min), plus the width of the widest label.
func leftAxisLabels(min, max float64, height int) ([]string, int) {
	labels := make([]string, height)
	maxWidth := 0
	for row := 0; row < height; row++ {
		frac := 1.0
		if height > 1 {
			frac = 1 - float64(row)/float64(height-1)
		}
		s := formatValue(min + frac*(max-min))
		labels[row] = s
		if w := len([]rune(s)); w > maxWidth {
			maxWidth = w
		}
	}
	return labels, maxWidth
}

// xAxisLabels renders a single row of category labels under a plot,
// centered under the character column each corresponds to, prefixed by
// leftPad spaces to align under the plot area (past the left axis
// column). Returns "" if labels doesn't have exactly n entries.
func xAxisLabels(labels []string, n, plotWidth, leftPad int) string {
	if len(labels) != n || n == 0 || plotWidth <= 0 {
		return ""
	}
	row := make([]rune, plotWidth)
	for i := range row {
		row[i] = ' '
	}
	for i, lbl := range labels {
		x := xPixel(i, n, plotWidth)
		cell := []rune(truncateRunes(lbl, 8))
		start := x - len(cell)/2
		for j, r := range cell {
			pos := start + j
			if pos >= 0 && pos < plotWidth {
				row[pos] = r
			}
		}
	}
	return strings.Repeat(" ", leftPad) + strings.TrimRight(string(row), " ")
}

// legendSwatch renders the marker used to represent series i in a legend:
// a colored fill glyph when color is enabled, otherwise a distinct plain
// glyph per series index.
func legendSwatch(i int, colorOn bool) string {
	return legendSwatchRamp(i, colorOn, fills)
}

// legendSwatchRamp is legendSwatch with an explicit fill-glyph ramp, so a
// legend can match bars rendered with a non-default ramp (e.g. the
// halftone bar style).
func legendSwatchRamp(i int, colorOn bool, ramp []rune) string {
	ch := string(ramp[i%len(ramp)])
	return colorize(ch, seriesColor(i), colorOn)
}

func seriesLabel(s Series, i int) string {
	if s.Name != "" {
		return s.Name
	}
	return fmt.Sprintf("series %d", i+1)
}

func legendLine(series []Series, colorOn bool) string {
	names := make([]string, len(series))
	for i, s := range series {
		names[i] = seriesLabel(s, i)
	}
	return namedLegend(names, colorOn)
}

// noShapeCaveat explains why a legend below it can't show a per-series
// swatch: quad/braille pack every series' dots into the same shared
// sub-character bits, so without color there is nothing shape-wise to
// distinguish them by — a colored/shaped swatch there would claim a
// distinction the chart doesn't actually draw.
const noShapeCaveat = `quad/braille dots from every series share the same sub-character bits and can't be told apart by shape — pass useColor: "on" to tell them apart, or use mode: "cell"`

// plainNameList renders a legend as just the series names plus
// noShapeCaveat, for a chart where no glyph or color actually distinguishes
// them in the body. The caveat is word-wrapped to width (the chart's own
// plot width, roughly) instead of left as one long line — border.Wrap sizes
// the whole frame to its widest line, so an unwrapped sentence here would
// balloon a narrow chart's frame just to fit it.
func plainNameList(names []string, width int) string {
	return strings.Join(names, ", ") + "\n(" + strings.Join(wrapText(noShapeCaveat, max(width, 40)), "\n") + ")"
}

// wrapText greedily wraps s into lines of at most width runes, breaking
// only at spaces.
func wrapText(s string, width int) []string {
	words := strings.Fields(s)
	if len(words) == 0 {
		return nil
	}
	lines := []string{words[0]}
	for _, w := range words[1:] {
		last := lines[len(lines)-1]
		if len([]rune(last))+1+len([]rune(w)) > width {
			lines = append(lines, w)
		} else {
			lines[len(lines)-1] = last + " " + w
		}
	}
	return lines
}

func namedLegend(names []string, colorOn bool) string {
	return namedLegendRamp(names, colorOn, fills)
}

// namedLegendRamp is namedLegend with an explicit fill-glyph ramp.
func namedLegendRamp(names []string, colorOn bool, ramp []rune) string {
	parts := make([]string, len(names))
	for i, name := range names {
		parts[i] = fmt.Sprintf("%s %s", legendSwatchRamp(i, colorOn, ramp), name)
	}
	return strings.Join(parts, "   ")
}
