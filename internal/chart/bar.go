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

	if in.ChartType == VBar {
		return renderVBar(labels, names, matrix, in.Width, height, in.Stacked, colorOn), nil
	}

	if len(names) == 1 {
		return renderHorizontalBars(labels, matrix[0], width), nil
	}
	if in.Stacked {
		return renderHBarStacked(labels, names, matrix, width, colorOn), nil
	}
	return renderHBarGrouped(labels, names, matrix, width, colorOn), nil
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

func renderVBar(labels, names []string, matrix [][]float64, width, height int, stacked, colorOn bool) string {
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
			for s, segRows := range alloc {
				ch := fills[s%len(fills)]
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
		maxVal := 0.0
		for s := 0; s < numSeries; s++ {
			for c := 0; c < numCat; c++ {
				maxVal = math.Max(maxVal, matrix[s][c])
			}
		}
		if maxVal == 0 {
			maxVal = 1
		}
		for c := 0; c < numCat; c++ {
			for s := 0; s < numSeries; s++ {
				colStart := c*(groupW+gap) + barsOffset + s*barWidth
				v := matrix[s][c]
				eighthsTotal := int(math.Round(v / maxVal * float64(height) * 8))
				fullRows := eighthsTotal / 8
				frac := eighthsTotal % 8
				color := -1
				if colorOn {
					color = seriesColor(s)
				}
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
		body += "\n\n" + namedLegend(names, colorOn)
	}
	return body
}

func renderHBarGrouped(labels, names []string, matrix [][]float64, width int, colorOn bool) string {
	maxVal := 0.0
	for _, row := range matrix {
		for _, v := range row {
			maxVal = math.Max(maxVal, v)
		}
	}
	if maxVal == 0 {
		maxVal = 1
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
			bar := renderBarRun(v/maxVal*float64(width), width)
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

func renderHBarStacked(labels, names []string, matrix [][]float64, width int, colorOn bool) string {
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

		var bar strings.Builder
		usedWidth := 0
		for s, w := range alloc {
			ch := fills[s%len(fills)]
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

	return strings.Join(lines, "\n") + "\n\n" + namedLegend(names, colorOn)
}

func renderHorizontalBars(labels []string, values []float64, width int) string {
	if width <= 0 {
		width = 40
	}

	maxLabel := 0
	for _, l := range labels {
		maxLabel = max(maxLabel, utf8.RuneCountInString(l))
	}

	scale := 0.0
	for _, v := range values {
		scale = math.Max(scale, math.Abs(v))
	}
	if scale == 0 {
		scale = 1
	}

	lines := make([]string, len(values))
	for i, v := range values {
		label := labels[i]
		pad := strings.Repeat(" ", maxLabel-utf8.RuneCountInString(label))
		bar := renderBarRun(v/scale*float64(width), width)
		lines[i] = fmt.Sprintf("%s%s │ %s %s", label, pad, bar, formatValue(v))
	}
	return strings.Join(lines, "\n")
}

func renderBarRun(length float64, maxWidth int) string {
	if length < 0 {
		length = 0
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
