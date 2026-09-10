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
	Scatter   Type = "scatter"
	DualAxis  Type = "dual_axis"
	Pie       Type = "pie"
	Histogram Type = "histogram"
	Heatmap   Type = "heatmap"
	Boxplot   Type = "boxplot"
)

// Point is a single (x, y) sample, used by scatter charts.
type Point struct {
	X float64 `json:"x"`
	Y float64 `json:"y"`
}

// Series is one row of chart input. Which fields are used, and what they
// mean, depends on chartType:
//   - sparkline, line, histogram: Values is the sample sequence (one
//     series each for line, exactly one series for sparkline/histogram).
//   - vbar, hbar: Values holds one number per category (in Labels);
//     multiple series are drawn grouped or stacked (see Stacked).
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
	ChartType Type         `json:"chartType" jsonschema:"chart type: sparkline, vbar, hbar, line, scatter, dual_axis, pie, histogram, heatmap or boxplot"`
	Series    []Series     `json:"series" jsonschema:"one or more data series/rows/slices to plot; see chartType for how each is interpreted"`
	Labels    []string     `json:"labels,omitempty" jsonschema:"category labels for vbar/hbar/histogram bars, or column headers for a heatmap"`
	Title     string       `json:"title,omitempty" jsonschema:"optional title shown above the chart"`
	Width     int          `json:"width,omitempty" jsonschema:"chart width in characters (default depends on chart type)"`
	Height    int          `json:"height,omitempty" jsonschema:"chart height in rows (default depends on chart type)"`
	Border    border.Style `json:"border,omitempty" jsonschema:"border style: none, ascii, light, heavy, double or rounded (default: light)"`
	Mode      Mode         `json:"mode,omitempty" jsonschema:"sub-character resolution for line/scatter/dual_axis: cell (1 point per character), quad (2x2 via quadrant blocks) or braille (2x4 via braille dots); default: cell"`
	Stacked   bool         `json:"stacked,omitempty" jsonschema:"for vbar/hbar with multiple series, stack bars instead of grouping them side by side"`
	Bins      int          `json:"bins,omitempty" jsonschema:"number of buckets for histogram charts (default: 10)"`
	UseColor  UseColor     `json:"useColor,omitempty" jsonschema:"ANSI 256-color output: auto, on or off (default: auto, which is equivalent to off since tool output is plain text for an agent, not a terminal)"`
}
