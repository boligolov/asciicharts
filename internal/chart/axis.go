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
	ch := string(fills[i%len(fills)])
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

func namedLegend(names []string, colorOn bool) string {
	parts := make([]string, len(names))
	for i, name := range names {
		parts[i] = fmt.Sprintf("%s %s", legendSwatch(i, colorOn), name)
	}
	return strings.Join(parts, "   ")
}
