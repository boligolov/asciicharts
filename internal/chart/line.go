package chart

import (
	"fmt"
	"strings"
)

func renderLine(in Input) (string, error) {
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

	for i, s := range in.Series {
		if len(s.Values) < 2 {
			return "", fmt.Errorf("series %d %q must contain at least two values", i, s.Name)
		}
	}

	min, max := seriesMinMax(in.Series)
	colorOn := in.UseColor.enabled()

	c := newCanvas(mode, width, height)
	pw, ph := c.pixelWidth(), c.pixelHeight()

	for si, s := range in.Series {
		color := -1
		if colorOn {
			color = seriesColor(si)
		}
		n := len(s.Values)
		prevX, prevY := -1, -1
		for i, v := range s.Values {
			x := xPixel(i, n, pw)
			y := yPixel(v, min, max, ph)
			if prevX >= 0 {
				c.line(prevX, prevY, x, y, 0, color)
			} else {
				c.setDot(x, y, 0, color)
			}
			prevX, prevY = x, y
		}
	}

	axisLabels, axisWidth := leftAxisLabels(min, max, height)
	rows := c.render(colorOn)

	var sb strings.Builder
	for row, l := range rows {
		fmt.Fprintf(&sb, "%*s ┤%s\n", axisWidth, axisLabels[row], l)
	}
	body := strings.TrimSuffix(sb.String(), "\n")

	if x := xAxisLabels(in.Labels, seriesMaxLen(in.Series), width, axisWidth+2); x != "" {
		body += "\n" + x
	}
	if len(in.Series) > 1 {
		body += "\n\n" + legendLine(in.Series, colorOn)
	}

	return body, nil
}
