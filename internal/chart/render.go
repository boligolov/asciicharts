package chart

import (
	"fmt"

	"github.com/boligolov/ascii-charts-mcp/internal/border"
)

// Render validates in and dispatches to the renderer for in.ChartType,
// then wraps the resulting body in the requested border/title.
func Render(in Input) (string, error) {
	if err := validate(in); err != nil {
		return "", err
	}

	var (
		body string
		err  error
	)
	switch in.ChartType {
	case Sparkline:
		body, err = renderSparkline(in)
	case VBar, HBar:
		body, err = renderBar(in)
	case Line:
		body, err = renderLine(in)
	case Scatter:
		body, err = renderScatter(in)
	case DualAxis:
		body, err = renderDualAxis(in)
	case Pie:
		body, err = renderPie(in)
	case Histogram:
		body, err = renderHistogram(in)
	case Heatmap:
		body, err = renderHeatmap(in)
	case Boxplot:
		body, err = renderBoxplot(in)
	default:
		return "", fmt.Errorf(
			"unknown chartType %q (expected one of: sparkline, vbar, hbar, line, scatter, dual_axis, pie, histogram, heatmap, boxplot)",
			in.ChartType)
	}
	if err != nil {
		return "", err
	}

	return border.Wrap(body, in.Title, in.Border), nil
}

func validate(in Input) error {
	if len(in.Series) == 0 {
		return fmt.Errorf("series must contain at least one entry")
	}
	if !border.Valid(in.Border) {
		return fmt.Errorf("invalid border %q (expected one of: none, ascii, light, heavy, double, rounded)", in.Border)
	}
	if !validMode(in.Mode) {
		return fmt.Errorf("invalid mode %q (expected one of: cell, quad, braille)", in.Mode)
	}
	if !validUseColor(in.UseColor) {
		return fmt.Errorf("invalid useColor %q (expected one of: auto, on, off)", in.UseColor)
	}
	return nil
}
