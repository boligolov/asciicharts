package chart_test

import (
	"strings"
	"testing"

	"github.com/boligolov/ascii-charts-mcp/internal/chart"
)

// TestGroupedVBarSeriesDistinctWithoutColor guards against a bug where
// solid-style grouped bars all rendered as the same glyph ('█'), making
// series indistinguishable from each other in the body even though the
// legend below always showed a different swatch per series.
func TestGroupedVBarSeriesDistinctWithoutColor(t *testing.T) {
	out, err := chart.Render(chart.Input{
		ChartType: chart.VBar,
		Height:    4,
		Series: []chart.Series{
			{Name: "A", Values: []float64{10, 10}},
			{Name: "B", Values: []float64{10, 10}},
		},
		Labels: []string{"x", "y"},
	})
	if err != nil {
		t.Fatalf("Render: %v", err)
	}
	body, _, _ := strings.Cut(out, "\n\n")
	if !strings.ContainsRune(body, '█') || !strings.ContainsRune(body, '▓') {
		t.Fatalf("expected series A and B to render with distinct glyphs in the body, got:\n%s", out)
	}
}

// TestGroupedVBarSingleSeriesStaysSolid guards the other side of the same
// fix: a lone series must keep the plain solid block (and its eighth-block
// sub-row precision), not switch to a shaded glyph it doesn't need.
func TestGroupedVBarSingleSeriesStaysSolid(t *testing.T) {
	out, err := chart.Render(chart.Input{
		ChartType: chart.VBar,
		Height:    4,
		Series:    []chart.Series{{Values: []float64{10, 10}}},
		Labels:    []string{"x", "y"},
	})
	if err != nil {
		t.Fatalf("Render: %v", err)
	}
	if strings.ContainsRune(out, '▓') {
		t.Fatalf("expected a single series to stay a plain solid block, got:\n%s", out)
	}
}

// TestMultiSeriesCellLineDistinctWithoutColor guards against a bug where
// every series in a cell-mode line chart shared one connecting character,
// making them indistinguishable without color despite the legend claiming
// otherwise.
func TestMultiSeriesCellLineDistinctWithoutColor(t *testing.T) {
	out, err := chart.Render(chart.Input{
		ChartType: chart.Line,
		Height:    4,
		Series: []chart.Series{
			{Name: "A", Values: []float64{1, 2, 1, 2}},
			{Name: "B", Values: []float64{2, 1, 2, 1}},
		},
	})
	if err != nil {
		t.Fatalf("Render: %v", err)
	}
	body, _, _ := strings.Cut(out, "\n\n")
	if !strings.ContainsRune(body, '█') || !strings.ContainsRune(body, '▓') {
		t.Fatalf("expected series A and B to render with distinct glyphs in the body, got:\n%s", out)
	}
}

// TestBrailleMultiSeriesLegendDoesNotClaimShapeWithoutColor guards against
// a legend claiming a shape distinction that quad/braille can't actually
// draw: every series shares the same packed sub-character bits there, so
// without color, a swatch-per-series legend was actively misleading.
func TestBrailleMultiSeriesLegendDoesNotClaimShapeWithoutColor(t *testing.T) {
	out, err := chart.Render(chart.Input{
		ChartType: chart.Line,
		Mode:      chart.ModeBraille,
		Height:    4,
		Width:     20,
		Series: []chart.Series{
			{Name: "forecast", Values: []float64{1, 2, 1, 2}},
			{Name: "actual", Values: []float64{2, 1, 2, 1}},
		},
	})
	if err != nil {
		t.Fatalf("Render: %v", err)
	}
	if strings.Contains(out, "█ forecast") || strings.Contains(out, "▓ actual") {
		t.Fatalf("legend should not claim a shape distinction quad/braille can't draw without color, got:\n%s", out)
	}
	if !strings.Contains(out, "forecast, actual") {
		t.Fatalf("expected a plain name list in the legend, got:\n%s", out)
	}
	if !strings.Contains(out, "useColor") {
		t.Fatalf("expected a caveat mentioning useColor, got:\n%s", out)
	}
}

// TestBrailleMultiSeriesWithColorKeepsSwatchLegend checks the flip side:
// once color is on, it's the real differentiator, so the ordinary
// swatch-per-series legend is accurate again.
func TestBrailleMultiSeriesWithColorKeepsSwatchLegend(t *testing.T) {
	out, err := chart.Render(chart.Input{
		ChartType: chart.Line,
		Mode:      chart.ModeBraille,
		Height:    4,
		Width:     20,
		UseColor:  chart.ColorOn,
		Series: []chart.Series{
			{Name: "forecast", Values: []float64{1, 2, 1, 2}},
			{Name: "actual", Values: []float64{2, 1, 2, 1}},
		},
	})
	if err != nil {
		t.Fatalf("Render: %v", err)
	}
	if strings.Contains(out, "forecast, actual") {
		t.Fatalf("expected the normal swatch legend once color is on, got:\n%s", out)
	}
}
