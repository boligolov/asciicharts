package chart

import (
	"fmt"
	"math"
	"sort"
	"strings"
	"unicode/utf8"
)

func renderBar(in Input) (string, error) {
	labels, names, matrix, err := barsMatrix(in)
	if err != nil {
		return "", err
	}

	width := in.Width
	if width <= 0 {
		width = 40
	}
	height := in.Height
	if height <= 0 {
		height = 10
	}
	colorOn := in.UseColor.enabled()
	ramp := barFillRamp(in.Style)

	if in.ChartType == VBar {
		return renderVBar(labels, names, matrix, in.Width, height, in.Stacked, colorOn, ramp), nil
	}

	if len(names) == 1 {
		return renderHorizontalBars(labels, matrix[0], width, ramp), nil
	}
	if in.Stacked {
		return renderHBarStacked(labels, names, matrix, width, colorOn, ramp), nil
	}
	return renderHBarGrouped(labels, names, matrix, width, colorOn, ramp), nil
}

// barFillRamp resolves a bar chart's style into a fill-glyph ramp: nil for
// the default "solid" style (flat blocks with eighth-block sub-character
// precision), or a textured/tiled ramp for "halftone" and "ascii".
func barFillRamp(style string) []rune {
	switch style {
	case "halftone":
		return halftoneFills
	case "ascii":
		return asciiFills
	default:
		return nil
	}
}

// barsMatrix normalizes bar/histogram-style input into a category label
// list, a series name list, and a [series][category] value matrix.
func barsMatrix(in Input) (labels []string, names []string, matrix [][]float64, err error) {
	if len(in.Series) == 0 {
		return nil, nil, nil, fmt.Errorf("series must contain at least one entry")
	}
	n := len(in.Series[0].Values)
	if n == 0 {
		return nil, nil, nil, fmt.Errorf("series must contain at least one value")
	}
	for i, s := range in.Series {
		if len(s.Values) != n {
			return nil, nil, nil, fmt.Errorf("all series must have the same number of values (series 0 has %d, series %d has %d)", n, i, len(s.Values))
		}
	}

	labels = in.Labels
	if len(labels) > 0 && len(labels) != n {
		return nil, nil, nil, fmt.Errorf("labels length (%d) must match each series' values length (%d)", len(labels), n)
	}
	if len(labels) == 0 {
		labels = make([]string, n)
		for i := range labels {
			labels[i] = fmt.Sprintf("%d", i+1)
		}
	}

	names = make([]string, len(in.Series))
	matrix = make([][]float64, len(in.Series))
	for i, s := range in.Series {
		names[i] = seriesLabel(s, i)
		matrix[i] = s.Values
	}
	return labels, names, matrix, nil
}

// diverging2 orders two row/column indices so the lower one comes first,
// giving an inclusive [lo, hi] span to fill for a bar that may grow toward
// either endpoint from a shared zero baseline.
func diverging2(a, b int) (lo, hi int) {
	if a > b {
		return b, a
	}
	return a, b
}

// allocateProportional splits total units across values proportionally,
// using the largest-remainder method so the parts sum to exactly total.
func allocateProportional(values []float64, sum float64, total int) []int {
	n := len(values)
	result := make([]int, n)
	if sum <= 0 || total <= 0 {
		return result
	}
	fracs := make([]float64, n)
	allocated := 0
	for i, v := range values {
		exact := v / sum * float64(total)
		result[i] = int(exact)
		fracs[i] = exact - float64(result[i])
		allocated += result[i]
	}
	remainder := total - allocated
	idx := make([]int, n)
	for i := range idx {
		idx[i] = i
	}
	sort.Slice(idx, func(a, b int) bool { return fracs[idx[a]] > fracs[idx[b]] })
	for i := 0; i < remainder && i < n; i++ {
		result[idx[i]]++
	}
	return result
}

func renderVBar(labels, names []string, matrix [][]float64, width, height int, stacked, colorOn bool, ramp []rune) string {
	numCat := len(labels)
	numSeries := len(matrix)
	const gap = 1

	// Stacked bars are a single column per category; grouped bars are
	// numSeries columns per category. barWidth thickens each of those
	// columns so the chart fills a requested total width, rather than
	// always being a single character thick.
	barsPerGroup := numSeries
	if stacked {
		barsPerGroup = 1
	}
	barWidth := 1
	if width > 0 {
		if avail := width - (numCat-1)*gap; avail > 0 {
			if bw := avail / (numCat * barsPerGroup); bw > 1 {
				barWidth = bw
			}
		}
	}

	maxLabelW := 0
	for _, l := range labels {
		maxLabelW = max(maxLabelW, utf8.RuneCountInString(l))
	}
	groupW := max(barsPerGroup*barWidth, maxLabelW)
	barsOffset := (groupW - barsPerGroup*barWidth) / 2

	totalW := numCat*groupW + (numCat-1)*gap
	if totalW < 1 {
		totalW = 1
	}

	grid := make([][]rune, height)
	colorGrid := make([][]int, height)
	for r := range grid {
		grid[r] = make([]rune, totalW)
		colorGrid[r] = make([]int, totalW)
		for x := range grid[r] {
			grid[r][x] = ' '
			colorGrid[r][x] = -1
		}
	}

	if stacked {
		maxSum := 0.0
		for c := 0; c < numCat; c++ {
			sum := 0.0
			for s := 0; s < numSeries; s++ {
				sum += matrix[s][c]
			}
			maxSum = math.Max(maxSum, sum)
		}
		if maxSum == 0 {
			maxSum = 1
		}
		for c := 0; c < numCat; c++ {
			colStart := c*(groupW+gap) + barsOffset
			values := make([]float64, numSeries)
			colSum := 0.0
			for s := 0; s < numSeries; s++ {
				values[s] = matrix[s][c]
				colSum += values[s]
			}
			totalRows := int(math.Round(colSum / maxSum * float64(height)))
			alloc := allocateProportional(values, colSum, totalRows)
			cursor := 0
			segRamp := ramp
			if segRamp == nil {
				segRamp = fills
			}
			for s, segRows := range alloc {
				ch := segRamp[s%len(segRamp)]
				color := -1
				if colorOn {
					color = seriesColor(s)
				}
				for r := 0; r < segRows; r++ {
					row := height - 1 - cursor - r
					if row < 0 || row >= height {
						continue
					}
					for w := 0; w < barWidth; w++ {
						grid[row][colStart+w] = ch
						colorGrid[row][colStart+w] = color
					}
				}
				cursor += segRows
			}
		}
	} else {
		// minVal/maxVal always include 0, so a chart of all-positive values
		// keeps the familiar bottom-anchored baseline (minVal == 0, the
		// !diverging path below, byte-for-byte the old behavior), while any
		// negative value switches to a diverging chart with the zero
		// baseline computed from the actual data range — bars can then grow
		// either up or down from it, like Bloomberg's growth-rate charts.
		minVal, maxVal := 0.0, 0.0
		for s := 0; s < numSeries; s++ {
			for c := 0; c < numCat; c++ {
				minVal = math.Min(minVal, matrix[s][c])
				maxVal = math.Max(maxVal, matrix[s][c])
			}
		}
		if maxVal == minVal {
			maxVal = minVal + 1
		}
		diverging := minVal < 0
		zeroRow := clampInt(yPixel(0, minVal, maxVal, height), 0, height-1)

		// Grouped bars with more than one series need a per-series glyph
		// even in the default "solid" style — otherwise every series
		// renders as an identical flat block, indistinguishable from each
		// other without color even though the legend below (which always
		// shows a distinct swatch per series) implies they aren't. A lone
		// series keeps full eighth-block sub-row precision, since there's
		// no ambiguity to resolve and no shade/letter character has an
		// eighths ramp to give up.
		effectiveRamp := ramp
		if effectiveRamp == nil && numSeries > 1 {
			effectiveRamp = fills
		}

		for c := 0; c < numCat; c++ {
			for s := 0; s < numSeries; s++ {
				colStart := c*(groupW+gap) + barsOffset + s*barWidth
				v := matrix[s][c]
				color := -1
				if colorOn {
					color = seriesColor(s)
				}

				if effectiveRamp != nil {
					ch := effectiveRamp[s%len(effectiveRamp)]
					if !diverging {
						rows := int(math.Round(v / maxVal * float64(height)))
						for w := 0; w < barWidth; w++ {
							col := colStart + w
							for r := 0; r < rows && r < height; r++ {
								grid[height-1-r][col] = ch
								colorGrid[height-1-r][col] = color
							}
						}
					} else {
						lo, hi := diverging2(zeroRow, yPixel(v, minVal, maxVal, height))
						for w := 0; w < barWidth; w++ {
							col := colStart + w
							for r := lo; r <= hi; r++ {
								grid[r][col] = ch
								colorGrid[r][col] = color
							}
						}
					}
					continue
				}

				if !diverging {
					eighthsTotal := int(math.Round(v / maxVal * float64(height) * 8))
					fullRows := eighthsTotal / 8
					frac := eighthsTotal % 8
					for w := 0; w < barWidth; w++ {
						col := colStart + w
						for r := 0; r < fullRows && r < height; r++ {
							grid[height-1-r][col] = '█'
							colorGrid[height-1-r][col] = color
						}
						if frac > 0 && fullRows < height {
							grid[height-1-fullRows][col] = eighthsUp[frac]
							colorGrid[height-1-fullRows][col] = color
						}
					}
				} else {
					lo, hi := diverging2(zeroRow, yPixel(v, minVal, maxVal, height))
					for w := 0; w < barWidth; w++ {
						col := colStart + w
						for r := lo; r <= hi; r++ {
							grid[r][col] = '█'
							colorGrid[r][col] = color
						}
					}
				}
			}
		}

		// A diverging chart's zero baseline sits somewhere in the middle of
		// the plot rather than at the bottom row, so draw a thin guide
		// across it wherever no bar already covers that row — without it,
		// nothing would show the reader where zero actually is.
		if diverging && minVal < 0 && maxVal > 0 {
			for x := 0; x < totalW; x++ {
				if grid[zeroRow][x] == ' ' {
					grid[zeroRow][x] = '-'
				}
			}
		}
	}

	var sb strings.Builder
	for r := 0; r < height; r++ {
		for x := 0; x < totalW; x++ {
			sb.WriteString(colorize(string(grid[r][x]), colorGrid[r][x], colorOn))
		}
		sb.WriteByte('\n')
	}

	labelRow := make([]rune, totalW)
	for i := range labelRow {
		labelRow[i] = ' '
	}
	for c, lbl := range labels {
		groupStart := c * (groupW + gap)
		cell := []rune(lbl)
		start := groupStart + (groupW-len(cell))/2
		for j, r := range cell {
			if pos := start + j; pos >= 0 && pos < totalW {
				labelRow[pos] = r
			}
		}
	}
	sb.WriteString(strings.TrimRight(string(labelRow), " "))

	body := sb.String()
	if numSeries > 1 {
		if ramp != nil {
			body += "\n\n" + namedLegendRamp(names, colorOn, ramp)
		} else {
			body += "\n\n" + namedLegend(names, colorOn)
		}
	}
	return body
}

func renderHBarGrouped(labels, names []string, matrix [][]float64, width int, colorOn bool, ramp []rune) string {
	minVal, maxVal := 0.0, 0.0
	for _, row := range matrix {
		for _, v := range row {
			minVal = math.Min(minVal, v)
			maxVal = math.Max(maxVal, v)
		}
	}
	if maxVal == minVal {
		maxVal = minVal + 1
	}
	diverging := minVal < 0
	zeroCol := 0
	if diverging {
		zeroCol = int(math.Round((0 - minVal) / (maxVal - minVal) * float64(width)))
	}

	maxNameW := 0
	for _, name := range names {
		maxNameW = max(maxNameW, utf8.RuneCountInString(name))
	}

	blocks := make([]string, len(labels))
	for c, lbl := range labels {
		lines := []string{lbl}
		for s, name := range names {
			v := matrix[s][c]
			var fillChar rune
			if ramp != nil {
				fillChar = ramp[s%len(ramp)]
			}
			var bar string
			if diverging {
				fc := fillChar
				if fc == 0 {
					fc = '█'
				}
				valCol := int(math.Round((v - minVal) / (maxVal - minVal) * float64(width)))
				bar = divergingBarRun(zeroCol, valCol, width, fc)
			} else {
				bar = renderBarRun(v/maxVal*float64(width), width, fillChar)
			}
			color := -1
			if colorOn {
				color = seriesColor(s)
			}
			pad := strings.Repeat(" ", maxNameW-utf8.RuneCountInString(name))
			lines = append(lines, fmt.Sprintf("  %s%s │ %s %s", name, pad, colorize(bar, color, colorOn), formatValue(v)))
		}
		blocks[c] = strings.Join(lines, "\n")
	}
	return strings.Join(blocks, "\n\n")
}

func renderHBarStacked(labels, names []string, matrix [][]float64, width int, colorOn bool, ramp []rune) string {
	maxSum := 0.0
	for c := range labels {
		sum := 0.0
		for s := range names {
			sum += matrix[s][c]
		}
		maxSum = math.Max(maxSum, sum)
	}
	if maxSum == 0 {
		maxSum = 1
	}
	maxLabelW := 0
	for _, l := range labels {
		maxLabelW = max(maxLabelW, utf8.RuneCountInString(l))
	}

	lines := make([]string, len(labels))
	for c, lbl := range labels {
		values := make([]float64, len(names))
		colSum := 0.0
		for s := range names {
			values[s] = matrix[s][c]
			colSum += values[s]
		}
		totalWidth := int(math.Round(colSum / maxSum * float64(width)))
		alloc := allocateProportional(values, colSum, totalWidth)

		segRamp := ramp
		if segRamp == nil {
			segRamp = fills
		}
		var bar strings.Builder
		usedWidth := 0
		for s, w := range alloc {
			ch := segRamp[s%len(segRamp)]
			color := -1
			if colorOn {
				color = seriesColor(s)
			}
			bar.WriteString(colorize(strings.Repeat(string(ch), w), color, colorOn))
			usedWidth += w
		}
		pad := strings.Repeat(" ", width-usedWidth)
		label := lbl + strings.Repeat(" ", maxLabelW-utf8.RuneCountInString(lbl))
		lines[c] = fmt.Sprintf("%s │ %s%s %s", label, bar.String(), pad, formatValue(colSum))
	}

	if ramp != nil {
		return strings.Join(lines, "\n") + "\n\n" + namedLegendRamp(names, colorOn, ramp)
	}
	return strings.Join(lines, "\n") + "\n\n" + namedLegend(names, colorOn)
}

func renderHorizontalBars(labels []string, values []float64, width int, ramp []rune) string {
	if width <= 0 {
		width = 40
	}

	maxLabel := 0
	for _, l := range labels {
		maxLabel = max(maxLabel, utf8.RuneCountInString(l))
	}

	var fillChar rune
	if ramp != nil {
		fillChar = ramp[0]
	}

	minVal, maxVal := 0.0, 0.0
	for _, v := range values {
		minVal = math.Min(minVal, v)
		maxVal = math.Max(maxVal, v)
	}
	if maxVal == minVal {
		maxVal = minVal + 1
	}

	lines := make([]string, len(values))
	if minVal < 0 {
		// Diverging: some value is negative, so bars grow left or right
		// from a shared zero column instead of always starting at 0 — see
		// divergingBarRun. Rounds to whole characters (no eighth-block
		// sub-character precision, since a bar can now end at either edge).
		fc := fillChar
		if fc == 0 {
			fc = '█'
		}
		zeroCol := int(math.Round((0 - minVal) / (maxVal - minVal) * float64(width)))
		for i, v := range values {
			label := labels[i]
			pad := strings.Repeat(" ", maxLabel-utf8.RuneCountInString(label))
			valCol := int(math.Round((v - minVal) / (maxVal - minVal) * float64(width)))
			bar := divergingBarRun(zeroCol, valCol, width, fc)
			lines[i] = fmt.Sprintf("%s%s │ %s %s", label, pad, bar, formatValue(v))
		}
		return strings.Join(lines, "\n")
	}

	for i, v := range values {
		label := labels[i]
		pad := strings.Repeat(" ", maxLabel-utf8.RuneCountInString(label))
		bar := renderBarRun(v/maxVal*float64(width), width, fillChar)
		lines[i] = fmt.Sprintf("%s%s │ %s %s", label, pad, bar, formatValue(v))
	}
	return strings.Join(lines, "\n")
}

// divergingBarRun draws a bar that starts at zeroCol and extends to valCol
// (either direction), with a thin '|' marking the zero column wherever the
// bar itself doesn't already cover it — used once any value in the chart is
// negative, so the reader can still see where zero falls.
func divergingBarRun(zeroCol, valCol, width int, fillChar rune) string {
	lo, hi := diverging2(zeroCol, valCol)
	lo = clampInt(lo, 0, width)
	hi = clampInt(hi, 0, width)
	row := make([]rune, width)
	for i := range row {
		row[i] = ' '
	}
	for i := lo; i < hi; i++ {
		row[i] = fillChar
	}
	if zeroCol >= 0 && zeroCol < width && row[zeroCol] == ' ' {
		row[zeroCol] = '|'
	}
	return string(row)
}

// renderBarRun draws a single horizontal run of length characters (out of
// maxWidth) as a text bar. With fillChar == 0, it uses solid blocks with
// eighth-block sub-character precision at the end. With fillChar set (the
// halftone/ascii bar styles), it fills whole characters with that glyph
// instead — a textured look at the cost of sub-character precision, since
// there's no fractional-width glyph for a shade or letter character.
func renderBarRun(length float64, maxWidth int, fillChar rune) string {
	if length < 0 {
		length = 0
	}

	if fillChar != 0 {
		full := int(math.Round(length))
		if full > maxWidth {
			full = maxWidth
		}
		return strings.Repeat(string(fillChar), full) + strings.Repeat(" ", maxWidth-full)
	}

	full := int(length)
	if full > maxWidth {
		full = maxWidth
	}
	frac := length - float64(full)

	var sb strings.Builder
	sb.WriteString(strings.Repeat(string(eighthsLeft[8]), full))
	if full < maxWidth {
		if idx := int(frac * 8); idx > 0 {
			sb.WriteRune(eighthsLeft[idx])
			full++
		}
	}
	sb.WriteString(strings.Repeat(" ", maxWidth-full))
	return sb.String()
}
