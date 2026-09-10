package chart

import (
	"fmt"
	"math"
	"strings"
)

// pieAspect corrects for terminal character cells being roughly twice as
// tall as they are wide, so a rasterized circle looks round rather than
// egg-shaped.
const pieAspect = 2.0

func renderPie(in Input) (string, error) {
	values := make([]float64, len(in.Series))
	names := make([]string, len(in.Series))
	total := 0.0
	for i, s := range in.Series {
		v := 0.0
		for _, x := range s.Values {
			v += x
		}
		if v < 0 {
			return "", fmt.Errorf("series %d %q: pie slice values must be non-negative", i, s.Name)
		}
		values[i] = v
		names[i] = seriesLabel(s, i)
		total += v
	}
	if total <= 0 {
		return "", fmt.Errorf("pie slice values must sum to more than zero")
	}

	width, height := in.Width, in.Height
	switch {
	case width <= 0 && height <= 0:
		width, height = 44, 22
	case width <= 0:
		width = height * 2
	case height <= 0:
		height = width / 2
	}
	if height < 1 {
		height = 1
	}

	cumulative := make([]float64, len(values))
	sum := 0.0
	for i, v := range values {
		sum += v
		cumulative[i] = sum / total
	}

	colorOn := in.UseColor.enabled()
	cx, cy := float64(width)/2, float64(height)/2
	radius := math.Min(float64(width)/2, float64(height)/2*pieAspect)

	grid := make([][]rune, height)
	colorGrid := make([][]int, height)
	for y := 0; y < height; y++ {
		grid[y] = make([]rune, width)
		colorGrid[y] = make([]int, width)
		for x := 0; x < width; x++ {
			grid[y][x] = ' '
			colorGrid[y][x] = -1
		}
	}

	for y := 0; y < height; y++ {
		for x := 0; x < width; x++ {
			dx := float64(x) + 0.5 - cx
			dy := (float64(y) + 0.5 - cy) * pieAspect
			if math.Hypot(dx, dy) > radius {
				continue
			}
			angle := math.Atan2(dx, -dy)
			if angle < 0 {
				angle += 2 * math.Pi
			}
			frac := angle / (2 * math.Pi)

			slice := len(cumulative) - 1
			for i, c := range cumulative {
				if frac <= c {
					slice = i
					break
				}
			}

			grid[y][x] = fills[slice%len(fills)]
			if colorOn {
				colorGrid[y][x] = seriesColor(slice)
			}
		}
	}

	var sb strings.Builder
	for y := 0; y < height; y++ {
		for x := 0; x < width; x++ {
			sb.WriteString(colorize(string(grid[y][x]), colorGrid[y][x], colorOn))
		}
		if y < height-1 {
			sb.WriteByte('\n')
		}
	}

	legend := make([]string, len(values))
	for i, v := range values {
		pct := v / total * 100
		legend[i] = fmt.Sprintf("%s %s: %s (%.1f%%)", legendSwatch(i, colorOn), names[i], formatValue(v), pct)
	}

	return sb.String() + "\n\n" + strings.Join(legend, "\n"), nil
}
