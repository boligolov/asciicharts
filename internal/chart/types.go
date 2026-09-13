// Package chart renders data as ASCII/Unicode text charts.
package chart

import "github.com/boligolov/ascii-charts-mcp/internal/border"

// Type identifies which chart renderer to use.
type Type string

const (
	Sparkline Type = "sparkline"
	VBar      Type = "vbar"
	HBar      Type = "hbar"
	Line      Type = "line"
	Area      Type = "area"
	Scatter   Type = "scatter"
	DualAxis  Type = "dual_axis"
	Pie       Type = "pie"
	Histogram Type = "histogram"
	Heatmap   Type = "heatmap"
	Boxplot   Type = "boxplot"
	DotPlot   Type = "dotplot"
)

// Point is a single (x, y) sample, used by scatter charts.
type Point struct {
	X float64 `json:"x"`
	Y float64 `json:"y"`
}

// Series is one row of chart input. Which fields are used, and what they
// mean, depends on chartType:
//   - sparkline, line, area, histogram: Values is the sample sequence (one
//     series each for line/area, exactly one series for sparkline/histogram).
//   - vbar, hbar, dotplot: Values holds one number per category (in
//     Labels); vbar/hbar draw multiple series grouped or stacked (see
//     Stacked), dotplot always overlays them on the same row.
//   - scatter: Points holds the (x, y) samples.
//   - dual_axis: exactly two series, each like a line series, each with
//     its own y-axis scale.
//   - pie: Values[0] is the slice's magnitude, Name is its label.
//   - heatmap: Values is one matrix row, aligned with Labels as column
//     headers; Name is the row label.
//   - boxplot: Values is the raw sample population a five-number summary
//     (min/Q1/median/Q3/max) is computed from; Name is the box's label.
type Series struct {
	Name   string    `json:"name,omitempty" jsonschema:"optional series/category/row name, used in legends and axis labels"`
	Values []float64 `json:"values,omitempty" jsonschema:"numeric values; meaning depends on chartType, see tool description"`
	Points []Point   `json:"points,omitempty" jsonschema:"(x, y) samples, used only by scatter charts"`
}

// Input is the full set of parameters accepted by the render_chart tool.
type Input struct {
	ChartType Type         `json:"chartType" jsonschema:"chart type: sparkline, vbar, hbar, line, area, scatter, dual_axis, pie, histogram, heatmap, boxplot or dotplot"`
	Series    []Series     `json:"series" jsonschema:"one or more data series/rows/slices to plot; see chartType for how each is interpreted"`
	Labels    []string     `json:"labels,omitempty" jsonschema:"category labels for vbar/hbar/histogram/dotplot bars, or column headers for a heatmap"`
	Title     string       `json:"title,omitempty" jsonschema:"optional title shown above the chart"`
	Width     int          `json:"width,omitempty" jsonschema:"chart width in characters (default depends on chart type)"`
	Height    int          `json:"height,omitempty" jsonschema:"chart height in rows (default depends on chart type)"`
	Border    border.Style `json:"border,omitempty" jsonschema:"border style: none, ascii, light, heavy, double or rounded (default: light)"`
	Mode      Mode         `json:"mode,omitempty" jsonschema:"sub-character resolution for line/scatter/dual_axis: cell (1 point per character), quad (2x2 via quadrant blocks) or braille (2x4 via braille dots); default: cell"`
	Style     string       `json:"style,omitempty" jsonschema:"visual style, meaning depends on chartType. vbar/hbar/histogram/area: solid (default; for vbar/hbar/histogram, flat blocks with sub-character precision), halftone (lighter stippled Unicode shades per series, no solid block), or ascii (plain-ASCII letters/punctuation per series — #, X, H, W, =, :, |, . — that render identically in any monospace font, no Unicode block-glyph support required). line: solid (default) or dotted (sparse plotted-dot trend line instead of a solid stroke)"`
	Stacked   bool         `json:"stacked,omitempty" jsonschema:"for vbar/hbar/area with multiple series, stack them (bars side-by-side by category, or area bands cumulative from zero) instead of grouping/overlaying"`
	Bins      int          `json:"bins,omitempty" jsonschema:"number of buckets for histogram charts (default: 10)"`
	UseColor  UseColor     `json:"useColor,omitempty" jsonschema:"ANSI 256-color output: auto, on or off (default: auto, which is equivalent to off since tool output is plain text for an agent, not a terminal)"`

	// Threshold, ShowPoints and PointChar apply only to chartType "line".
	Threshold  *float64 `json:"threshold,omitempty" jsonschema:"line charts only: draw a dashed horizontal reference line at this y-value"`
	ShowPoints bool     `json:"showPoints,omitempty" jsonschema:"line charts only: mark each individual data point with a glyph on top of the connecting line"`
	PointChar  string   `json:"pointChar,omitempty" jsonschema:"line charts only, with showPoints: single character used to mark points on every series (default: a large circle for the first series, with a distinct shape per additional series)"`
}
