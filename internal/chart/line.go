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
	dotted := in.Style == "dotted"
	multiSeries := len(in.Series) > 1

	for si, s := range in.Series {
		color := -1
		if colorOn {
			color = seriesColor(si)
		}

		// In cell mode, more than one series needs its own glyph or they'd
		// overlap into one indistinguishable line without color — quad and
		// braille modes can't do this at all (every series shares the same
		// sub-character bits), which is why the legend below only claims a
		// shape distinction when mode is cell.
		var lineChar rune
		switch {
		case in.ShowPoints:
			lineChar = '·'
		case multiSeries && mode == ModeCell:
			lineChar = fills[si%len(fills)]
		case dotted:
			lineChar = '+'
		}

		n := len(s.Values)
		prevX, prevY := -1, -1
		for i, v := range s.Values {
			x := xPixel(i, n, pw)
			y := yPixel(v, min, max, ph)
			if prevX >= 0 {
				if dotted {
					c.lineDotted(prevX, prevY, x, y, lineChar, color)
				} else {
					c.line(prevX, prevY, x, y, lineChar, color)
				}
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
	if multiSeries {
		body += "\n\n" + lineLegend(in.Series, mode, in.ShowPoints, colorOn, width)
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

// lineLegend picks the legend that actually matches what renderLine drew:
// the marker ramp when ShowPoints put a real per-series glyph on the
// canvas, the fill ramp when cell-mode gave each series its own connecting
// character, and — since neither exists in quad/braille without color,
// where every series shares the same sub-character bits — a plain name
// list with an explanation instead of a swatch that would claim a
// distinction the chart doesn't draw.
func lineLegend(series []Series, mode Mode, showPoints, colorOn bool, width int) string {
	names := make([]string, len(series))
	for i, s := range series {
		names[i] = seriesLabel(s, i)
	}
	// ShowPoints stamps a real per-series marker glyph on the canvas at
	// every data point (setMarker overrides a cell outright, unlike the
	// connecting line, so this works even in quad/braille) — accurate in
	// every mode, so it's checked before the mode/color fallback below.
	if showPoints {
		return namedLegendRamp(names, colorOn, markers)
	}
	if mode != ModeCell && !colorOn {
		return plainNameList(names, width)
	}
	return namedLegendRamp(names, colorOn, fills)
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
