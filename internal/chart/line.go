package chart

import (
	"fmt"
	"math"
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
	if in.Threshold != nil {
		min = math.Min(min, *in.Threshold)
		max = math.Max(max, *in.Threshold)
	}
	colorOn := in.UseColor.enabled()

	c := newCanvas(mode, width, height)
	pw, ph := c.pixelWidth(), c.pixelHeight()

	// A solid block reads as a thick, flat-edged line. That looks fine on
	// its own, but clashes with the round dot markers from ShowPoints, so
	// the connecting line switches to a thin centered dot in that case
	// (cell mode only — quad/braille already draw a thin line by nature).
	var lineChar rune
	if in.ShowPoints {
		lineChar = '·'
	}

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
				c.line(prevX, prevY, x, y, lineChar, color)
			} else {
				c.setDot(x, y, lineChar, color)
			}
			prevX, prevY = x, y
		}
	}

	if in.Threshold != nil {
		drawThreshold(c, *in.Threshold, min, max, colorOn)
	}

	if in.ShowPoints {
		customPoint := rune(0)
		if in.PointChar != "" {
			customPoint = []rune(in.PointChar)[0]
		}
		for si, s := range in.Series {
			color := -1
			if colorOn {
				color = seriesColor(si)
			}
			marker := markers[si%len(markers)]
			if customPoint != 0 {
				marker = customPoint
			}
			n := len(s.Values)
			for i, v := range s.Values {
				x := xPixel(i, n, pw)
				y := yPixel(v, min, max, ph)
				c.setMarker(x/c.subX, y/c.subY, marker, color)
			}
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
	if in.Threshold != nil {
		note := fmt.Sprintf("- - threshold: %s", formatValue(*in.Threshold))
		if len(in.Series) > 1 {
			body += "   " + note
		} else {
			body += "\n\n" + note
		}
	}

	return body, nil
}

// drawThreshold overlays a dashed horizontal reference line at value,
// overwriting whatever line/canvas content occupies that row so it stays
// legible regardless of resolution mode.
func drawThreshold(c *canvas, value, min, max float64, colorOn bool) {
	row := yPixel(value, min, max, c.pixelHeight()) / c.subY
	color := -1
	if colorOn {
		color = thresholdColor
	}
	for x := 0; x < c.width; x++ {
		if x%2 == 0 {
			c.setMarker(x, row, '-', color)
		}
	}
}
