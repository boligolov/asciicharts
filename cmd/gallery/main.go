// Command gallery renders one example of every chart type supported by
// render_chart and prints them to stdout. Useful for a quick visual sanity
// check, and as the source of the examples in README.md.
package main

import (
	"fmt"

	"github.com/boligolov/ascii-charts-mcp/internal/border"
	"github.com/boligolov/ascii-charts-mcp/internal/chart"
)

func main() {
	examples := []struct {
		name  string
		input chart.Input
	}{
		{
			"sparkline",
			chart.Input{
				ChartType: chart.Sparkline,
				Border:    border.None,
				Series:    []chart.Series{{Name: "latency", Values: []float64{4, 6, 5, 9, 3, 7, 8, 2, 6, 9, 4}}},
			},
		},
		{
			"vbar (grouped)",
			chart.Input{
				ChartType: chart.VBar,
				Title:     "Revenue by quarter",
				Border:    border.Rounded,
				Height:    10,
				Series: []chart.Series{
					{Name: "2025", Values: []float64{30, 45, 40, 60}},
					{Name: "2026", Values: []float64{35, 50, 55, 70}},
				},
				Labels: []string{"Q1", "Q2", "Q3", "Q4"},
			},
		},
		{
			"vbar (wide)",
			chart.Input{
				ChartType: chart.VBar,
				Title:     "Revenue by quarter (width: 60)",
				Border:    border.Rounded,
				Height:    10,
				Width:     60,
				Series: []chart.Series{
					{Name: "2025", Values: []float64{30, 45, 40, 60}},
					{Name: "2026", Values: []float64{35, 50, 55, 70}},
				},
				Labels: []string{"Q1", "Q2", "Q3", "Q4"},
			},
		},
		{
			"vbar (stacked)",
			chart.Input{
				ChartType: chart.VBar,
				Title:     "Revenue by quarter (stacked)",
				Border:    border.Double,
				Stacked:   true,
				Height:    10,
				Series: []chart.Series{
					{Name: "Product", Values: []float64{30, 45, 40, 60}},
					{Name: "Services", Values: []float64{15, 20, 18, 25}},
				},
				Labels: []string{"Q1", "Q2", "Q3", "Q4"},
			},
		},
		{
			"vbar (halftone)",
			chart.Input{
				ChartType: chart.VBar,
				Title:     "Revenue by quarter (halftone)",
				Border:    border.Rounded,
				Height:    10,
				Style:     "halftone",
				Series: []chart.Series{
					{Name: "2025", Values: []float64{30, 45, 40, 60}},
					{Name: "2026", Values: []float64{35, 50, 55, 70}},
				},
				Labels: []string{"Q1", "Q2", "Q3", "Q4"},
			},
		},
		{
			"vbar (ascii)",
			chart.Input{
				ChartType: chart.VBar,
				Title:     "Revenue by quarter (ascii)",
				Border:    border.Rounded,
				Height:    10,
				Style:     "ascii",
				Series: []chart.Series{
					{Name: "2025", Values: []float64{30, 45, 40, 60}},
					{Name: "2026", Values: []float64{35, 50, 55, 70}},
				},
				Labels: []string{"Q1", "Q2", "Q3", "Q4"},
			},
		},
		{
			"vbar (diverging)",
			chart.Input{
				ChartType: chart.VBar,
				Title:     "Subscriber growth YoY (diverging)",
				Border:    border.Rounded,
				Height:    10,
				Style:     "ascii",
				Series: []chart.Series{
					{Name: "Satellite TV", Values: []float64{-6, -8, -5, -9, -7, -4, -8}},
					{Name: "Third-party", Values: []float64{3, 5, 2, 8, 4, 6, 9}},
				},
				Labels: []string{"Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7"},
			},
		},
		{
			"hbar (single)",
			chart.Input{
				ChartType: chart.HBar,
				Title:     "Browser share",
				Border:    border.Light,
				Series:    []chart.Series{{Values: []float64{62, 21, 12, 5}}},
				Labels:    []string{"Chrome", "Firefox", "Safari", "Other"},
			},
		},
		{
			"hbar (stacked)",
			chart.Input{
				ChartType: chart.HBar,
				Title:     "Revenue by region (stacked)",
				Border:    border.Light,
				Stacked:   true,
				Labels:    []string{"EMEA", "APAC", "Americas"},
				Series: []chart.Series{
					{Name: "Product", Values: []float64{40, 25, 55}},
					{Name: "Services", Values: []float64{15, 20, 18}},
				},
			},
		},
		{
			"hbar (diverging)",
			chart.Input{
				ChartType: chart.HBar,
				Title:     "Estimated sales growth (diverging)",
				Border:    border.Light,
				Series:    []chart.Series{{Values: []float64{-8.2, 4.9, 27.6, -42.8, 7.8}}},
				Labels:    []string{"ABB", "Aetna", "Apple", "Bankers Pet.", "Biogen"},
			},
		},
		{
			"hbar (ascii, grouped)",
			chart.Input{
				ChartType: chart.HBar,
				Title:     "Share of analysts' ratings that are a buy",
				Border:    border.Light,
				Style:     "ascii",
				Labels:    []string{"04/01/15", "06/01/15", "08/01/15", "10/01/15"},
				Series: []chart.Series{
					{Name: "Shell", Values: []float64{22, 25, 24, 30}},
					{Name: "Total", Values: []float64{34, 30, 32, 30}},
					{Name: "BP", Values: []float64{15, 12, 18, 22}},
				},
			},
		},
		{
			"hbar (halftone, stacked)",
			chart.Input{
				ChartType: chart.HBar,
				Title:     "Revenue by region (halftone)",
				Border:    border.Light,
				Stacked:   true,
				Style:     "halftone",
				Labels:    []string{"EMEA", "APAC", "Americas"},
				Series: []chart.Series{
					{Name: "Product", Values: []float64{40, 25, 55}},
					{Name: "Services", Values: []float64{15, 20, 18}},
				},
			},
		},
		{
			"hbar (ascii, single)",
			chart.Input{
				ChartType: chart.HBar,
				Title:     "Data center switching market share",
				Border:    border.Light,
				Style:     "ascii",
				Series:    []chart.Series{{Values: []float64{61, 9, 6, 4, 4, 4, 3, 2}}},
				Labels:    []string{"Cisco", "HPE", "Arista", "Huawei", "Juniper", "Dell", "Lenovo", "Brocade"},
			},
		},
		{
			"line (cell)",
			chart.Input{
				ChartType: chart.Line,
				Title:     "CPU load",
				Border:    border.Light,
				Height:    8,
				Series:    []chart.Series{{Values: []float64{12, 18, 15, 30, 42, 38, 50, 45, 60, 55, 48, 35}}},
			},
		},
		{
			"line (threshold + points)",
			chart.Input{
				ChartType:  chart.Line,
				Title:      "Response time vs SLA",
				Border:     border.Light,
				Height:     8,
				Threshold:  floatPtr(50),
				ShowPoints: true,
				Series:     []chart.Series{{Values: []float64{20, 25, 22, 30, 45, 38, 55, 60, 48, 35, 30, 28}}},
			},
		},
		{
			"line (dotted, Bloomberg-style)",
			chart.Input{
				ChartType: chart.Line,
				Title:     "Apple revenue",
				Border:    border.Light,
				Height:    10,
				Width:     50,
				Style:     "dotted",
				Series:    []chart.Series{{Name: "iPhone", Values: []float64{15, 16, 17.5, 19, 20, 21.5, 23, 24.5, 26, 27.5, 29, 30}}},
			},
		},
		{
			"line (braille, two series)",
			chart.Input{
				ChartType: chart.Line,
				Title:     "Temperature: forecast vs actual",
				Border:    border.Heavy,
				Mode:      chart.ModeBraille,
				Width:     50,
				Height:    10,
				Series: []chart.Series{
					{Name: "forecast", Values: []float64{10, 12, 15, 14, 18, 20, 19, 17, 15, 13, 12, 11}},
					{Name: "actual", Values: []float64{11, 13, 14, 16, 17, 19, 21, 18, 16, 14, 13, 10}},
				},
			},
		},
		{
			"area (single series)",
			chart.Input{
				ChartType: chart.Area,
				Title:     "Actively managed fund flows",
				Border:    border.Light,
				Height:    8,
				Series:    []chart.Series{{Values: []float64{20, 10, -20, -60, -120, -180, -260, -340, -420, -520, -600}}},
			},
		},
		{
			"area (stacked)",
			chart.Input{
				ChartType: chart.Area,
				Title:     "Mobile data traffic (stacked)",
				Border:    border.Light,
				Height:    8,
				Stacked:   true,
				Style:     "ascii",
				Series: []chart.Series{
					{Name: "Other", Values: []float64{1, 2, 3, 5, 8, 12}},
					{Name: "Video", Values: []float64{0.2, 0.4, 0.8, 1.5, 2.5, 4}},
				},
				Labels: []string{"2014", "2015", "2016", "2017", "2018", "2019"},
			},
		},
		{
			"dotplot",
			chart.Input{
				ChartType: chart.DotPlot,
				Title:     "2016 apartment rent growth forecast",
				Border:    border.Light,
				Width:     30,
				Labels:    []string{"Oakland", "San Francisco", "Seattle", "Denver", "Chicago", "Detroit"},
				Series:    []chart.Series{{Values: []float64{5.2, 4.8, 4.4, 3.6, 2.8, 2.2}}},
			},
		},
		{
			"scatter (cell, two groups)",
			chart.Input{
				ChartType: chart.Scatter,
				Title:     "Height vs weight",
				Border:    border.Light,
				Width:     40,
				Height:    14,
				Series: []chart.Series{
					{Name: "group A", Points: []chart.Point{
						{X: 158, Y: 52}, {X: 160, Y: 55}, {X: 162, Y: 54}, {X: 165, Y: 60},
						{X: 167, Y: 58}, {X: 170, Y: 65}, {X: 172, Y: 68}, {X: 163, Y: 62},
					}},
					{Name: "group B", Points: []chart.Point{
						{X: 175, Y: 80}, {X: 178, Y: 78}, {X: 180, Y: 85}, {X: 183, Y: 88},
						{X: 185, Y: 90}, {X: 182, Y: 82}, {X: 188, Y: 92}, {X: 177, Y: 86},
					}},
				},
			},
		},
		{
			"scatter (quad, colored groups)",
			chart.Input{
				ChartType: chart.Scatter,
				Title:     "Height vs weight",
				Border:    border.Light,
				Mode:      chart.ModeQuad,
				Width:     40,
				Height:    14,
				UseColor:  chart.ColorOn,
				Series: []chart.Series{
					{Name: "group A", Points: []chart.Point{
						{X: 158, Y: 52}, {X: 160, Y: 55}, {X: 162, Y: 54}, {X: 165, Y: 60},
						{X: 167, Y: 58}, {X: 170, Y: 65}, {X: 172, Y: 68}, {X: 163, Y: 62},
					}},
					{Name: "group B", Points: []chart.Point{
						{X: 175, Y: 80}, {X: 178, Y: 78}, {X: 180, Y: 85}, {X: 183, Y: 88},
						{X: 185, Y: 90}, {X: 182, Y: 82}, {X: 188, Y: 92}, {X: 177, Y: 86},
					}},
				},
			},
		},
		{
			"dual_axis",
			chart.Input{
				ChartType: chart.DualAxis,
				Title:     "Temperature (left) vs humidity (right)",
				Border:    border.Light,
				Height:    8,
				Series: []chart.Series{
					{Name: "Temp °C", Values: []float64{10, 12, 15, 14, 18, 20, 19}},
					{Name: "Humidity %", Values: []float64{80, 78, 65, 70, 60, 55, 58}},
				},
			},
		},
		{
			"pie",
			chart.Input{
				ChartType: chart.Pie,
				Title:     "Browser share",
				Border:    border.Rounded,
				Width:     32,
				Height:    16,
				Series: []chart.Series{
					{Name: "Chrome", Values: []float64{62}},
					{Name: "Firefox", Values: []float64{21}},
					{Name: "Safari", Values: []float64{12}},
					{Name: "Other", Values: []float64{5}},
				},
			},
		},
		{
			"histogram",
			chart.Input{
				ChartType: chart.Histogram,
				Title:     "Response times (ms)",
				Border:    border.Double,
				Bins:      6,
				Series:    []chart.Series{{Values: []float64{12, 15, 14, 18, 20, 22, 21, 25, 30, 28, 35, 40, 55, 60, 18, 19, 22}}},
			},
		},
		{
			"heatmap",
			chart.Input{
				ChartType: chart.Heatmap,
				Title:     "Traffic by hour",
				Border:    border.Light,
				Labels:    []string{"Mon", "Tue", "Wed", "Thu", "Fri"},
				Series: []chart.Series{
					{Name: "9am", Values: []float64{20, 35, 25, 40, 30}},
					{Name: "1pm", Values: []float64{55, 60, 58, 62, 50}},
					{Name: "5pm", Values: []float64{80, 70, 90, 85, 95}},
				},
			},
		},
		{
			"boxplot",
			chart.Input{
				ChartType: chart.Boxplot,
				Title:     "Test scores by class",
				Border:    border.Light,
				Width:     50,
				Series: []chart.Series{
					{Name: "Class A", Values: []float64{55, 60, 62, 65, 70, 72, 75, 80, 85, 95}},
					{Name: "Class B", Values: []float64{40, 50, 58, 60, 63, 65, 68, 70, 78, 99}},
				},
			},
		},
	}

	for _, ex := range examples {
		out, err := chart.Render(ex.input)
		if err != nil {
			fmt.Printf("=== %s ===\nERROR: %v\n\n", ex.name, err)
			continue
		}
		fmt.Printf("=== %s ===\n%s\n\n", ex.name, out)
	}
}

func floatPtr(v float64) *float64 { return &v }
