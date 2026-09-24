package main

// Parity with the Python server (stdio, HTTP, tools/list, answers on random specs) is checked by
// python/tests/test_go_server.py; this test runs the tools in memory.

import (
	"context"
	"strings"
	"testing"

	"github.com/boligolov/asciicharts/go/asciicharts"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func TestTools(t *testing.T) {
	ctx := context.Background()
	serverT, clientT := mcp.NewInMemoryTransports()
	if _, err := newServer().Connect(ctx, serverT, nil); err != nil {
		t.Fatal(err)
	}
	session, err := mcp.NewClient(&mcp.Implementation{Name: "test"}, nil).Connect(ctx, clientT, nil)
	if err != nil {
		t.Fatal(err)
	}
	defer session.Close()

	tools, err := session.ListTools(ctx, nil)
	if err != nil || len(tools.Tools) != 2 || tools.Tools[0].Name != "list_charts" || tools.Tools[1].Name != "render_chart" {
		t.Fatalf("tools: %v %v", tools, err)
	}
	call := func(name string, args map[string]any) (string, bool) {
		t.Helper()
		r, err := session.CallTool(ctx, &mcp.CallToolParams{Name: name, Arguments: args})
		if err != nil {
			t.Fatal(err)
		}
		return r.Content[0].(*mcp.TextContent).Text, r.IsError
	}

	spec := `{"chartType":"hbar","labels":["a","b"],"series":[{"values":[3,1]}]}`
	want, _ := asciicharts.RenderJSON([]byte(spec))
	if got, isErr := call("render_chart", map[string]any{"chartType": "hbar", "labels": []any{"a", "b"},
		"series": []any{map[string]any{"values": []any{3, 1}}}}); isErr || got != want {
		t.Errorf("render_chart: %v\n%s\nwant\n%s", isErr, got, want)
	}
	if got, isErr := call("render_chart", map[string]any{"chartType": "line", "series": []any{map[string]any{"values": []any{1}}}}); !isErr ||
		got != `Error executing tool render_chart: series 0 "" must contain at least two values` {
		t.Errorf("chart error: %v %q", isErr, got)
	}
	for _, loose := range []map[string]any{
		{"chartType": "line", "series": []any{map[string]any{"values": []any{"1", "2"}}}},
		{"chartType": "line", "series": []any{map[string]any{"values": []any{true, false}}}},
		{"chartType": "line", "series": []any{map[string]any{"values": []any{1, 2}}}, "width": "40"},
		{"chartType": "line", "series": []any{map[string]any{"values": []any{1, 2}}}, "width": 40.5},
		{"chartType": "nope", "series": []any{map[string]any{"values": []any{1, 2}}}},
	} {
		if got, isErr := call("render_chart", loose); !isErr || !strings.Contains(got, "invalid arguments") {
			t.Errorf("%v should be rejected: %q", loose, got)
		}
	}
	if got, isErr := call("list_charts", map[string]any{}); isErr || !strings.HasPrefix(got, "{\n  \"type\": \"sparkline\",") {
		t.Errorf("list_charts: %v %q", isErr, got)
	}
}
