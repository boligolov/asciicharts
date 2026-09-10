package chart_test

import (
	"fmt"
	"testing"

	"github.com/boligolov/ascii-charts-mcp/internal/border"
	"github.com/boligolov/ascii-charts-mcp/internal/chart"
)

func TestSmokeAllChartTypes(t *testing.T) {
	cases := []chart.Input{
		{
			ChartType: chart.Sparkline,
			Title:     "Sparkline",
			Border:    border.None,
			Series:    []chart.Series{{Name: "latency", Values: []float64{1, 5, 3, 9, 2, 7, 4}}},
		},
		{
			ChartType: chart.VBar,
			Title:     "VBar single",
			Border:    border.Rounded,
			Series:    []chart.Series{{Values: []float64{10, 45, 30, 80, 60}}},
			Labels:    []string{"Jan", "Feb", "Mar", "Apr", "May"},
		},
		{
			ChartType: chart.VBar,
			Title:     "VBar grouped",
			Border:    border.Heavy,
			Series: []chart.Series{
				{Name: "A", Values: []float64{10, 45, 30}},
				{Name: "B", Values: []float64{20, 15, 50}},
			},
			Labels: []string{"Jan", "Feb", "Mar"},
		},
		{
			ChartType: chart.VBar,
			Title:     "VBar stacked",
			Border:    border.Double,
			Stacked:   true,
			Series: []chart.Series{
				{Name: "A", Values: []float64{10, 45, 30}},
				{Name: "B", Values: []float64{20, 15, 50}},
			},
			Labels: []string{"Jan", "Feb", "Mar"},
		},
		{
			ChartType: chart.HBar,
			Title:     "HBar single",
			Border:    border.ASCII,
			Series:    []chart.Series{{Values: []float64{10, 45, 30, 80, 60}}},
			Labels:    []string{"Jan", "Feb", "Mar", "Apr", "May"},
		},
		{
			ChartType: chart.HBar,
			Title:     "HBar grouped",
			Border:    border.Light,
			Series: []chart.Series{
				{Name: "A", Values: []float64{10, 45}},
				{Name: "B", Values: []float64{20, 15}},
			},
			Labels: []string{"Jan", "Feb"},
		},
		{
			ChartType: chart.HBar,
			Title:     "HBar stacked",
			Border:    border.Light,
			Stacked:   true,
			Series: []chart.Series{
				{Name: "A", Values: []float64{10, 45}},
				{Name: "B", Values: []float64{20, 15}},
			},
			Labels: []string{"Jan", "Feb"},
		},
		{
			ChartType: chart.Line,
			Title:     "Line cell, two series",
			Border:    border.Light,
			Series: []chart.Series{
				{Name: "A", Values: []float64{1, 3, 2, 5, 4, 8, 6, 9, 7}},
				{Name: "B", Values: []float64{9, 7, 8, 4, 6, 2, 5, 1, 3}},
			},
		},
		{
			ChartType:  chart.Line,
			Title:      "Line with threshold and points",
			Border:     border.Light,
			Height:     8,
			Threshold:  floatPtr(7),
			ShowPoints: true,
			Series:     []chart.Series{{Values: []float64{1, 3, 2, 5, 4, 8, 6, 9, 7, 2, 5, 3}}},
		},
		{
			ChartType: chart.Line,
			Title:     "Line quad",
			Border:    border.Light,
			Mode:      chart.ModeQuad,
			Width:     40,
			Height:    8,
			Series:    []chart.Series{{Values: []float64{1, 3, 2, 5, 4, 8, 6, 9, 7, 2, 5, 3}}},
		},
		{
			ChartType: chart.Line,
			Title:     "Line braille + color",
			Border:    border.Double,
			Mode:      chart.ModeBraille,
			Width:     40,
			Height:    8,
			UseColor:  chart.ColorOn,
			Series: []chart.Series{
				{Name: "A", Values: []float64{1, 3, 2, 5, 4, 8, 6, 9, 7, 2, 5, 3}},
				{Name: "B", Values: []float64{5, 4, 6, 3, 7, 2, 8, 1, 9, 6, 3, 5}},
			},
		},
		{
			ChartType: chart.Scatter,
			Title:     "Scatter cell",
			Border:    border.Light,
			Series: []chart.Series{
				{Name: "A", Points: []chart.Point{{X: 1, Y: 1}, {X: 2, Y: 3}, {X: 3, Y: 2}}},
				{Name: "B", Points: []chart.Point{{X: 1, Y: 5}, {X: 4, Y: 4}}},
			},
		},
		{
			ChartType: chart.Scatter,
			Title:     "Scatter quad + color",
			Border:    border.Light,
			Mode:      chart.ModeQuad,
			UseColor:  chart.ColorOn,
			Series: []chart.Series{
				{Name: "A", Points: []chart.Point{{X: 1, Y: 1}, {X: 2, Y: 3}, {X: 3, Y: 2}}},
				{Name: "B", Points: []chart.Point{{X: 1, Y: 5}, {X: 4, Y: 4}}},
			},
		},
		{
			ChartType: chart.DualAxis,
			Title:     "Dual axis",
			Border:    border.Light,
			Series: []chart.Series{
				{Name: "Temp", Values: []float64{10, 12, 15, 14, 18, 20}},
				{Name: "Humidity", Values: []float64{80, 78, 65, 70, 60, 55}},
			},
		},
		{
			ChartType: chart.Pie,
			Title:     "Pie",
			Border:    border.Rounded,
			Width:     30,
			Height:    15,
			Series: []chart.Series{
				{Name: "Chrome", Values: []float64{60}},
				{Name: "Firefox", Values: []float64{20}},
				{Name: "Safari", Values: []float64{15}},
				{Name: "Other", Values: []float64{5}},
			},
		},
		{
			ChartType: chart.Histogram,
			Title:     "Histogram",
			Border:    border.Double,
			Bins:      5,
			Series:    []chart.Series{{Values: []float64{1, 2, 2, 3, 3, 3, 4, 4, 5, 8, 9, 9}}},
		},
		{
			ChartType: chart.Heatmap,
			Title:     "Heatmap",
			Border:    border.Light,
			Labels:    []string{"Mon", "Tue", "Wed", "Thu", "Fri"},
			Series: []chart.Series{
				{Name: "9am", Values: []float64{1, 3, 2, 5, 4}},
				{Name: "1pm", Values: []float64{5, 4, 6, 3, 7}},
				{Name: "5pm", Values: []float64{2, 8, 1, 9, 6}},
			},
		},
		{
			ChartType: chart.Heatmap,
			Title:     "Heatmap color",
			Border:    border.Light,
			UseColor:  chart.ColorOn,
			Labels:    []string{"Mon", "Tue", "Wed"},
			Series: []chart.Series{
				{Name: "9am", Values: []float64{1, 3, 2}},
				{Name: "1pm", Values: []float64{5, 4, 6}},
			},
		},
		{
			ChartType: chart.Boxplot,
			Title:     "Boxplot",
			Border:    border.Light,
			Series: []chart.Series{
				{Name: "A", Values: []float64{1, 2, 2, 3, 4, 5, 5, 6, 9}},
				{Name: "B", Values: []float64{2, 3, 3, 3, 4, 4, 5, 7, 8, 20}},
			},
		},
	}

	for _, in := range cases {
		out, err := chart.Render(in)
		if err != nil {
			t.Fatalf("%s: unexpected error: %v", in.Title, err)
		}
		fmt.Printf("=== %s ===\n%s\n\n", in.Title, out)
	}
}

func floatPtr(v float64) *float64 { return &v }
