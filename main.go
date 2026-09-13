// Command ascii-charts-mcp is an MCP server exposing two tools: render_chart,
// which renders numeric data as an ASCII/Unicode text chart, and feedback,
// which forwards a short free-text message to the maintainer. If DATABASE_URL
// is set, anonymous usage statistics and feedback messages are recorded to
// Postgres; otherwise the server runs exactly the same without a database.
//
// By default the server speaks MCP over stdio, for a client that launches
// its own process per session (Claude Desktop, Claude Code, etc.). Setting
// the PORT environment variable switches it to a long-running HTTP server
// instead, serving the streamable-HTTP MCP transport at /mcp — for a shared
// deployment multiple clients connect to over the network.
package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
	"time"
	"unicode/utf8"

	"github.com/boligolov/ascii-charts-mcp/internal/chart"
	"github.com/boligolov/ascii-charts-mcp/internal/store"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

const serverVersion = "v0.2.0"

// maxFeedbackLen is the feedback tool's input cap, in runes.
const maxFeedbackLen = 256

type renderChartOutput struct {
	Chart string `json:"chart" jsonschema:"the rendered chart as text"`
}

type feedbackInput struct {
	Message string `json:"message" jsonschema:"feedback message for the maintainer (bug report, feature request, or general comment); at most 256 characters"`
}

type feedbackOutput struct {
	Received bool `json:"received" jsonschema:"whether the feedback was recorded"`
}

// app holds the shared dependencies each tool handler needs. Its stats
// field is a *store.Store, which is nil (and therefore a no-op on every
// method) whenever DATABASE_URL isn't set.
type app struct {
	stats *store.Store
}

func (a *app) renderChart(ctx context.Context, _ *mcp.CallToolRequest, input chart.Input) (*mcp.CallToolResult, renderChartOutput, error) {
	rendered, err := chart.Render(input)

	event := store.ChartEvent{
		ChartType:   string(input.ChartType),
		Style:       input.Style,
		Mode:        string(input.Mode),
		Border:      string(input.Border),
		UseColor:    input.UseColor == chart.ColorOn,
		SeriesCount: len(input.Series),
		Success:     err == nil,
	}
	if err != nil {
		event.ErrorMessage = truncateRunes(err.Error(), 200)
	} else {
		event.PointCountBucket = bucket(totalPoints(input), 10, 100, 1000)
		event.OutputSizeBucket = bucket(len(rendered), 500, 2000, 8000)
	}
	a.stats.RecordChartEvent(ctx, event)

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

func (a *app) submitFeedback(ctx context.Context, _ *mcp.CallToolRequest, input feedbackInput) (*mcp.CallToolResult, feedbackOutput, error) {
	msg := strings.TrimSpace(input.Message)
	if msg == "" {
		return &mcp.CallToolResult{
			Content: []mcp.Content{&mcp.TextContent{Text: "feedback message must not be empty"}},
			IsError: true,
		}, feedbackOutput{}, nil
	}
	if n := utf8.RuneCountInString(msg); n > maxFeedbackLen {
		return &mcp.CallToolResult{
			Content: []mcp.Content{&mcp.TextContent{Text: fmt.Sprintf("feedback message must be at most %d characters, got %d", maxFeedbackLen, n)}},
			IsError: true,
		}, feedbackOutput{}, nil
	}

	a.stats.RecordFeedback(ctx, msg)

	return &mcp.CallToolResult{
		Content: []mcp.Content{&mcp.TextContent{Text: "Thanks for the feedback!"}},
	}, feedbackOutput{Received: true}, nil
}

// totalPoints counts a chart.Input's data points across every series,
// summing whichever of Values/Points that series actually uses.
func totalPoints(in chart.Input) int {
	n := 0
	for _, s := range in.Series {
		n += len(s.Values) + len(s.Points)
	}
	return n
}

// bucket labels n against ascending thresholds, e.g. bucket(n, 10, 100,
// 1000) yields "<10", "10-100", "100-1000" or "1000+".
func bucket(n int, thresholds ...int) string {
	for i, t := range thresholds {
		if n < t {
			if i == 0 {
				return fmt.Sprintf("<%d", t)
			}
			return fmt.Sprintf("%d-%d", thresholds[i-1], t)
		}
	}
	return fmt.Sprintf("%d+", thresholds[len(thresholds)-1])
}

func truncateRunes(s string, max int) string {
	r := []rune(s)
	if len(r) <= max {
		return s
	}
	return string(r[:max])
}

func newServer(stats *store.Store) *mcp.Server {
	a := &app{stats: stats}

	server := mcp.NewServer(&mcp.Implementation{
		Name:    "ascii-charts-mcp",
		Version: serverVersion,
	}, nil)

	mcp.AddTool(server, &mcp.Tool{
		Name: "render_chart",
		Description: "Render numeric data as an ASCII/Unicode text chart. Supports sparkline, vbar, hbar, line, area, scatter, " +
			"dual_axis, pie, histogram, heatmap, boxplot and dotplot, with an optional title, border frame (none/ascii/light/" +
			"heavy/double/rounded), sub-character resolution for line/scatter/dual_axis (cell/quad/braille), bar/area fill " +
			"style (solid/halftone/ascii) and line style (solid/dotted), a dashed threshold line and configurable per-point " +
			"markers for line charts, a target chart width (vbar/hbar scale to fill it), automatic diverging bars for " +
			"negative values, and optional ANSI 256-color output. Returns the chart as plain text.",
	}, a.renderChart)

	mcp.AddTool(server, &mcp.Tool{
		Name: "feedback",
		Description: "Send a short free-text feedback message (bug report, feature request, or general comment) about this " +
			"MCP server to its maintainer. At most 256 characters.",
	}, a.submitFeedback)

	return server
}

// defaultPort is healthcheckSelf's fallback when PORT isn't set — matching
// what a typical deployment sets it to, so the healthcheck subcommand still
// probes the right port even if invoked from an environment where PORT
// somehow isn't visible.
const defaultPort = "8080"

func main() {
	// A tiny self-check subcommand instead of a second binary: the deployed
	// image is FROM scratch with nothing else in it (no shell, no curl), so
	// `docker healthcheck` runs this same binary against its own /healthz.
	if len(os.Args) > 1 && os.Args[1] == "healthcheck" {
		os.Exit(healthcheckSelf())
	}

	ctx := context.Background()

	stats, err := store.Open(ctx, os.Getenv("DATABASE_URL"), serverVersion)
	if err != nil {
		log.Printf("stats: %v — continuing without usage statistics", err)
		stats = nil
	}
	defer stats.Close()

	server := newServer(stats)

	if port := os.Getenv("PORT"); port != "" {
		runHTTP(server, port)
		return
	}

	if err := server.Run(ctx, &mcp.StdioTransport{}); err != nil {
		log.Fatal(err)
	}
}

// runHTTP serves the MCP streamable-HTTP transport at /mcp, plus a plain
// /healthz for container/orchestrator probes. Stateless: true is used
// because this server never needs to push unsolicited messages to a client
// (no server-initiated requests or notifications) — every session is just
// one tool call answered directly, so there's no bidirectional state worth
// tracking between requests.
func runHTTP(server *mcp.Server, port string) {
	mcpHandler := mcp.NewStreamableHTTPHandler(
		func(*http.Request) *mcp.Server { return server },
		&mcp.StreamableHTTPOptions{Stateless: true},
	)

	mux := http.NewServeMux()
	mux.Handle("/mcp", mcpHandler)
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	addr := ":" + port
	log.Printf("ascii-charts-mcp: serving MCP over HTTP at %s/mcp", addr)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatal(err)
	}
}

// healthcheckSelf GETs its own /healthz and returns a process exit code
// (0 healthy, 1 not) — see the "healthcheck" subcommand in main.
func healthcheckSelf() int {
	port := os.Getenv("PORT")
	if port == "" {
		port = defaultPort
	}
	client := &http.Client{Timeout: 3 * time.Second}
	resp, err := client.Get("http://127.0.0.1:" + port + "/healthz")
	if err != nil {
		return 1
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return 1
	}
	return 0
}
