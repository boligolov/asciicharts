package asciicharts

// Pie, histogram, heatmap and boxplot (docs/spec/principles.md §4.9–§4.12, §7).

import (
	"math"
	"sort"
	"strconv"
	"strings"
)

func renderPie(in *input) (string, error) {
	values := make([]float64, 0, len(in.series))
	names := make([]string, 0, len(in.series))
	total := 0.0
	for i, s := range in.series {
		v := sum(s.values)
		if v < 0 {
			return "", errorf("series %d %s: pie slice values must be non-negative", i, quote(s.name))
		}
		values = append(values, v)
		names = append(names, seriesLabel(s, i))
		total += v
	}
	if total <= 0 {
		return "", errorf("pie slice values must sum to more than zero")
	}
	w, h := in.width, in.height
	switch {
	case w <= 0 && h <= 0:
		w, h = 44, 22
	case w <= 0:
		w = h * 2
	case h <= 0:
		h = w / 2
	}
	h = maxInt(h, 1)

	cumulative := make([]float64, len(values))
	running := 0.0
	for i, v := range values {
		running += v
		cumulative[i] = running / total
	}
	colorOn := in.color
	cx, cy := float64(w)/2, float64(h)/2
	radius := pyMin(float64(w)/2, float64(h)/2*pieAspect)

	grid := make([][]int, h)
	type point struct{ x, y int }
	var inside []point // in row-major order, like the reference's dict
	frac := map[point]float64{}
	for y := 0; y < h; y++ {
		grid[y] = make([]int, w)
		for x := 0; x < w; x++ {
			grid[y][x] = -1
			dx := float64(x) + 0.5 - cx
			dy := (float64(y) + 0.5 - cy) * pieAspect
			if math.Hypot(dx, dy) > radius {
				continue
			}
			angle := math.Atan2(dx, -dy)
			if angle < 0 {
				angle += 2 * math.Pi
			}
			f := angle / (2 * math.Pi)
			sl := len(cumulative) - 1
			for i, cum := range cumulative {
				if f <= cum {
					sl = i
					break
				}
			}
			grid[y][x] = sl
			frac[point{x, y}] = f
			inside = append(inside, point{x, y})
		}
	}

	// A slice too thin to own a cell gets the inside cell nearest the middle of its angle, taken from
	// a slice with cells to spare.
	counts := map[int]int{}
	for _, row := range grid {
		for _, sl := range row {
			counts[sl]++
		}
	}
	for i, v := range values {
		if v <= 0 || counts[i] > 0 || len(inside) == 0 {
			continue
		}
		mid := pyMod1(cumulative[i] - v/total/2)
		best, found := point{}, false
		bestDist := 0.0
		for _, p := range inside {
			if counts[grid[p.y][p.x]] <= 1 {
				continue
			}
			d := math.Abs(frac[p] - mid)
			d = pyMin(d, 1-d)
			// the smallest (distance, y, x)
			if !found || d < bestDist || (d == bestDist && (p.y < best.y || (p.y == best.y && p.x < best.x))) {
				best, bestDist, found = p, d, true
			}
		}
		if found {
			counts[grid[best.y][best.x]]--
			grid[best.y][best.x] = i
			counts[i] = 1
		}
	}

	rows := make([]string, h)
	for y, row := range grid {
		var b strings.Builder
		for _, sl := range row {
			if sl < 0 {
				b.WriteString(" ")
			} else {
				b.WriteString(colorize(fills[sl%len(fills)], seriesColor(sl), colorOn))
			}
		}
		rows[y] = b.String()
	}
	legend := make([]string, len(values))
	for i, v := range values {
		legend[i] = legendSwatch(i, colorOn, fills) + " " + names[i] + ": " + fmtValue(v) +
			" (" + strconv.FormatFloat(v/total*100, 'f', 1, 64) + "%)"
	}
	return strings.Join(rows, "\n") + "\n\n" + strings.Join(legend, "\n"), nil
}

func renderHistogram(in *input) (string, error) {
	if len(in.series) != 1 {
		return "", errorf("histogram expects exactly one series, got %d", len(in.series))
	}
	values := in.series[0].values
	if len(values) == 0 {
		return "", errorf("series must contain at least one value")
	}
	bins := in.bins
	if bins <= 0 {
		bins = 10
	}
	lo, hi := values[0], values[0]
	for _, v := range values[1:] {
		lo, hi = pyMin(lo, v), pyMax(hi, v)
	}
	if hi == lo {
		hi = lo + 1
	}
	binWidth := (hi - lo) / float64(bins)
	counts := make([]float64, bins)
	for _, v := range values {
		counts[clamp(int((v-lo)/binWidth), 0, bins-1)]++
	}
	labels := make([]string, bins)
	for i := 0; i < bins; i++ {
		bLo := lo + float64(i)*binWidth
		labels[i] = fmtValue(bLo) + ".." + fmtValue(bLo+binWidth)
	}
	return renderHorizontalBars(labels, counts, in.width, barFillRamp(in.style), in.style == "fine", false, false), nil
}

func renderHeatmap(in *input) (string, error) {
	ss := in.series
	if len(ss) == 0 {
		return "", errorf("series must contain at least one row")
	}
	numCols := len(ss[0].values)
	if numCols == 0 {
		return "", errorf("each row must contain at least one value")
	}
	for i, s := range ss {
		if len(s.values) != numCols {
			return "", errorf("all rows must have the same number of values (row 0 has %d, "+
				"row %d has %d)", numCols, i, len(s.values))
		}
	}
	labels := in.labels
	if len(labels) > 0 && len(labels) != numCols {
		return "", errorf("labels length (%d) must match each row's values length (%d)", len(labels), numCols)
	}
	lo, hi := ss[0].values[0], ss[0].values[0]
	for _, s := range ss {
		for _, v := range s.values {
			lo, hi = pyMin(lo, v), pyMax(hi, v)
		}
	}
	dataLo, dataHi := lo, hi
	lo, hi = scaleRange(lo, hi)
	colorOn := in.color
	rowLabelW := 0
	for _, s := range ss {
		rowLabelW = maxInt(rowLabelW, width(s.name))
	}
	gw := in.width
	if gw == 0 {
		gw = 60
	}
	cellW := maxInt(heatCellWidth, (gw+1)/numCols-1)

	var out []string
	if len(labels) > 0 {
		var b strings.Builder
		b.WriteString(repeat(" ", rowLabelW+1))
		for _, c := range labels {
			b.WriteString(padCenter(c, cellW) + " ")
		}
		out = append(out, b.String())
	}
	for _, s := range ss {
		var b strings.Builder
		b.WriteString(pad(s.name, rowLabelW) + " ")
		for _, v := range s.values {
			norm := (v - lo) / (hi - lo)
			if colorOn {
				b.WriteString(colorize(repeat("█", cellW), heatRamp[level(norm, len(heatRamp))], true))
			} else {
				b.WriteString(repeat(shades[1+level(norm, len(shades)-1)], cellW)) // never blank
			}
			b.WriteString(" ")
		}
		out = append(out, b.String())
	}
	out = append(out, "", heatLegend(dataLo, dataHi, lo, hi, colorOn))
	return strings.Join(out, "\n"), nil
}

// heatLegend says what each shade stands for: the four equal buckets of the data's range (the color
// ramp and its range with color; the one shade and its value when all values are equal).
func heatLegend(dataLo, dataHi, lo, hi float64, colorOn bool) string {
	if dataLo == dataHi {
		norm := (dataLo - lo) / (hi - lo)
		swatch := shades[1+level(norm, len(shades)-1)]
		if colorOn {
			swatch = colorize("█", heatRamp[level(norm, len(heatRamp))], true)
		}
		return swatch + " " + fmtValue(dataLo)
	}
	if colorOn {
		var ramp strings.Builder
		for _, c := range heatRamp {
			ramp.WriteString(colorize("█", c, true))
		}
		return ramp.String() + " " + fmtValue(dataLo) + ".." + fmtValue(dataHi)
	}
	n := len(shades) - 1
	// inner edges rounded to 12 significant digits, like axis labels, to drop float noise
	edges := []float64{dataLo}
	for k := 1; k < n; k++ {
		edges = append(edges, roundSig12(dataLo+float64(k)/float64(n)*(dataHi-dataLo)))
	}
	edges = append(edges, dataHi)
	parts := make([]string, n)
	for k := range n {
		parts[k] = shades[1+k] + " " + fmtValue(edges[k]) + ".." + fmtValue(edges[k+1])
	}
	return joinLegend(parts)
}

// quantile interpolates linearly between order statistics (type 7).
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
	return sorted[lo] + (sorted[hi]-sorted[lo])*(pos-float64(lo))
}

func renderBoxplot(in *input) (string, error) {
	w := in.width
	if w == 0 {
		w = 40
	}
	type summary struct{ min, q1, med, q3, max float64 }
	var summaries []summary
	var names []string
	gMin, gMax := math.Inf(1), math.Inf(-1)
	for i, s := range in.series {
		if len(s.values) == 0 {
			return "", errorf("series %d %s must contain at least one value", i, quote(s.name))
		}
		sv := append([]float64(nil), s.values...)
		sort.SliceStable(sv, func(a, b int) bool { return sv[a] < sv[b] })
		fn := summary{sv[0], quantile(sv, 0.25), quantile(sv, 0.5), quantile(sv, 0.75), sv[len(sv)-1]}
		summaries = append(summaries, fn)
		names = append(names, seriesLabel(s, i))
		gMin, gMax = pyMin(gMin, fn.min), pyMax(gMax, fn.max)
	}
	gMin, gMax = scaleRange(gMin, gMax)
	maxNameW := 0
	for _, n := range names {
		maxNameW = maxInt(maxNameW, width(n))
	}
	colorOn := in.color
	pos := func(v float64) int {
		return clamp(round((v-gMin)/(gMax-gMin)*float64(w-1)), 0, w-1)
	}
	// the five numbers as a table: a header row names the columns once, each column right-aligned
	stats := make([][]string, len(summaries))
	colW := make([]int, len(boxStats))
	for k, h := range boxStats {
		colW[k] = len(h)
	}
	cols := make([][]float64, len(boxStats))
	for _, fn := range summaries {
		for k, v := range []float64{fn.min, fn.q1, fn.med, fn.q3, fn.max} {
			cols[k] = append(cols[k], v)
		}
	}
	for k := range cols {
		for i, s := range fmtColumn(cols[k]) {
			stats[i] = append(stats[i], s)
			colW[k] = maxInt(colW[k], len(s))
		}
	}
	table := func(cols []string) string {
		out := make([]string, len(cols))
		for k, s := range cols {
			out[k] = repeat(" ", colW[k]-len(s)) + s
		}
		return strings.Join(out, " ")
	}
	lines := make([]string, len(summaries)+1)
	lines[0] = repeat(" ", maxNameW) + " │ " + repeat(" ", w) + " " + table(boxStats)
	for i, fn := range summaries {
		row := make([]string, w)
		for x := range row {
			row[x] = " "
		}
		minP, q1P, medP, q3P, maxP := pos(fn.min), pos(fn.q1), pos(fn.med), pos(fn.q3), pos(fn.max)
		for x := minP; x <= maxP; x++ {
			row[x] = "─"
		}
		for x := q1P; x <= q3P; x++ {
			row[x] = "█"
		}
		row[minP], row[maxP], row[medP] = "├", "┤", "║" // ║, not the heavy ┃: not in Consolas
		body := colorize(strings.Join(row, ""), seriesColor(i), colorOn)
		lines[i+1] = pad(names[i], maxNameW) + " │ " + body + " " + table(stats[i])
	}
	return strings.Join(lines, "\n"), nil
}

var boxStats = []string{"min", "q1", "med", "q3", "max"}
