package chart

import (
	"fmt"
	"math"
	"strings"
)

func renderScatter(in Input) (string, error) {
	width := in.Width
	if width <= 0 {
		width = 60
	}
	height := in.Height
	if height <= 0 {
		height = 15
	}
	mode := Mode(in.Mode)
	if mode == "" {
		mode = ModeCell
	}

	var all []Point
	for i, s := range in.Series {
		if len(s.Points) == 0 {
			return "", fmt.Errorf("series %d %q must contain at least one point", i, s.Name)
		}
		all = append(all, s.Points...)
	}

	minX, maxX := all[0].X, all[0].X
	minY, maxY := all[0].Y, all[0].Y
	for _, p := range all {
		minX, maxX = math.Min(minX, p.X), math.Max(maxX, p.X)
		minY, maxY = math.Min(minY, p.Y), math.Max(maxY, p.Y)
	}
	if maxX == minX {
		maxX = minX + 1
	}
	if maxY == minY {
		maxY = minY + 1
	}

	colorOn := in.UseColor.enabled()
	c := newCanvas(mode, width, height)
	pw, ph := c.pixelWidth(), c.pixelHeight()

	for si, s := range in.Series {
		color := -1
		if colorOn {
			color = seriesColor(si)
		}
		for _, p := range s.Points {
			px := int(math.Round((p.X - minX) / (maxX - minX) * float64(pw-1)))
			py := ph - 1 - int(math.Round((p.Y-minY)/(maxY-minY)*float64(ph-1)))
			if mode == ModeCell {
				c.setMarker(px, py, markers[si%len(markers)], color)
			} else {
				c.setDot(px, py, 0, color)
			}
		}
	}

	rows := c.render(colorOn)
	body := strings.Join(rows, "\n")
	body += fmt.Sprintf("\nx: [%s, %s]  y: [%s, %s]", formatValue(minX), formatValue(maxX), formatValue(minY), formatValue(maxY))
	if len(in.Series) > 1 {
		body += "\n" + scatterLegend(in.Series, mode, colorOn)
	}

	return body, nil
}

func scatterLegend(series []Series, mode Mode, colorOn bool) string {
	parts := make([]string, len(series))
	for i, s := range series {
		var glyph rune
		if mode == ModeCell {
			glyph = markers[i%len(markers)]
		} else {
			glyph = fills[i%len(fills)]
		}
		parts[i] = fmt.Sprintf("%s %s", colorize(string(glyph), seriesColor(i), colorOn), seriesLabel(s, i))
	}
	return strings.Join(parts, "   ")
}
