package asciicharts

// Sparkline, line, area, scatter, dual_axis and dotplot (spec/principles.md §4.7–§4.8, §5.5–§5.6, §7).

import (
	"strings"
)

func renderSparkline(in *input) (string, error) {
	lines := make([]string, 0, len(in.series))
	for i, s := range in.series {
		vals := s.values
		if len(vals) == 0 {
			return "", errorf("series %d %s must contain at least one value", i, quote(s.name))
		}
		lo, hi := vals[0], vals[0]
		for _, v := range vals[1:] {
			lo, hi = pyMin(lo, v), pyMax(hi, v)
		}
		span := hi - lo
		var b strings.Builder
		for _, v := range vals {
			idx := 3 // a flat series is a flat line at half height
			if span > 0 {
				idx = level((v-lo)/span, len(sparkTicks))
			}
			b.WriteString(sparkTicks[idx])
		}
		spark := colorize(b.String(), seriesColor(i), in.color)
		if s.name != "" {
			lines = append(lines, s.name+" "+spark)
		} else {
			lines = append(lines, spark)
		}
	}
	return strings.Join(lines, "\n"), nil
}

func lineLegend(ss []series, showPoints, colorOn, asciiStyle bool) string {
	names := make([]string, len(ss))
	for i, s := range ss {
		names[i] = seriesLabel(s, i)
	}
	switch {
	case showPoints && asciiStyle:
		return namedLegend(names, colorOn, asciiMarkers)
	case showPoints:
		return namedLegend(names, colorOn, markers)
	case asciiStyle:
		return namedLegend(names, colorOn, asciiFills)
	}
	return namedLegend(names, colorOn, fills)
}

func renderLine(in *input) (string, error) {
	height := in.height
	if height == 0 {
		height = 10
	}
	w := in.width
	if w == 0 {
		w = 60
	}
	ss := in.series
	for i, s := range ss {
		if len(s.values) < 2 {
			return "", errorf("series %d %s must contain at least two values", i, quote(s.name))
		}
	}
	lo, hi := seriesMinMax(ss)
	var refs []float64
	if in.threshold != nil {
		refs = append(refs, *in.threshold)
	}
	for _, t := range in.thresholds {
		refs = append(refs, t.value)
	}
	if len(refs) > 0 {
		newLo, newHi := lo, hi
		for _, v := range refs {
			newLo, newHi = pyMin(newLo, v), pyMax(newHi, v)
		}
		lo, hi = newLo, newHi
	}
	lo, hi = zeroOnRow(lo, hi, height)
	colorOn := in.color

	c := newCanvas(w, height)
	dotted := in.style == "dotted"
	asciiStyle := in.style == "ascii"
	multi := len(ss) > 1
	for si, s := range ss {
		color := colorOf(si, colorOn)
		lineChar := ""
		switch {
		case in.showPoints && asciiStyle:
			lineChar = "."
		case in.showPoints:
			lineChar = "·"
		case asciiStyle:
			lineChar = asciiFills[si%len(asciiFills)]
		case multi:
			lineChar = fills[si%len(fills)]
		case dotted:
			lineChar = "+"
		}
		n := len(s.values)
		px, py, havePrev := 0, 0, false
		for i, v := range s.values {
			x, y := xPixel(i, n, w), yPixel(v, lo, hi, height)
			if havePrev {
				c.line(px, py, x, y, lineChar, color, dotted)
			} else {
				c.setDot(x, y, lineChar, color)
			}
			px, py, havePrev = x, y, true
		}
	}

	tcolor := -1
	if colorOn {
		tcolor = thresholdColor
	}
	for _, ref := range refs {
		row := yPixel(ref, lo, hi, height)
		for x := 0; x < c.width; x++ {
			if x%2 == 0 && c.char[row][x] == "" { // behind the data
				c.setMarker(x, row, "-", tcolor)
			}
		}
	}
	notes := map[int][]string{}
	for _, t := range in.thresholds {
		row := yPixel(t.value, lo, hi, height)
		note := fmtValue(t.value)
		if t.label != "" {
			note = t.label + ": " + note
		}
		notes[row] = append(notes[row], note)
	}

	if in.showPoints {
		custom := firstRune(in.pointChar)
		for si, s := range ss {
			color := colorOf(si, colorOn)
			set := markers
			if asciiStyle {
				set = asciiMarkers
			}
			marker := custom
			if marker == "" {
				marker = set[si%len(set)]
			}
			n := len(s.values)
			for i, v := range s.values {
				c.setMarker(xPixel(i, n, w), yPixel(v, lo, hi, height), marker, color)
			}
		}
	}

	axisLabels, axisW := leftAxisLabels(lo, hi, height)
	rows := c.render(colorOn)
	tick := "┤"
	if asciiStyle {
		tick = "+"
	}
	out := make([]string, len(rows))
	for r, l := range rows {
		out[r] = padLeft(axisLabels[r], axisW) + " " + tick + l
		if ns, ok := notes[r]; ok {
			out[r] += "  " + colorize(strings.Join(ns, ", "), tcolor, colorOn)
		}
	}
	body := strings.Join(out, "\n")
	if x := xAxisLabels(in.labels, seriesMaxLen(ss), w, axisW+2); x != "" {
		body += "\n" + x
	}
	if multi {
		body += "\n\n" + lineLegend(ss, in.showPoints, colorOn, asciiStyle)
	}
	if in.threshold != nil {
		note := "- - threshold: " + fmtValue(*in.threshold)
		if len(ss) > 1 {
			body += "   " + note
		} else {
			body += "\n\n" + note
		}
	}
	return body, nil
}

func areaFillRamp(style string) ramp {
	switch style {
	case "halftone":
		return halftoneFills
	case "ascii":
		return areaASCII
	}
	return fills
}

// interpAt is the series' value at column x of a plot w columns wide, by linear interpolation.
func interpAt(values []float64, x, w int) float64 {
	n := len(values)
	if n == 1 || w <= 1 {
		return values[0]
	}
	pos := float64(x*(n-1)) / float64(w-1)
	i0 := int(pos)
	if i0 >= n-1 {
		return values[n-1]
	}
	frac := pos - float64(i0)
	return values[i0]*(1-frac) + values[i0+1]*frac
}

func renderArea(in *input) (string, error) {
	ss := in.series
	if len(ss) == 0 {
		return "", errorf("series must contain at least one entry")
	}
	n := len(ss[0].values)
	for i, s := range ss {
		if len(s.values) < 2 {
			return "", errorf("series %d %s must contain at least two values", i, quote(s.name))
		}
		if len(s.values) != n {
			return "", errorf("all series must have the same number of values (series 0 has %d, "+
				"series %d has %d)", n, i, len(s.values))
		}
	}
	height := in.height
	if height == 0 {
		height = 10
	}
	w := in.width
	if w == 0 {
		w = 60
	}
	colorOn := in.color
	r := areaFillRamp(in.style)
	numSeries := len(ss)
	names := make([]string, numSeries)
	for i, s := range ss {
		names[i] = seriesLabel(s, i)
	}
	g := newGrid(w, height)
	stackMatrix := make([][]float64, numSeries)
	for si, s := range ss {
		stackMatrix[si] = make([]float64, w)
		for x := 0; x < w; x++ {
			stackMatrix[si][x] = interpAt(s.values, x, w)
		}
	}
	maxPos, maxNeg := stackExtents(stackMatrix)
	column := func(x int) []float64 {
		values := make([]float64, numSeries)
		for si, s := range ss {
			values[si] = interpAt(s.values, x, w)
		}
		return values
	}

	var minVal, maxVal float64
	switch {
	case in.stacked && maxNeg == 0:
		minVal, maxVal = 0, 0
		for x := 0; x < w; x++ {
			maxVal = pyMax(maxVal, sum(column(x)))
		}
		if maxVal == 0 {
			maxVal = 1
		}
		for x := 0; x < w; x++ {
			values := column(x)
			colSum := sum(values)
			totalRows := round(colSum / maxVal * float64(height))
			cursor := 0
			for si, segRows := range allocateProportional(values, colSum, totalRows, false) {
				ch := r[si%len(r)]
				color := colorOf(si, colorOn)
				for rr := 0; rr < segRows; rr++ {
					row := height - 1 - cursor - rr
					if row >= 0 && row < height {
						g.ch[row][x] = ch
						g.color[row][x] = color
					}
				}
				cursor += segRows
			}
		}
	case in.stacked:
		minVal, maxVal = zeroOnRow(-maxNeg, maxPos, height)
		zeroRow := clamp(yPixel(0, minVal, maxVal, height), 0, height-1)
		if maxNeg > 0 && zeroRow == height-1 && height > 1 {
			zeroRow = height - 2
		}
		for x := 0; x < w; x++ {
			values := make([]float64, numSeries)
			for si := range ss {
				values[si] = stackMatrix[si][x]
			}
			up, down := splitStack(values, maxPos, maxNeg, zeroRow+1, height-1-zeroRow, false)
			for side, rowsBySeries := range [][]int{up, down} {
				cursor := 0
				for si, segRows := range rowsBySeries {
					ch := r[si%len(r)]
					color := colorOf(si, colorOn)
					for rr := 0; rr < segRows; rr++ {
						row := zeroRow - cursor - rr
						if side == 1 {
							row = zeroRow + 1 + cursor + rr
						}
						if row >= 0 && row < height {
							g.ch[row][x] = ch
							g.color[row][x] = color
						}
					}
					cursor += segRows
				}
			}
		}
	default:
		minVal, maxVal = seriesMinMax(ss)
		minVal, maxVal = pyMin(minVal, 0), pyMax(maxVal, 0)
		if maxVal == minVal {
			maxVal = minVal + 1
		}
		minVal, maxVal = zeroOnRow(minVal, maxVal, height)
		zeroRow := yPixel(0, minVal, maxVal, height)
		for si := numSeries - 1; si >= 0; si-- { // later series first, so the first ends on top
			ch := r[si%len(r)]
			color := colorOf(si, colorOn)
			for x := 0; x < w; x++ {
				row := yPixel(interpAt(ss[si].values, x, w), minVal, maxVal, height)
				lo, hi := row, zeroRow
				if lo > hi {
					lo, hi = hi, lo
				}
				for rr := lo; rr <= hi; rr++ {
					g.ch[rr][x] = ch
					g.color[rr][x] = color
				}
			}
		}
	}

	axisLabels, axisW := leftAxisLabels(minVal, maxVal, height)
	tick := "┤"
	if isASCIIRamp(r) {
		tick = "+"
	}
	lines := make([]string, height)
	for y := 0; y < height; y++ {
		lines[y] = padLeft(axisLabels[y], axisW) + " " + tick + g.row(y, colorOn)
	}
	body := strings.Join(lines, "\n")
	if x := xAxisLabels(in.labels, seriesMaxLen(ss), w, axisW+2); x != "" {
		body += "\n" + x
	}
	if numSeries > 1 {
		body += "\n\n" + namedLegend(names, colorOn, r)
	}
	return body, nil
}

func renderDotplot(in *input) (string, error) {
	labels, names, matrix, err := barsMatrix(in)
	if err != nil {
		return "", err
	}
	w := in.width
	if w == 0 {
		w = 40
	}
	colorOn := in.color
	numSeries := len(names)
	dataMin, dataMax := matrix[0][0], matrix[0][0]
	for _, row := range matrix {
		for _, v := range row {
			dataMin, dataMax = pyMin(dataMin, v), pyMax(dataMax, v)
		}
	}
	minVal, maxVal := scaleRange(dataMin, dataMax)
	maxLabel := 0
	for _, l := range labels {
		maxLabel = maxInt(maxLabel, width(l))
	}
	lines := make([]string, len(labels))
	overlap := false
	for c, lbl := range labels {
		row := make([]string, w)
		crow := make([]int, w)
		owner := make([]int, w)
		for i := range row {
			row[i], crow[i], owner[i] = "·", -1, -1
		}
		for s := 0; s < numSeries; s++ {
			col := clamp(round((matrix[s][c]-minVal)/(maxVal-minVal)*float64(w-1)), 0, w-1)
			if owner[col] >= 0 {
				row[col], crow[col] = overlapMarker, -1
				overlap = true
				continue
			}
			owner[col] = s
			row[col] = markers[s%len(markers)]
			if colorOn {
				crow[col] = seriesColor(s)
			}
		}
		var b strings.Builder
		for i, ch := range row {
			b.WriteString(colorize(ch, crow[i], colorOn))
		}
		line := pad(lbl, maxLabel) + " │ " + b.String()
		if numSeries == 1 {
			line += " " + fmtValue(matrix[0][c])
		}
		lines[c] = line
	}
	body := strings.Join(lines, "\n") + "\nvalue axis: [" + fmtValue(dataMin) + ", " + fmtValue(dataMax) + "]"
	if numSeries > 1 {
		body += "\n" + namedLegend(names, colorOn, markers)
		if overlap {
			body += "   " + overlapNote
		}
	}
	return body, nil
}

func renderScatter(in *input) (string, error) {
	w := in.width
	if w == 0 {
		w = 60
	}
	height := in.height
	if height == 0 {
		height = 15
	}
	ss := in.series
	var pts [][2]float64
	for i, s := range ss {
		if len(s.points) == 0 {
			return "", errorf("series %d %s must contain at least one point", i, quote(s.name))
		}
		pts = append(pts, s.points...)
	}
	dxMin, dxMax, dyMin, dyMax := pts[0][0], pts[0][0], pts[0][1], pts[0][1]
	for _, p := range pts[1:] {
		dxMin, dxMax = pyMin(dxMin, p[0]), pyMax(dxMax, p[0])
		dyMin, dyMax = pyMin(dyMin, p[1]), pyMax(dyMax, p[1])
	}
	minX, maxX := scaleRange(dxMin, dxMax)
	minY, maxY := scaleRange(dyMin, dyMax)
	colorOn := in.color
	c := newCanvas(w, height)
	type cell struct{ x, y int }
	owner := map[cell]int{}
	overlap := false
	for si, s := range ss {
		color := colorOf(si, colorOn)
		for _, p := range s.points {
			px := round((p[0] - minX) / (maxX - minX) * float64(w-1))
			py := height - 1 - round((p[1]-minY)/(maxY-minY)*float64(height-1))
			key := cell{px, py}
			if o, seen := owner[key]; seen && o != si {
				c.char[py][px], c.color[py][px] = overlapMarker, -1
				overlap = true
				continue
			} else if !seen {
				owner[key] = si
			}
			if c.char[py][px] != overlapMarker {
				c.setMarker(px, py, markers[si%len(markers)], color)
			}
		}
	}
	body := strings.Join(c.render(colorOn), "\n")
	body += "\nx: [" + fmtValue(dxMin) + ", " + fmtValue(dxMax) + "]  y: [" + fmtValue(dyMin) + ", " + fmtValue(dyMax) + "]"
	if len(ss) > 1 {
		names := make([]string, len(ss))
		for i, s := range ss {
			names[i] = seriesLabel(s, i)
		}
		body += "\n" + namedLegend(names, colorOn, markers)
		if overlap {
			body += "   " + overlapNote
		}
	}
	return body, nil
}

func renderDualAxis(in *input) (string, error) {
	ss := in.series
	if len(ss) != 2 {
		return "", errorf("dual_axis expects exactly two series, got %d", len(ss))
	}
	for i, s := range ss {
		if len(s.values) < 2 {
			return "", errorf("series %d %s must contain at least two values", i, quote(s.name))
		}
	}
	height := in.height
	if height == 0 {
		height = 10
	}
	w := in.width
	if w == 0 {
		w = 60
	}
	colorOn := in.color
	c := newCanvas(w, height)
	var mins, maxs [2]float64
	for si, s := range ss {
		lo, hi := seriesMinMax([]series{s})
		mins[si], maxs[si] = zeroOnRow(lo, hi, height)
		color := colorOf(si, colorOn)
		glyph := dualGlyphs[si]
		n := len(s.values)
		px, py, havePrev := 0, 0, false
		for i, v := range s.values {
			x, y := xPixel(i, n, w), yPixel(v, mins[si], maxs[si], height)
			if havePrev {
				c.line(px, py, x, y, glyph, color, false)
			} else {
				c.setDot(x, y, glyph, color)
			}
			px, py, havePrev = x, y, true
		}
	}
	left, leftW := leftAxisLabels(mins[0], maxs[0], height)
	right, rightW := leftAxisLabels(mins[1], maxs[1], height)
	rows := c.render(colorOn)
	out := make([]string, len(rows))
	for r, l := range rows {
		out[r] = padLeft(left[r], leftW) + " ┤" + l + "├ " + padRight(right[r], rightW)
	}
	n0, n1 := seriesLabel(ss[0], 0), seriesLabel(ss[1], 1)
	legend := "left:  " + colorize(dualGlyphs[0], seriesColor(0), colorOn) + " " + n0 + "\n" +
		"right: " + colorize(dualGlyphs[1], seriesColor(1), colorOn) + " " + n1
	return strings.Join(out, "\n") + "\n\n" + legend, nil
}
