package main

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func TestRenderChartToolEndToEnd(t *testing.T) {
	ctx := context.Background()

	clientTransport, serverTransport := mcp.NewInMemoryTransports()

	server := newServer(nil)
	serverSession, err := server.Connect(ctx, serverTransport, nil)
	if err != nil {
		t.Fatalf("server.Connect: %v", err)
	}
	defer serverSession.Close()

	client := mcp.NewClient(&mcp.Implementation{Name: "test-client", Version: "v0.0.0"}, nil)
	clientSession, err := client.Connect(ctx, clientTransport, nil)
	if err != nil {
		t.Fatalf("client.Connect: %v", err)
	}
	defer clientSession.Close()

	tools, err := clientSession.ListTools(ctx, nil)
	if err != nil {
		t.Fatalf("ListTools: %v", err)
	}
	if len(tools.Tools) != 2 {
		t.Fatalf("unexpected tools: %+v", tools.Tools)
	}
	names := map[string]bool{}
	for _, tool := range tools.Tools {
		names[tool.Name] = true
	}
	if !names["render_chart"] || !names["feedback"] {
		t.Fatalf("expected render_chart and feedback tools, got: %+v", tools.Tools)
	}

	result, err := clientSession.CallTool(ctx, &mcp.CallToolParams{
		Name: "render_chart",
		Arguments: map[string]any{
			"chartType": "vbar",
			"title":     "Test",
			"border":    "light",
			"series": []map[string]any{
				{"values": []float64{1, 2, 3}},
			},
			"labels": []string{"a", "b", "c"},
		},
	})
	if err != nil {
		t.Fatalf("CallTool: %v", err)
	}
	if result.IsError {
		t.Fatalf("tool returned an error result: %+v", result.Content)
	}
	if len(result.Content) != 1 {
		t.Fatalf("expected exactly one content block, got %d", len(result.Content))
	}
	text, ok := result.Content[0].(*mcp.TextContent)
	if !ok {
		t.Fatalf("expected TextContent, got %T", result.Content[0])
	}
	if !strings.Contains(text.Text, "Test") || !strings.Contains(text.Text, "┌") {
		t.Fatalf("unexpected chart output:\n%s", text.Text)
	}
}

func TestRenderChartToolInvalidInput(t *testing.T) {
	ctx := context.Background()

	clientTransport, serverTransport := mcp.NewInMemoryTransports()

	server := newServer(nil)
	serverSession, err := server.Connect(ctx, serverTransport, nil)
	if err != nil {
		t.Fatalf("server.Connect: %v", err)
	}
	defer serverSession.Close()

	client := mcp.NewClient(&mcp.Implementation{Name: "test-client", Version: "v0.0.0"}, nil)
	clientSession, err := client.Connect(ctx, clientTransport, nil)
	if err != nil {
		t.Fatalf("client.Connect: %v", err)
	}
	defer clientSession.Close()

	result, err := clientSession.CallTool(ctx, &mcp.CallToolParams{
		Name: "render_chart",
		Arguments: map[string]any{
			"chartType": "not_a_real_chart_type",
			"series":    []map[string]any{{"values": []float64{1}}},
		},
	})
	if err != nil {
		t.Fatalf("CallTool: %v", err)
	}
	if !result.IsError {
		t.Fatalf("expected an error result for unknown chart type, got: %+v", result.Content)
	}
}

func TestFeedbackTool(t *testing.T) {
	ctx := context.Background()

	clientTransport, serverTransport := mcp.NewInMemoryTransports()

	server := newServer(nil)
	serverSession, err := server.Connect(ctx, serverTransport, nil)
	if err != nil {
		t.Fatalf("server.Connect: %v", err)
	}
	defer serverSession.Close()

	client := mcp.NewClient(&mcp.Implementation{Name: "test-client", Version: "v0.0.0"}, nil)
	clientSession, err := client.Connect(ctx, clientTransport, nil)
	if err != nil {
		t.Fatalf("client.Connect: %v", err)
	}
	defer clientSession.Close()

	result, err := clientSession.CallTool(ctx, &mcp.CallToolParams{
		Name:      "feedback",
		Arguments: map[string]any{"message": "the pie chart legend wraps oddly at width 20"},
	})
	if err != nil {
		t.Fatalf("CallTool: %v", err)
	}
	if result.IsError {
		t.Fatalf("tool returned an error result: %+v", result.Content)
	}

	// A nil store means feedback is accepted but silently not persisted —
	// this must not surface as an error to the caller.
	result, err = clientSession.CallTool(ctx, &mcp.CallToolParams{
		Name:      "feedback",
		Arguments: map[string]any{"message": strings.Repeat("x", 257)},
	})
	if err != nil {
		t.Fatalf("CallTool: %v", err)
	}
	if !result.IsError {
		t.Fatalf("expected an error result for a too-long message, got: %+v", result.Content)
	}

	result, err = clientSession.CallTool(ctx, &mcp.CallToolParams{
		Name:      "feedback",
		Arguments: map[string]any{"message": "   "},
	})
	if err != nil {
		t.Fatalf("CallTool: %v", err)
	}
	if !result.IsError {
		t.Fatalf("expected an error result for a blank message, got: %+v", result.Content)
	}
}

func TestRenderChartOverHTTP(t *testing.T) {
	ctx := context.Background()

	server := newServer(nil)
	mcpHandler := mcp.NewStreamableHTTPHandler(
		func(*http.Request) *mcp.Server { return server },
		&mcp.StreamableHTTPOptions{Stateless: true},
	)
	mux := http.NewServeMux()
	mux.Handle("/mcp", mcpHandler)
	httpServer := httptest.NewServer(mux)
	defer httpServer.Close()

	client := mcp.NewClient(&mcp.Implementation{Name: "test-client", Version: "v0.0.0"}, nil)
	clientSession, err := client.Connect(ctx, &mcp.StreamableClientTransport{Endpoint: httpServer.URL + "/mcp"}, nil)
	if err != nil {
		t.Fatalf("client.Connect: %v", err)
	}
	defer clientSession.Close()

	tools, err := clientSession.ListTools(ctx, nil)
	if err != nil {
		t.Fatalf("ListTools: %v", err)
	}
	if len(tools.Tools) != 2 {
		t.Fatalf("unexpected tools over HTTP: %+v", tools.Tools)
	}

	result, err := clientSession.CallTool(ctx, &mcp.CallToolParams{
		Name: "render_chart",
		Arguments: map[string]any{
			"chartType": "sparkline",
			"series":    []map[string]any{{"values": []float64{1, 2, 3}}},
		},
	})
	if err != nil {
		t.Fatalf("CallTool over HTTP: %v", err)
	}
	if result.IsError {
		t.Fatalf("tool returned an error result over HTTP: %+v", result.Content)
	}
}
