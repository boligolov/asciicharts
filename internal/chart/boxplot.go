package chart

import (
	"fmt"
	"math"
	"sort"
	"strings"
	"unicode/utf8"
)

type fiveNumber struct {
	min, q1, median, q3, max float64
}

// quantile computes q (0..1) over an already-sorted slice using linear
// interpolation between closest ranks.
func quantile(sorted []float64, q float64) float64 {
	n := len(sorted)
	if n == 1 {
		return sorted[0]
	}
	pos := q * float64(n-1)
	lo, hi := int(math.Floor(pos)), int(math.Ceil(pos))
	if lo == hi {
		return sorted[lo]
	}
	frac := pos - float64(lo)
	return sorted[lo] + (sorted[hi]-sorted[lo])*frac
}

func summarize(values []float64) fiveNumber {
	sorted := append([]float64(nil), values...)
	sort.Float64s(sorted)
	return fiveNumber{
		min:    sorted[0],
		q1:     quantile(sorted, 0.25),
		median: quantile(sorted, 0.5),
		q3:     quantile(sorted, 0.75),
		max:    sorted[len(sorted)-1],
	}
}

func renderBoxplot(in Input) (string, error) {
	width := in.Width
	if width <= 0 {
		width = 40
	}

	summaries := make([]fiveNumber, len(in.Series))
	names := make([]string, len(in.Series))
	globalMin, globalMax := math.Inf(1), math.Inf(-1)
	for i, s := range in.Series {
		if len(s.Values) == 0 {
			return "", fmt.Errorf("series %d %q must contain at least one value", i, s.Name)
		}
		summaries[i] = summarize(s.Values)
		names[i] = seriesLabel(s, i)
		globalMin = math.Min(globalMin, summaries[i].min)
		globalMax = math.Max(globalMax, summaries[i].max)
	}
	if globalMax == globalMin {
		globalMax = globalMin + 1
	}

	maxNameW := 0
	for _, n := range names {
		maxNameW = max(maxNameW, utf8.RuneCountInString(n))
	}

	colorOn := in.UseColor.enabled()
	pos := func(v float64) int {
		return clampInt(int(math.Round((v-globalMin)/(globalMax-globalMin)*float64(width-1))), 0, width-1)
	}

	lines := make([]string, len(summaries))
	for i, fn := range summaries {
		row := make([]rune, width)
		for x := range row {
			row[x] = ' '
		}

		minP, q1P, medP, q3P, maxP := pos(fn.min), pos(fn.q1), pos(fn.median), pos(fn.q3), pos(fn.max)

		for x := minP; x <= maxP; x++ {
			row[x] = '─'
		}
		for x := q1P; x <= q3P; x++ {
			row[x] = '█'
		}
		row[minP] = '├'
		row[maxP] = '┤'
		row[medP] = '┃'

		body := colorize(string(row), seriesColor(i), colorOn)
		name := names[i] + strings.Repeat(" ", maxNameW-utf8.RuneCountInString(names[i]))
		lines[i] = fmt.Sprintf("%s │ %s  min=%s q1=%s med=%s q3=%s max=%s",
			name, body, formatValue(fn.min), formatValue(fn.q1), formatValue(fn.median), formatValue(fn.q3), formatValue(fn.max))
	}

	return strings.Join(lines, "\n"), nil
}
