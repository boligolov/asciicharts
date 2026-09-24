package asciicharts

// Bars: hbar, vbar and the histogram's bars (spec/principles.md §4.4–§4.6, §5.3–§5.4).

import (
	"strconv"
	"strings"
)

func barsMatrix(in *input) ([]string, []string, [][]float64, error) {
	ss := in.series
	if len(ss) == 0 {
		return nil, nil, nil, errorf("series must contain at least one entry")
	}
	n := len(ss[0].values)
	if n == 0 {
		return nil, nil, nil, errorf("series must contain at least one value")
	}
	for i, s := range ss {
		if len(s.values) != n {
			return nil, nil, nil, errorf("all series must have the same number of values (series 0 has %d, "+
				"series %d has %d)", n, i, len(s.values))
		}
	}
	labels := in.labels
	if len(labels) > 0 && len(labels) != n {
		return nil, nil, nil, errorf("labels length (%d) must match each series' values length (%d)", len(labels), n)
	}
	if len(labels) == 0 {
		labels = make([]string, n)
		for i := range labels {
			labels[i] = strconv.Itoa(i + 1)
		}
	}
	names := make([]string, len(ss))
	matrix := make([][]float64, len(ss))
	for i, s := range ss {
		names[i] = seriesLabel(s, i)
		matrix[i] = s.values
	}
	return labels, names, matrix, nil
}

func barFillRamp(style string) ramp {
	switch style {
	case "halftone":
		return halftoneFills
	case "ascii":
		return asciiFills
	}
	return nil
}

// allocateProportional splits total units in proportion to values by the largest-remainder method;
// with keepNonzero every non-zero value keeps at least one unit while there is one to spare.
func allocateProportional(values []float64, totalSum float64, total int, keepNonzero bool) []int {
	n := len(values)
	result := make([]int, n)
	if keepNonzero && totalSum > 0 {
		total = maxInt(total, 1)
	}
	if totalSum <= 0 || total <= 0 {
		return result
	}
	fracs := make([]float64, n)
	allocated := 0
	for i, v := range values {
		exact := v / totalSum * float64(total)
		result[i] = int(exact)
		fracs[i] = exact - float64(result[i])
		allocated += result[i]
	}
	remainder := total - allocated
	order := stableOrderByDescending(fracs)
	for i := 0; i < minInt(remainder, n); i++ {
		result[order[i]]++
	}
	if keepNonzero {
		for i, v := range values {
			if v > 0 && result[i] == 0 {
				donor := 0
				for j := 1; j < n; j++ {
					if result[j] > result[donor] {
						donor = j
					}
				}
				if result[donor] <= 1 {
					break
				}
				result[donor]--
				result[i] = 1
			}
		}
	}
	return result
}

// stackExtents is the largest positive and negative (magnitude) column totals.
func stackExtents(matrix [][]float64) (float64, float64) {
	maxPos, maxNeg := 0.0, 0.0
	if len(matrix) == 0 {
		return 0, 0
	}
	for c := range matrix[0] {
		pos, neg := 0.0, 0.0
		for _, row := range matrix {
			v := row[c]
			if v > 0 {
				pos += v
			} else {
				neg -= v
			}
		}
		maxPos, maxNeg = pyMax(maxPos, pos), pyMax(maxNeg, neg)
	}
	return maxPos, maxNeg
}

func splitRows(maxPos, maxNeg float64, total int) int {
	if maxPos <= 0 {
		return 0
	}
	if maxNeg <= 0 || total < 2 {
		return total
	}
	return clamp(round(maxPos/(maxPos+maxNeg)*float64(total)), 1, total-1)
}

func splitStack(values []float64, maxPos, maxNeg float64, upCap, downCap int, keepNonzero bool) ([]int, []int) {
	pos := make([]float64, len(values))
	neg := make([]float64, len(values))
	posSum, negSum := 0.0, 0.0
	for i, v := range values {
		if v > 0 {
			pos[i] = v
		}
		if v < 0 {
			neg[i] = -v
		}
	}
	for _, v := range values {
		if v > 0 {
			posSum += v
		} else if v < 0 {
			negSum -= v
		}
	}
	up := make([]int, len(values))
	down := make([]int, len(values))
	if maxPos > 0 {
		up = allocateProportional(pos, posSum, round(posSum/maxPos*float64(upCap)), keepNonzero)
	}
	if maxNeg > 0 {
		down = allocateProportional(neg, negSum, round(negSum/maxNeg*float64(downCap)), keepNonzero)
	}
	return up, down
}

func renderBar(in *input) (string, error) {
	labels, names, matrix, err := barsMatrix(in)
	if err != nil {
		return "", err
	}
	w := in.width
	if w <= 0 {
		w = 40
	}
	height := in.height
	if height <= 0 {
		height = 10
	}
	r := barFillRamp(in.style)
	fine := in.style == "fine"
	track := in.style == "" || in.style == "solid" || in.style == "fine" || in.style == "ascii"
	asciiStyle := in.style == "ascii"
	if in.chartType == "vbar" {
		vw := in.width
		if vw == 0 {
			vw = 60
		}
		return renderVbar(labels, names, matrix, vw, height, in.stacked, in.color, r, fine, track, asciiStyle), nil
	}
	if len(names) == 1 {
		return renderHorizontalBars(labels, matrix[0], w, r, fine, track, asciiStyle), nil
	}
	if in.stacked {
		return renderHbarStacked(labels, names, matrix, w, in.color, r), nil
	}
	return renderHbarGrouped(labels, names, matrix, w, in.color, r, fine, track, asciiStyle), nil
}

func renderVbar(labels, names []string, matrix [][]float64, w, height int, stacked, colorOn bool, r ramp,
	fine, track, asciiStyle bool) string {
	numCat, numSeries := len(labels), len(matrix)
	gap := 1
	barsPerGroup := numSeries
	if stacked {
		barsPerGroup = 1
	}
	barWidth := 1
	if w > 0 {
		avail := w - (numCat-1)*gap
		if avail > 0 {
			bw := avail / (numCat * barsPerGroup)
			if bw > 1 {
				barWidth = bw
			}
		}
	}
	maxLabelW := 0
	for _, l := range labels {
		maxLabelW = maxInt(maxLabelW, width(l))
	}
	groupW := maxInt(barsPerGroup*barWidth, maxLabelW)
	barsOffset := (groupW - barsPerGroup*barWidth) / 2
	totalW := maxInt(numCat*groupW+(numCat-1)*gap, 1)
	g := newGrid(totalW, height)

	maxPos, maxNeg := stackExtents(matrix)
	column := func(c int) []float64 {
		values := make([]float64, numSeries)
		for s := 0; s < numSeries; s++ {
			values[s] = matrix[s][c]
		}
		return values
	}
	switch {
	case stacked && maxNeg == 0:
		maxSum := 0.0
		for c := 0; c < numCat; c++ {
			maxSum = pyMax(maxSum, sum(column(c)))
		}
		if maxSum == 0 {
			maxSum = 1
		}
		segRamp := r
		if segRamp == nil {
			segRamp = fills
		}
		for c := 0; c < numCat; c++ {
			colStart := c*(groupW+gap) + barsOffset
			values := column(c)
			colSum := sum(values)
			totalRows := round(colSum / maxSum * float64(height))
			cursor := 0
			for s, segRows := range allocateProportional(values, colSum, totalRows, true) {
				ch := segRamp[s%len(segRamp)]
				for rr := 0; rr < segRows; rr++ {
					row := height - 1 - cursor - rr
					if row < 0 || row >= height {
						continue
					}
					for x := 0; x < barWidth; x++ {
						g.ch[row][colStart+x] = ch
						g.color[row][colStart+x] = colorOf(s, colorOn)
					}
				}
				cursor += segRows
			}
		}
	case stacked:
		// positives stack up from a zero baseline, negatives down from it; the baseline is a row of
		// its own, owned by no bar (when there are 3+ rows)
		axis := height >= 3
		plot := height
		if axis {
			plot = height - 1
		}
		upCap := splitRows(maxPos, maxNeg, plot)
		below := upCap
		if axis {
			below = upCap + 1
		}
		segRamp := r
		if segRamp == nil {
			segRamp = fills
		}
		for c := 0; c < numCat; c++ {
			colStart := c*(groupW+gap) + barsOffset
			up, down := splitStack(column(c), maxPos, maxNeg, upCap, plot-upCap, true)
			for side, rowsBySeries := range [][]int{up, down} {
				cursor := 0
				for s, segRows := range rowsBySeries {
					ch := segRamp[s%len(segRamp)]
					for rr := 0; rr < segRows; rr++ {
						row := upCap - 1 - cursor - rr
						if side == 1 {
							row = below + cursor + rr
						}
						if row < 0 || row >= height {
							continue
						}
						for x := 0; x < barWidth; x++ {
							g.ch[row][colStart+x] = ch
							g.color[row][colStart+x] = colorOf(s, colorOn)
						}
					}
					cursor += segRows
				}
			}
		}
		if axis {
			for x := 0; x < totalW; x++ {
				g.ch[upCap][x] = "-"
			}
		}
	default:
		minVal, maxVal := 0.0, 0.0
		for s := 0; s < numSeries; s++ {
			for c := 0; c < numCat; c++ {
				minVal = pyMin(minVal, matrix[s][c])
				maxVal = pyMax(maxVal, matrix[s][c])
			}
		}
		if maxVal == minVal {
			maxVal = minVal + 1
		}
		diverging := minVal < 0
		zeroRow := clamp(yPixel(0, minVal, maxVal, height), 0, height-1)
		if diverging && height >= 3 {
			if maxVal > 0 {
				zeroRow = maxInt(zeroRow, 1)
			}
			zeroRow = minInt(zeroRow, height-2)
		}
		// divergingRows: the rows of a diverging bar, strictly above or below the baseline, at least one.
		divergingRows := func(v float64) (int, int) {
			if v == 0 {
				return 0, 0
			}
			row := yPixel(v, minVal, maxVal, height)
			if v > 0 {
				if zeroRow == 0 {
					return zeroRow, zeroRow + 1
				}
				top := minInt(row, zeroRow-1)
				return maxInt(top, 0), zeroRow
			}
			if zeroRow == height-1 {
				return zeroRow, zeroRow + 1
			}
			bottom := maxInt(row, zeroRow+1)
			return zeroRow + 1, minInt(bottom, height-1) + 1
		}
		effective := r
		if effective == nil && numSeries > 1 {
			effective = fills
		}
		for c := 0; c < numCat; c++ {
			for s := 0; s < numSeries; s++ {
				colStart := c*(groupW+gap) + barsOffset + s*barWidth
				v := matrix[s][c]
				color := colorOf(s, colorOn)
				if effective != nil || !fine {
					ch := "█"
					if effective != nil {
						ch = effective[s%len(effective)]
					}
					if !diverging {
						rows := round(v / maxVal * float64(height))
						if v > 0 && rows == 0 {
							rows = 1
						}
						filled := minInt(rows, height)
						for x := 0; x < barWidth; x++ {
							col := colStart + x
							for rr := 0; rr < filled; rr++ {
								g.ch[height-1-rr][col] = ch
								g.color[height-1-rr][col] = color
							}
							if track {
								p := trackGlyph(ch, asciiStyle)
								for rr := maxInt(filled, 0); rr < height; rr++ {
									g.ch[height-1-rr][col] = p
								}
							}
						}
					} else {
						a, b := divergingRows(v)
						for x := 0; x < barWidth; x++ {
							for rr := a; rr < b; rr++ {
								g.ch[rr][colStart+x] = ch
								g.color[rr][colStart+x] = color
							}
						}
					}
					continue
				}
				if !diverging {
					eighths := round(v / maxVal * float64(height) * 8)
					full, frac := floorDiv(eighths, 8), eighths-8*floorDiv(eighths, 8)
					for x := 0; x < barWidth; x++ {
						col := colStart + x
						for rr := 0; rr < minInt(full, height); rr++ {
							g.ch[height-1-rr][col] = "█"
							g.color[height-1-rr][col] = color
						}
						top := minInt(full, height)
						if frac > 0 && full < height {
							g.ch[height-1-full][col] = eighthsUp[frac]
							g.color[height-1-full][col] = color
							top = full + 1
						}
						if track {
							p := trackGlyph("█", asciiStyle)
							for rr := maxInt(top, 0); rr < height; rr++ {
								g.ch[height-1-rr][col] = p
							}
						}
					}
				} else {
					a, b := divergingRows(v)
					for x := 0; x < barWidth; x++ {
						for rr := a; rr < b; rr++ {
							g.ch[rr][colStart+x] = "█"
							g.color[rr][colStart+x] = color
						}
					}
				}
			}
		}
		if diverging {
			for x := 0; x < totalW; x++ {
				if g.ch[zeroRow][x] == " " {
					g.ch[zeroRow][x] = "-"
				}
			}
		}
	}

	out := make([]string, 0, height+1)
	for y := 0; y < height; y++ {
		out = append(out, g.row(y, colorOn))
	}
	labelRow := make([]string, totalW)
	for i := range labelRow {
		labelRow[i] = " "
	}
	for c, lbl := range labels {
		start := c*(groupW+gap) + (groupW-width(lbl))/2
		for j, ch := range cells(lbl) {
			if start+j >= 0 && start+j < totalW {
				labelRow[start+j] = ch
			}
		}
	}
	out = append(out, strings.TrimRight(strings.Join(labelRow, ""), " "))
	body := strings.Join(out, "\n")
	if numSeries > 1 {
		legendRamp := r
		if legendRamp == nil {
			legendRamp = fills
		}
		body += "\n\n" + namedLegend(names, colorOn, legendRamp)
	}
	return body
}

// divergingScale is the zero-axis column and the cells per data unit of a diverging row.
func divergingScale(minVal, maxVal float64, w int) (int, float64) {
	unit := 0.0
	if w > 1 {
		unit = float64(w-1) / (maxVal - minVal)
	}
	return clamp(round(-minVal*unit), 0, maxInt(w-1, 0)), unit
}

func divergingBarRun(v float64, zeroCol int, unit float64, w int, fill, axis string) string {
	if w <= 0 {
		return ""
	}
	row := make([]string, w)
	for i := range row {
		row[i] = " "
	}
	row[zeroCol] = axis
	n := round(absFloat(v) * unit)
	if v != 0 && n == 0 {
		n = 1
	}
	if v > 0 {
		for i := zeroCol + 1; i < minInt(w, zeroCol+1+n); i++ {
			row[i] = fill
		}
	} else if v < 0 {
		for i := maxInt(0, zeroCol-n); i < zeroCol; i++ {
			row[i] = fill
		}
	}
	return strings.Join(row, "")
}

func axisGlyph(r ramp) string {
	if isASCIIRamp(r) {
		return "+"
	}
	return "¦"
}

func renderBarRun(length float64, maxWidth int, fill string, fine, track, asciiStyle bool) string {
	length = pyMax(length, 0)
	if fill != "" || !fine {
		ch := fill
		if ch == "" {
			ch = "█"
		}
		full := minInt(round(length), maxWidth)
		if length > 0 && full == 0 {
			full = 1
		}
		p := " "
		if track {
			p = trackGlyph(ch, asciiStyle)
		}
		return repeat(ch, full) + repeat(p, maxWidth-full)
	}
	full := minInt(int(length), maxWidth)
	frac := length - float64(full)
	s := repeat(eighthsLeft[8], full)
	if full < maxWidth {
		idx := int(frac * 8)
		if idx > 0 {
			s += eighthsLeft[idx]
			full++
		}
	}
	p := " "
	if track {
		p = trackGlyph("█", asciiStyle)
	}
	return s + repeat(p, maxWidth-full)
}

func renderHbarGrouped(labels, names []string, matrix [][]float64, w int, colorOn bool, r ramp,
	fine, track, asciiStyle bool) string {
	minVal, maxVal := 0.0, 0.0
	for _, row := range matrix {
		for _, v := range row {
			minVal, maxVal = pyMin(minVal, v), pyMax(maxVal, v)
		}
	}
	if maxVal == minVal {
		maxVal = minVal + 1
	}
	diverging := minVal < 0
	zeroCol, unit := 0, 0.0
	if diverging {
		zeroCol, unit = divergingScale(minVal, maxVal, w)
	}
	maxNameW := 0
	for _, n := range names {
		maxNameW = maxInt(maxNameW, width(n))
	}
	blocks := make([]string, len(labels))
	for c, lbl := range labels {
		lines := []string{lbl}
		for s, name := range names {
			v := matrix[s][c]
			fill := ""
			if r != nil {
				fill = r[s%len(r)]
			}
			var bar string
			if diverging {
				f := fill
				if f == "" {
					f = "█"
				}
				bar = divergingBarRun(v, zeroCol, unit, w, f, axisGlyph(r))
			} else {
				bar = renderBarRun(v/maxVal*float64(w), w, fill, fine, track, asciiStyle)
			}
			lines = append(lines, "  "+pad(name, maxNameW)+" "+sep(r)+" "+colorize(bar, colorOf(s, colorOn), colorOn)+" "+fmtValue(v))
		}
		blocks[c] = strings.Join(lines, "\n")
	}
	return strings.Join(blocks, "\n\n")
}

func renderHbarStackedDiverging(labels, names []string, matrix [][]float64, w int, colorOn bool, r ramp,
	maxPos, maxNeg float64) string {
	// the zero axis is a column of its own, owned by no bar (when there are 3+ columns)
	axis := ""
	if w >= 3 {
		axis = axisGlyph(r)
	}
	cols := w - len([]rune(axis))
	posCols := splitRows(maxPos, maxNeg, cols)
	negCols := cols - posCols
	segRamp := r
	if segRamp == nil {
		segRamp = fills
	}
	maxLabelW := 0
	for _, l := range labels {
		maxLabelW = maxInt(maxLabelW, width(l))
	}
	seg := func(s, n int) string {
		return colorize(repeat(segRamp[s%len(segRamp)], n), colorOf(s, colorOn), colorOn)
	}
	lines := make([]string, len(labels))
	for c, lbl := range labels {
		values := make([]float64, len(names))
		for s := range names {
			values[s] = matrix[s][c]
		}
		net := sum(values)
		up, down := splitStack(values, maxPos, maxNeg, posCols, negCols, true)
		var b strings.Builder
		b.WriteString(repeat(" ", negCols-sumInts(down)))
		for s := len(down) - 1; s >= 0; s-- {
			b.WriteString(seg(s, down[s]))
		}
		b.WriteString(axis)
		for s, n := range up {
			b.WriteString(seg(s, n))
		}
		b.WriteString(repeat(" ", posCols-sumInts(up)))
		lines[c] = pad(lbl, maxLabelW) + " " + sep(r) + " " + b.String() + " " + fmtValue(net)
	}
	legendRamp := r
	if legendRamp == nil {
		legendRamp = fills
	}
	return strings.Join(lines, "\n") + "\n\n" + namedLegend(names, colorOn, legendRamp)
}

func renderHbarStacked(labels, names []string, matrix [][]float64, w int, colorOn bool, r ramp) string {
	maxPos, maxNeg := stackExtents(matrix)
	if maxNeg > 0 {
		return renderHbarStackedDiverging(labels, names, matrix, w, colorOn, r, maxPos, maxNeg)
	}
	column := func(c int) []float64 {
		values := make([]float64, len(names))
		for s := range names {
			values[s] = matrix[s][c]
		}
		return values
	}
	maxSum := 0.0
	for c := range labels {
		maxSum = pyMax(maxSum, sum(column(c)))
	}
	if maxSum == 0 {
		maxSum = 1
	}
	maxLabelW := 0
	for _, l := range labels {
		maxLabelW = maxInt(maxLabelW, width(l))
	}
	segRamp := r
	if segRamp == nil {
		segRamp = fills
	}
	lines := make([]string, len(labels))
	for c, lbl := range labels {
		values := column(c)
		colSum := sum(values)
		totalWidth := round(colSum / maxSum * float64(w))
		var b strings.Builder
		used := 0
		for s, n := range allocateProportional(values, colSum, totalWidth, true) {
			b.WriteString(colorize(repeat(segRamp[s%len(segRamp)], n), colorOf(s, colorOn), colorOn))
			used += n
		}
		lines[c] = pad(lbl, maxLabelW) + " " + sep(r) + " " + b.String() + repeat(" ", w-used) + " " + fmtValue(colSum)
	}
	legendRamp := r
	if legendRamp == nil {
		legendRamp = fills
	}
	return strings.Join(lines, "\n") + "\n\n" + namedLegend(names, colorOn, legendRamp)
}

func renderHorizontalBars(labels []string, values []float64, w int, r ramp, fine, track, asciiStyle bool) string {
	if w <= 0 {
		w = 40
	}
	maxLabel := 0
	for _, l := range labels {
		maxLabel = maxInt(maxLabel, width(l))
	}
	fill := ""
	if r != nil {
		fill = r[0]
	}
	minVal, maxVal := 0.0, 0.0
	for _, v := range values {
		minVal, maxVal = pyMin(minVal, v), pyMax(maxVal, v)
	}
	if maxVal == minVal {
		maxVal = minVal + 1
	}
	lines := make([]string, len(values))
	if minVal < 0 {
		zc, unit := divergingScale(minVal, maxVal, w)
		for i, v := range values {
			f := fill
			if f == "" {
				f = "█"
			}
			bar := divergingBarRun(v, zc, unit, w, f, axisGlyph(r))
			lines[i] = labels[i] + repeat(" ", maxLabel-width(labels[i])) + " " + sep(r) + " " + bar + " " + fmtValue(v)
		}
		return strings.Join(lines, "\n")
	}
	for i, v := range values {
		lines[i] = labels[i] + repeat(" ", maxLabel-width(labels[i])) + " " + sep(r) + " " +
			renderBarRun(v/maxVal*float64(w), w, fill, fine, track, asciiStyle) + " " + fmtValue(v)
	}
	return strings.Join(lines, "\n")
}

func absFloat(x float64) float64 {
	if x < 0 {
		return -x
	}
	return x
}
