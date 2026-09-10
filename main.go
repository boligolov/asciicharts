// Command ascii-charts-mcp is an MCP server exposing a single tool,
// render_chart, which renders numeric data as an ASCII/Unicode text chart.
package main

import (
	"context"
	"log"

	"github.com/boligolov/ascii-charts-mcp/internal/chart"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

type renderChartOutput struct {
	Chart string `json:"chart" jsonschema:"the rendered chart as text"`
}

func renderChart(_ context.Context, _ *mcp.CallToolRequest, input chart.Input) (*mcp.CallToolResult, renderChartOutput, error) {
	rendered, err := chart.Render(input)
	if err != nil {
		return &mcp.CallToolResult{
			Content: []mcp.Content{&mcp.TextContent{Text: err.Error()}},
			IsError: true,
		}, renderChartOutput{}, nil
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{&mcp.TextContent{Text: rendered}},
	}, renderChartOutput{Chart: rendered}, nil
}

func newServer() *mcp.Server {
	server := mcp.NewServer(&mcp.Implementation{
		Name:    "ascii-charts-mcp",
		Version: "v0.1.0",
	}, nil)

	mcp.AddTool(server, &mcp.Tool{
		Name: "render_chart",
		Description: "Render numeric data as an ASCII/Unicode text chart. Supports sparkline, vbar, hbar, line, scatter, " +
			"dual_axis, pie, histogram, heatmap and boxplot, with an optional title, border frame (none/ascii/light/heavy/" +
			"double/rounded), sub-character resolution for line/scatter/dual_axis (cell/quad/braille), a dashed threshold " +
			"line and per-point markers for line charts, and optional ANSI 256-color output. Returns the chart as plain text.",
	}, renderChart)

	return server
}

func main() {
	if err := newServer().Run(context.Background(), &mcp.StdioTransport{}); err != nil {
		log.Fatal(err)
	}
}
