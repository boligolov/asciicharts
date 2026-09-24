package main

// The server's answers are pinned by testdata/, recorded from the Python server this one replaced:
// render_chart.json (754 calls: charts and chart errors byte for byte, and the calls to reject) and
// list_charts.json. The transports are tested for real: stdio (this test binary re-run as the server)
// and HTTP.

import (
	"context"
	"encoding/json"
	"fmt"
	"net"
	"os"
	"os/exec"
	"strings"
	"testing"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func TestMain(m *testing.M) {
	if os.Getenv("ASCIICHARTS_MCP_TEST_SERVE") == "1" {
		main()
		os.Exit(0)
	}
	os.Exit(m.Run())
}

func connect(t *testing.T, transport mcp.Transport) *mcp.ClientSession {
	t.Helper()
	session, err := mcp.NewClient(&mcp.Implementation{Name: "test"}, nil).Connect(context.Background(), transport, nil)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { session.Close() })
	return session
}

func inMemory(t *testing.T) *mcp.ClientSession {
	serverT, clientT := mcp.NewInMemoryTransports()
	if _, err := newServer().Connect(context.Background(), serverT, nil); err != nil {
		t.Fatal(err)
	}
	return connect(t, clientT)
}

func call(t *testing.T, s *mcp.ClientSession, name string, args any) (*mcp.CallToolResult, string) {
	t.Helper()
	r, err := s.CallTool(context.Background(), &mcp.CallToolParams{Name: name, Arguments: args})
	if err != nil {
		t.Fatal(err)
	}
	return r, r.Content[0].(*mcp.TextContent).Text
}

func readJSON(t *testing.T, path string, v any) {
	t.Helper()
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if err := json.Unmarshal(data, v); err != nil {
		t.Fatal(err)
	}
}

func TestRenderChartAnswers(t *testing.T) {
	var cases []struct {
		Args     json.RawMessage `json:"args"` // raw: 11.0 must reach the server as 11.0
		Out, Err string
		Rejected bool
	}
	readJSON(t, "testdata/render_chart.json", &cases)
	s := inMemory(t)
	failed := 0
	for i, c := range cases {
		r, text := call(t, s, "render_chart", c.Args)
		ok := false
		switch {
		case c.Rejected:
			ok = r.IsError && strings.HasPrefix(text, "Error executing tool render_chart: invalid arguments: ")
		case c.Err != "":
			ok = r.IsError && text == c.Err
		default:
			sc, _ := json.Marshal(r.StructuredContent)
			want, _ := json.Marshal(map[string]string{"result": c.Out})
			ok = !r.IsError && text == c.Out && string(sc) == string(want)
		}
		if !ok {
			failed++
			if failed <= 3 {
				t.Errorf("case %d: %s\n--- want (rejected %v)\n%s%s\n--- got (error %v)\n%s", i, c.Args, c.Rejected, c.Out, c.Err, r.IsError, text)
			}
		}
	}
	t.Logf("%d of %d answers as recorded", len(cases)-failed, len(cases))
}

func TestToolsAndCatalogue(t *testing.T) {
	s := inMemory(t)
	tools, err := s.ListTools(context.Background(), nil)
	if err != nil {
		t.Fatal(err)
	}
	var want []map[string]any
	readJSON(t, "tools.json", &want)
	got, _ := json.Marshal(tools.Tools)
	var gotAny []map[string]any
	json.Unmarshal(got, &gotAny)
	if g, w := fmt.Sprint(gotAny), fmt.Sprint(want); g != w {
		t.Errorf("tools/list is not tools.json:\n%s\n%s", g, w)
	}

	var texts []string
	readJSON(t, "testdata/list_charts.json", &texts)
	r, _ := call(t, s, "list_charts", map[string]any{})
	if r.IsError || len(r.Content) != len(texts) {
		t.Fatalf("list_charts: error %v, %d items", r.IsError, len(r.Content))
	}
	for i, c := range r.Content {
		if c.(*mcp.TextContent).Text != texts[i] {
			t.Errorf("list_charts item %d:\n%s\nwant\n%s", i, c.(*mcp.TextContent).Text, texts[i])
		}
	}
	sc, _ := json.Marshal(r.StructuredContent)
	var structured struct{ Result []struct{ Type string } }
	if json.Unmarshal(sc, &structured); len(structured.Result) != 12 || structured.Result[0].Type != "sparkline" {
		t.Errorf("list_charts structured content: %.200s", sc)
	}
}

// checkTools is the check every transport must pass.
func checkTools(t *testing.T, s *mcp.ClientSession) {
	t.Helper()
	tools, err := s.ListTools(context.Background(), nil)
	if err != nil || len(tools.Tools) != 2 {
		t.Fatalf("tools: %v %v", tools, err)
	}
	if r, text := call(t, s, "render_chart", map[string]any{"chartType": "vbar", "title": "Test", "labels": []any{"a", "b", "c"},
		"series": []any{map[string]any{"values": []any{1, 2, 3}}}}); r.IsError || !strings.Contains(text, "Test") || !strings.Contains(text, "┌") {
		t.Errorf("render_chart: %q", text)
	}
	if r, text := call(t, s, "render_chart", map[string]any{"chartType": "line", "series": []any{map[string]any{"values": []any{"1", "2"}}}}); !r.IsError {
		t.Errorf("a string value must be rejected: %q", text)
	}
	if r, _ := call(t, s, "list_charts", map[string]any{}); r.IsError || len(r.Content) != 12 {
		t.Errorf("list_charts: %v", r)
	}
}

func TestStdio(t *testing.T) {
	cmd := exec.Command(os.Args[0])
	cmd.Env = append(os.Environ(), "ASCIICHARTS_MCP_TEST_SERVE=1", "PORT=")
	checkTools(t, connect(t, &mcp.CommandTransport{Command: cmd}))
}

func freePort(t *testing.T) string {
	l, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer l.Close()
	return fmt.Sprint(l.Addr().(*net.TCPAddr).Port)
}

func TestHTTPAndHealthcheck(t *testing.T) {
	port := freePort(t)
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan error)
	go func() { done <- serveHTTP(ctx, newServer(), "127.0.0.1:"+port) }()
	defer func() { cancel(); <-done }()

	t.Setenv("PORT", port)
	for i := 0; healthcheck() != 0; i++ {
		if i == 100 {
			t.Fatal("HTTP server did not come up")
		}
		time.Sleep(50 * time.Millisecond)
	}
	checkTools(t, connect(t, &mcp.StreamableClientTransport{Endpoint: "http://127.0.0.1:" + port + "/mcp"}))

	t.Setenv("PORT", freePort(t))
	if healthcheck() != 1 {
		t.Error("healthcheck of a port nobody serves must fail")
	}
}
