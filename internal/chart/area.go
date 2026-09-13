package chart

import (
	"fmt"
	"math"
	"strings"
)

func renderArea(in Input) (string, error) {
	if len(in.Series) == 0 {
		return "", fmt.Errorf("series must contain at least one entry")
	}
	n := len(in.Series[0].Values)
	for i, s := range in.Series {
		if len(s.Values) < 2 {
			return "", fmt.Errorf("series %d %q must contain at least two values", i, s.Name)
		}
		if len(s.Values) != n {
			return "", fmt.Errorf("all series must have the same number of values (series 0 has %d, series %d has %d)", n, i, len(s.Values))
		}
	}

	height := in.Height
	if height <= 0 {
		height = 10
	}
	width := in.Width
	if width <= 0 {
		width = 60
	}
	colorOn := in.UseColor.enabled()
	ramp := areaFillRamp(in.Style)
	numSeries := len(in.Series)

	names := make([]string, numSeries)
	for i, s := range in.Series {
		names[i] = seriesLabel(s, i)
	}

	grid := make([][]rune, height)
	colorGrid := make([][]int, height)
	for r := range grid {
		grid[r] = make([]rune, width)
		colorGrid[r] = make([]int, width)
		for x := range grid[r] {
			grid[r][x] = ' '
			colorGrid[r][x] = -1
		}
	}

	var minVal, maxVal float64

	if in.Stacked {
		// Stacked area assumes non-negative values, like stacked bars: each
		// series is a band stacked cumulatively from a zero baseline.
		minVal = 0
		maxVal = 0
		for x := 0; x < width; x++ {
			sum := 0.0
			for _, s := range in.Series {
				sum += interpAt(s.Values, x, width)
			}
			maxVal = math.Max(maxVal, sum)
		}
		if maxVal == 0 {
			maxVal = 1
		}

		// Per column, allocate exact integer row counts per series that sum
		// to the column's total height (allocateProportional, the same
		// largest-remainder allocator stacked vbar uses) rather than
		// rounding each series' own cumulative boundary independently —
		// that would let adjacent bands round to overlapping boundary rows
		// and silently swallow whichever series is thinnest.
		for x := 0; x < width; x++ {
			values := make([]float64, numSeries)
			colSum := 0.0
			for si, s := range in.Series {
				values[si] = interpAt(s.Values, x, width)
				colSum += values[si]
			}
			totalRows := int(math.Round(colSum / maxVal * float64(height)))
			alloc := allocateProportional(values, colSum, totalRows)
			cursor := 0
			for si, segRows := range alloc {
				ch := ramp[si%len(ramp)]
				color := -1
				if colorOn {
					color = seriesColor(si)
				}
				for r := 0; r < segRows; r++ {
					row := height - 1 - cursor - r
					if row < 0 || row >= height {
						continue
					}
					grid[row][x] = ch
					colorGrid[row][x] = color
				}
				cursor += segRows
			}
		}
	} else {
		minVal, maxVal = seriesMinMax(in.Series)
		minVal = math.Min(minVal, 0)
		maxVal = math.Max(maxVal, 0)
		if maxVal == minVal {
			maxVal = minVal + 1
		}
		zeroRow := yPixel(0, minVal, maxVal, height)

		// Paint later series first so the first (presumably primary) series
		// ends up drawn on top wherever overlaid areas overlap.
		for si := numSeries - 1; si >= 0; si-- {
			s := in.Series[si]
			ch := ramp[si%len(ramp)]
			color := -1
			if colorOn {
				color = seriesColor(si)
			}
			for x := 0; x < width; x++ {
				v := interpAt(s.Values, x, width)
				row := yPixel(v, minVal, maxVal, height)
				lo, hi := diverging2(row, zeroRow)
				for r := lo; r <= hi; r++ {
					grid[r][x] = ch
					colorGrid[r][x] = color
				}
			}
		}
	}

	axisLabels, axisWidth := leftAxisLabels(minVal, maxVal, height)
	var sb strings.Builder
	for r := 0; r < height; r++ {
		var line strings.Builder
		for x := 0; x < width; x++ {
			line.WriteString(colorize(string(grid[r][x]), colorGrid[r][x], colorOn))
		}
		fmt.Fprintf(&sb, "%*s ┤%s\n", axisWidth, axisLabels[r], line.String())
	}
	body := strings.TrimSuffix(sb.String(), "\n")

	if x := xAxisLabels(in.Labels, seriesMaxLen(in.Series), width, axisWidth+2); x != "" {
		body += "\n" + x
	}
	if numSeries > 1 {
		body += "\n\n" + namedLegendRamp(names, colorOn, ramp)
	}

	return body, nil
}

// areaFillRamp resolves an area chart's style into a fill-glyph ramp. Unlike
// bar charts, area charts always tile a glyph (there's no sub-character
// "solid block with eighths" mode for a filled region), so "solid" still
// resolves to a concrete ramp — fills, whose first glyph is a plain solid
// block, matching a single-series area chart's expected flat fill.
func areaFillRamp(style string) []rune {
	switch style {
	case "halftone":
		return halftoneFills
	case "ascii":
		// A reordering of asciiFills for area's own purposes: an area
		// chart's second-and-later bands are often thin slivers stacked on
		// a much larger first band, so ':' (much lighter than 'X') reads
		// better there than it would cycling through bar chart series,
		// which tend to be closer in size to each other.
		return []rune{'#', ':', 'H', 'W', '=', 'X', '|', '.'}
	default:
		return fills
	}
}

// interpAt linearly interpolates values at continuous character column x
// (0..width-1). This is the inverse of xPixel, which places sample i at
// column i*(width-1)/(n-1); interpAt fills in the columns between samples
// so an area chart's fill has no gaps.
func interpAt(values []float64, x, width int) float64 {
	n := len(values)
	if n == 1 || width <= 1 {
		return values[0]
	}
	pos := float64(x) * float64(n-1) / float64(width-1)
	i0 := int(pos)
	if i0 >= n-1 {
		return values[n-1]
	}
	frac := pos - float64(i0)
	return values[i0]*(1-frac) + values[i0+1]*frac
}
