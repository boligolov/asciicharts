package chart

import (
	"fmt"
	"strings"
)

// dualAxisGlyphs distinguishes the two series from each other in cell mode,
// where overlapping points would otherwise be indistinguishable without
// color.
var dualAxisGlyphs = [2]rune{'█', '▒'}

func renderDualAxis(in Input) (string, error) {
	if len(in.Series) != 2 {
		return "", fmt.Errorf("dual_axis expects exactly two series, got %d", len(in.Series))
	}
	for i, s := range in.Series {
		if len(s.Values) < 2 {
			return "", fmt.Errorf("series %d %q must contain at least two values", i, s.Name)
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
	mode := Mode(in.Mode)
	if mode == "" {
		mode = ModeCell
	}

	colorOn := in.UseColor.enabled()
	c := newCanvas(mode, width, height)
	pw, ph := c.pixelWidth(), c.pixelHeight()

	mins := make([]float64, 2)
	maxs := make([]float64, 2)
	for si, s := range in.Series {
		mins[si], maxs[si] = seriesMinMax([]Series{s})

		color := -1
		if colorOn {
			color = seriesColor(si)
		}
		glyph := dualAxisGlyphs[si]

		n := len(s.Values)
		prevX, prevY := -1, -1
		for i, v := range s.Values {
			x := xPixel(i, n, pw)
			y := yPixel(v, mins[si], maxs[si], ph)
			if prevX >= 0 {
				c.line(prevX, prevY, x, y, glyph, color)
			} else {
				c.setDot(x, y, glyph, color)
			}
			prevX, prevY = x, y
		}
	}

	leftLabels, leftWidth := leftAxisLabels(mins[0], maxs[0], height)
	rightLabels, rightWidth := leftAxisLabels(mins[1], maxs[1], height)
	rows := c.render(colorOn)

	var sb strings.Builder
	for row, l := range rows {
		fmt.Fprintf(&sb, "%*s ┤%s├ %-*s\n", leftWidth, leftLabels[row], l, rightWidth, rightLabels[row])
	}
	body := strings.TrimSuffix(sb.String(), "\n")

	legend := fmt.Sprintf("left:  %s %s\nright: %s %s",
		colorize(string(dualAxisGlyphs[0]), seriesColor(0), colorOn), seriesLabel(in.Series[0], 0),
		colorize(string(dualAxisGlyphs[1]), seriesColor(1), colorOn), seriesLabel(in.Series[1], 1),
	)

	return body + "\n\n" + legend, nil
}
