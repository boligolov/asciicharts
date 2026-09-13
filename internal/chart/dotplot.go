package chart

import (
	"fmt"
	"math"
	"strings"
	"unicode/utf8"
)

// renderDotPlot draws a Cleveland dot plot: one row per category, a marker
// placed at each series' value along a shared numeric axis, connected to
// the left edge by a light leader line. Unlike vbar/hbar, the axis is not
// forced to include zero — it's scaled to the data's actual range, since a
// dot's position (not a filled run's length) carries the value.
func renderDotPlot(in Input) (string, error) {
	labels, names, matrix, err := barsMatrix(in)
	if err != nil {
		return "", err
	}

	width := in.Width
	if width <= 0 {
		width = 40
	}
	colorOn := in.UseColor.enabled()
	numSeries := len(names)

	minVal, maxVal := matrix[0][0], matrix[0][0]
	for _, row := range matrix {
		for _, v := range row {
			minVal = math.Min(minVal, v)
			maxVal = math.Max(maxVal, v)
		}
	}
	if maxVal == minVal {
		maxVal = minVal + 1
	}

	maxLabel := 0
	for _, l := range labels {
		maxLabel = max(maxLabel, utf8.RuneCountInString(l))
	}

	lines := make([]string, len(labels))
	for c, lbl := range labels {
		row := make([]rune, width)
		colorRow := make([]int, width)
		for i := range row {
			row[i] = '·'
			colorRow[i] = -1
		}
		for s := 0; s < numSeries; s++ {
			v := matrix[s][c]
			col := clampInt(int(math.Round((v-minVal)/(maxVal-minVal)*float64(width-1))), 0, width-1)
			row[col] = markers[s%len(markers)]
			if colorOn {
				colorRow[col] = seriesColor(s)
			}
		}
		var sb strings.Builder
		for i, r := range row {
			sb.WriteString(colorize(string(r), colorRow[i], colorOn))
		}
		pad := strings.Repeat(" ", maxLabel-utf8.RuneCountInString(lbl))
		line := fmt.Sprintf("%s%s │ %s", lbl, pad, sb.String())
		if numSeries == 1 {
			line += " " + formatValue(matrix[0][c])
		}
		lines[c] = line
	}

	body := strings.Join(lines, "\n")
	body += fmt.Sprintf("\nvalue axis: [%s, %s]", formatValue(minVal), formatValue(maxVal))
	if numSeries > 1 {
		body += "\n" + namedLegendRamp(names, colorOn, markers)
	}

	return body, nil
}
